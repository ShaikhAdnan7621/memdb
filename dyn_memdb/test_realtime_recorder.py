"""
Real-time Interaction Recorder for MemDB
Records all database operations with timestamps and states
"""

import asyncio
import logging
import time
import json
import os
from datetime import datetime
from memdb import MemDB
import asyncpg

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealtimeRecorder:
    def __init__(self, db, output_file="interaction_log.json"):
        self.db = db
        self.output_file = output_file
        self.interactions = []
        self.start_time = time.time()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def timestamp(self):
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    def elapsed_time(self):
        return round(time.time() - self.start_time, 3)
    
    async def record_interaction(self, operation, details, before_state=None, after_state=None):
        """Record a single interaction with full context"""
        
        # Get current database state
        memory_state = await self.get_memory_state()
        db_state = await self.get_db_state()
        stats = self.db.stats()
        
        interaction = {
            "session_id": self.session_id,
            "timestamp": self.timestamp(),
            "elapsed_seconds": self.elapsed_time(),
            "operation": operation,
            "details": details,
            "memory_state": memory_state,
            "database_state": db_state,
            "statistics": stats,
            "before_state": before_state,
            "after_state": after_state
        }
        
        self.interactions.append(interaction)
        
        # Real-time console output
        print(f"\n🔴 RECORDING: {operation} at {self.timestamp()}")
        print(f"   Details: {details}")
        print(f"   Memory: {memory_state['total_records']} records ({memory_state['dirty_records']} dirty)")
        print(f"   Database: {db_state['total_records']} records")
        print(f"   Stats: H:{stats['cache_hits']} M:{stats['cache_misses']} F:{stats['flushes']} E:{stats['evictions']}")
        
        # Save to file immediately
        await self.save_to_file()
    
    async def get_memory_state(self):
        """Get current memory state"""
        total_records = sum(len(table) for table in self.db.cache.values())
        dirty_records = sum(len(keys) for keys in self.db.dirty_records.values())
        clean_records = total_records - dirty_records
        
        tables = {}
        for table_name, table_data in self.db.cache.items():
            if table_data:
                table_dirty = len(self.db.dirty_records[table_name])
                table_clean = len(table_data) - table_dirty
                
                # Sample records
                samples = []
                for key, entry in list(table_data.items())[:3]:
                    samples.append({
                        "key": key,
                        "dirty": entry.dirty,
                        "last_access": datetime.fromtimestamp(entry.last_access).strftime("%H:%M:%S"),
                        "last_updated": datetime.fromtimestamp(entry.last_updated).strftime("%H:%M:%S"),
                        "data": entry.data
                    })
                
                tables[table_name] = {
                    "total": len(table_data),
                    "dirty": table_dirty,
                    "clean": table_clean,
                    "samples": samples
                }
        
        return {
            "total_records": total_records,
            "dirty_records": dirty_records,
            "clean_records": clean_records,
            "tables": tables
        }
    
    async def get_db_state(self):
        """Get current database state"""
        if not hasattr(self.db, 'db_url') or 'mock://' in self.db.db_url:
            return {"total_records": 0, "tables": {}, "note": "Mock database"}
        
        try:
            conn = await asyncpg.connect(self.db.db_url)
            
            # Get all memdb tables
            tables_query = """
            SELECT tablename FROM pg_tables 
            WHERE tablename LIKE 'memdb_%' 
            ORDER BY tablename
            """
            tables = await conn.fetch(tables_query)
            
            total_records = 0
            table_info = {}
            
            for table_row in tables:
                table_name = table_row['tablename']
                
                # Get record count
                count_result = await conn.fetchrow(f"SELECT COUNT(*) as count FROM {table_name}")
                record_count = count_result['count']
                total_records += record_count
                
                # Get recent records
                recent_query = f"""
                SELECT key, data, updated_at 
                FROM {table_name} 
                ORDER BY updated_at DESC 
                LIMIT 3
                """
                recent_records = await conn.fetch(recent_query)
                
                samples = []
                for row in recent_records:
                    samples.append({
                        "key": row['key'],
                        "data": row['data'],
                        "updated_at": row['updated_at'].strftime("%H:%M:%S") if row['updated_at'] else None
                    })
                
                table_info[table_name] = {
                    "count": record_count,
                    "samples": samples
                }
            
            await conn.close()
            
            return {
                "total_records": total_records,
                "tables": table_info
            }
            
        except Exception as e:
            return {"total_records": 0, "tables": {}, "error": str(e)}
    
    async def save_to_file(self):
        """Save interactions to JSON file"""
        try:
            with open(self.output_file, 'w') as f:
                json.dump({
                    "session_info": {
                        "session_id": self.session_id,
                        "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                        "total_interactions": len(self.interactions),
                        "duration_seconds": self.elapsed_time()
                    },
                    "interactions": self.interactions
                }, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save interactions: {e}")

async def test_with_recording():
    """Test MemDB with real-time recording"""
    
    # Get configuration
    db_url = os.getenv('PG_DSN', 'mock://test')
    flush_interval = int(os.getenv('FLUSH_INTERVAL', 10))
    idle_ttl = int(os.getenv('IDLE_TTL', 30))
    max_connections = int(os.getenv('MAX_CONNECTIONS', 5))
    
    print("🎬 STARTING REAL-TIME RECORDING SESSION")
    print(f"📊 Database: {db_url}")
    print(f"⏱️  Settings: Flush={flush_interval}s, Evict={idle_ttl}s")
    print(f"📝 Recording to: interaction_log.json")
    
    # Create MemDB
    db = MemDB(
        db_url=db_url,
        flush_interval=flush_interval,
        evict_interval=idle_ttl,
        max_connections=max_connections
    )
    
    # Create recorder
    recorder = RealtimeRecorder(db)
    
    try:
        # Start database
        await db.start()
        await recorder.record_interaction("DATABASE_START", "MemDB initialized and connected")
        
        # Create tables
        await db.create_table("users", {"name": "string", "email": "string"})
        await recorder.record_interaction("CREATE_TABLE", {"table": "users", "schema": {"name": "string", "email": "string"}})
        
        await db.create_table("sessions", {"user_id": "string", "status": "string"})
        await recorder.record_interaction("CREATE_TABLE", {"table": "sessions", "schema": {"user_id": "string", "status": "string"}})
        
        # Insert data with recording
        for i in range(5):
            user_data = {"name": f"User {i}", "email": f"user{i}@test.com"}
            await db.insert("users", f"user_{i}", user_data)
            await recorder.record_interaction("INSERT", {"table": "users", "key": f"user_{i}", "data": user_data})
            
            session_data = {"user_id": f"user_{i}", "status": "active"}
            await db.insert("sessions", f"session_{i}", session_data)
            await recorder.record_interaction("INSERT", {"table": "sessions", "key": f"session_{i}", "data": session_data})
        
        # Test cache reads
        for i in [0, 2, 4]:
            result = await db.get("users", f"user_{i}")
            await recorder.record_interaction("CACHE_READ", {"table": "users", "key": f"user_{i}", "found": result is not None})
        
        # Wait for automatic flush
        print(f"\n⏰ Waiting for automatic flush ({flush_interval} seconds)...")
        
        # Start background tasks
        import memdb_tasks
        bg_task = asyncio.create_task(memdb_tasks.start_background_tasks(db))
        
        # Record during wait
        for i in range(flush_interval + 2):
            await asyncio.sleep(1)
            if i % 3 == 0:  # Record every 3 seconds
                await recorder.record_interaction("WAITING", {"seconds_elapsed": i, "waiting_for": "auto_flush"})
        
        await recorder.record_interaction("AUTO_FLUSH_COMPLETED", "Background flush should have occurred")
        
        # Add more data
        for i in range(5, 8):
            user_data = {"name": f"New User {i}", "email": f"newuser{i}@test.com"}
            await db.insert("users", f"user_{i}", user_data)
            await recorder.record_interaction("INSERT_AFTER_FLUSH", {"table": "users", "key": f"user_{i}", "data": user_data})
        
        # Manual flush
        await db.flush()
        await recorder.record_interaction("MANUAL_FLUSH", "Explicitly flushed all dirty records")
        
        # Test eviction
        print(f"\n⏰ Waiting for eviction ({idle_ttl} seconds)...")
        
        # Make some records old
        current_time = time.time()
        evicted_keys = []
        for table_name in db.cache:
            for key, entry in list(db.cache[table_name].items())[:3]:
                if not entry.dirty:
                    entry.last_access = current_time - (idle_ttl + 5)
                    evicted_keys.append(f"{table_name}:{key}")
        
        await recorder.record_interaction("PREPARE_EVICTION", {"marked_old": evicted_keys})
        
        # Wait for eviction
        await asyncio.sleep(idle_ttl + 2)
        
        await recorder.record_interaction("EVICTION_COMPLETED", "Idle records should have been evicted")
        
        # Test cache miss (read evicted data)
        result = await db.get("users", "user_0")
        await recorder.record_interaction("CACHE_MISS_RECOVERY", {"table": "users", "key": "user_0", "loaded_from_db": result is not None})
        
        # Cancel background tasks
        bg_task.cancel()
        try:
            await bg_task
        except asyncio.CancelledError:
            pass
        
        await recorder.record_interaction("BACKGROUND_TASKS_STOPPED", "Background flush/eviction tasks cancelled")
        
        # Final state
        await recorder.record_interaction("SESSION_END", "Recording session completed")
        
        print(f"\n🎬 RECORDING COMPLETED!")
        print(f"📊 Total interactions recorded: {len(recorder.interactions)}")
        print(f"⏱️  Session duration: {recorder.elapsed_time():.1f} seconds")
        print(f"📝 Saved to: {recorder.output_file}")
        
    except Exception as e:
        await recorder.record_interaction("ERROR", {"error": str(e), "type": type(e).__name__})
        logger.error(f"Test failed: {e}")
        raise
    
    finally:
        await db.stop()
        await recorder.record_interaction("DATABASE_STOP", "MemDB stopped and cleaned up")

if __name__ == "__main__":
    asyncio.run(test_with_recording())