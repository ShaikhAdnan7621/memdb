"""
Dynamic Memory Database with PostgreSQL Persistence
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
import asyncpg

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cached record with metadata"""
    data: dict
    dirty: bool = False
    last_access: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    
    def touch(self):
        self.last_access = time.time()
    
    def mark_dirty(self):
        self.dirty = True
        self.last_updated = time.time()

class MemDB:
    """Hybrid in-memory + PostgreSQL database"""
    
    def __init__(self, db_url: str, flush_interval: int = 600, evict_interval: int = 600, max_connections: int = 10):
        self.db_url = db_url
        self.flush_interval = flush_interval
        self.evict_interval = evict_interval
        self.max_connections = max_connections
        
        # Storage: {table_name: {key: CacheEntry}}
        self.cache: Dict[str, Dict[str, CacheEntry]] = defaultdict(dict)
        self.dirty_records: Dict[str, Set[str]] = defaultdict(set)
        self.schemas: Dict[str, dict] = {}
        
        self.lock = asyncio.Lock()
        self.pool: Optional[asyncpg.Pool] = None
        self.background_task: Optional[asyncio.Task] = None
        
        self.stats_data = {
            'cache_hits': 0, 'cache_misses': 0, 'inserts': 0, 
            'flushes': 0, 'evictions': 0
        }
    
    async def start(self):
        """Initialize database and start background tasks"""
        self.pool = await asyncpg.create_pool(self.db_url, min_size=1, max_size=self.max_connections)
        
        # Import and start background tasks
        import memdb_tasks
        self.background_task = asyncio.create_task(memdb_tasks.start_background_tasks(self))
        
        logger.info(f"MemDB started: flush={self.flush_interval}s, evict={self.evict_interval}s")
    
    async def stop(self):
        """Cleanup and final flush"""
        if self.background_task:
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                pass
        
        await self.flush()
        if self.pool:
            await self.pool.close()
        logger.info("MemDB stopped")
    
    async def create_table(self, table_name: str, schema: dict):
        """Create table with JSONB storage"""
        if table_name in self.schemas:
            return
        
        self.schemas[table_name] = schema
        db_table = f"memdb_{table_name}"
        
        async with self.pool.acquire() as conn:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {db_table} (
                    key TEXT PRIMARY KEY,
                    data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{db_table}_data ON {db_table} USING GIN (data)")
        
        logger.info(f"Created table: {db_table}")
    
    async def insert(self, table_name: str, key: str, record: dict):
        """Insert record (memory-first)"""
        if table_name not in self.schemas:
            await self.create_table(table_name, {})
        
        async with self.lock:
            entry = CacheEntry(data=record.copy(), dirty=True)
            entry.mark_dirty()
            self.cache[table_name][key] = entry
            self.dirty_records[table_name].add(key)
            self.stats_data['inserts'] += 1
    
    async def upsert(self, table_name: str, key: str, record: dict):
        """Upsert record"""
        await self.insert(table_name, key, record)
    
    async def get(self, table_name: str, key: str, use_cache: bool = True) -> Optional[dict]:
        """Get record with read-through caching"""
        async with self.lock:
            # Check cache
            if use_cache and key in self.cache[table_name]:
                entry = self.cache[table_name][key]
                entry.touch()
                self.stats_data['cache_hits'] += 1
                return entry.data.copy()
            
            # Cache miss - load from DB
            self.stats_data['cache_misses'] += 1
            if table_name not in self.schemas:
                return None
            
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(f"SELECT data FROM memdb_{table_name} WHERE key = $1", key)
                if row:
                    data = row['data']
                    # Ensure data is a dict (JSONB should already be a dict)
                    if isinstance(data, str):
                        data = json.loads(data)
                    if use_cache:
                        entry = CacheEntry(data=data.copy(), dirty=False)
                        self.cache[table_name][key] = entry
                    return data
                return None
    
    async def query(self, table_name: str, where_sql: str = "", limit: int = 100) -> List[dict]:
        """Query records from database"""
        if table_name not in self.schemas:
            return []
        
        query = f"SELECT key, data FROM memdb_{table_name}"
        if where_sql:
            query += f" WHERE {where_sql}"
        query += f" LIMIT {limit}"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [{'_key': row['key'], **row['data']} for row in rows]
    
    async def flush(self, table_name: Optional[str] = None):
        """Flush dirty records to database"""
        async with self.lock:
            tables = [table_name] if table_name else list(self.dirty_records.keys())
            
            for table in tables:
                if not self.dirty_records[table]:
                    continue
                
                # Prepare batch upsert
                records = []
                keys_to_clean = []
                
                for key in list(self.dirty_records[table]):
                    if key in self.cache[table]:
                        entry = self.cache[table][key]
                        if entry.dirty:
                            records.append((key, entry.data))
                            keys_to_clean.append(key)
                
                if records:
                    async with self.pool.acquire() as conn:
                        # Convert dict to JSON string for PostgreSQL JSONB
                        json_records = [(key, json.dumps(data)) for key, data in records]
                        await conn.executemany(
                            f"INSERT INTO memdb_{table} (key, data, updated_at) VALUES ($1, $2::jsonb, NOW()) "
                            f"ON CONFLICT (key) DO UPDATE SET data = $2::jsonb, updated_at = NOW()",
                            json_records
                        )
                    
                    # Mark as clean
                    for key in keys_to_clean:
                        if key in self.cache[table]:
                            self.cache[table][key].dirty = False
                        self.dirty_records[table].discard(key)
                    
                    self.stats_data['flushes'] += len(records)
                    logger.info(f"Flushed {len(records)} records from {table}")
    
    async def evict_idle(self):
        """Evict idle records from memory"""
        async with self.lock:
            now = time.time()
            evicted = 0
            
            for table_name in list(self.cache.keys()):
                for key in list(self.cache[table_name].keys()):
                    entry = self.cache[table_name][key]
                    
                    # Never evict dirty records
                    if entry.dirty:
                        continue
                    
                    # Evict if idle too long
                    if now - entry.last_access > self.evict_interval:
                        del self.cache[table_name][key]
                        evicted += 1
            
            self.stats_data['evictions'] += evicted
            if evicted > 0:
                logger.info(f"Evicted {evicted} idle records")
    
    def stats(self) -> dict:
        """Get database statistics"""
        return {
            **self.stats_data,
            'cached_records': sum(len(table) for table in self.cache.values()),
            'dirty_records': sum(len(keys) for keys in self.dirty_records.values()),
            'tables': len(self.schemas)
        }