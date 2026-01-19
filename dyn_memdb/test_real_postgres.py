"""
Real PostgreSQL Test - Memory vs Database Comparison
Uses actual PostgreSQL database and shows real-time state comparison
"""

import asyncio
import logging
import time
import os
from datetime import datetime
from memdb import MemDB
import asyncpg

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealDatabaseTracker:
    def __init__(self, db, db_url):
        self.db = db
        self.db_url = db_url
        self.start_time = time.time()
        self.step = 0
    
    def elapsed_time(self):
        return time.time() - self.start_time
    
    def timestamp(self):
        return datetime.now().strftime("%H:%M:%S")
    
    async def get_real_db_state(self):
        """Query actual PostgreSQL database state"""
        try:
            conn = await asyncpg.connect(self.db_url)
            
            # Get all memdb tables
            tables_query = """
            SELECT tablename FROM pg_tables 
            WHERE tablename LIKE 'memdb_%' 
            ORDER BY tablename
            """
            tables = await conn.fetch(tables_query)
            
            db_state = {}
            total_records = 0
            
            for table_row in tables:
                table_name = table_row['tablename']
                
                # Get record count and sample data
                count_query = f"SELECT COUNT(*) as count FROM {table_name}"
                count_result = await conn.fetchrow(count_query)
                record_count = count_result['count']
                total_records += record_count
                
                # Get sample records
                sample_query = f"""
                SELECT key, data, created_at, updated_at 
                FROM {table_name} 
                ORDER BY updated_at DESC 
                LIMIT 3
                """
                samples = await conn.fetch(sample_query)
                
                db_state[table_name] = {
                    'count': record_count,
                    'samples': [
                        {
                            'key': row['key'],
                            'data': row['data'],  # row['data'] is already a dict from JSONB
                            'updated_at': row['updated_at'].strftime("%H:%M:%S") if row['updated_at'] else None
                        }
                        for row in samples
                    ]
                }
            
            await conn.close()
            return db_state, total_records
            
        except Exception as e:
            logger.error(f"Error querying database: {e}")
            return {}, 0
    
    async def log_comparison(self, event_description):
        """Compare memory state with actual database state"""
        self.step += 1
        elapsed = self.elapsed_time()
        
        print(f"\n{'='*80}")
        print(f"STEP {self.step}: {event_description}")
        print(f"Time: {self.timestamp()} (Elapsed: {elapsed:.1f}s)")
        print(f"{'='*80}")
        
        # Get memory state
        total_memory = sum(len(table) for table in self.db.cache.values())
        total_dirty = sum(len(keys) for keys in self.db.dirty_records.values())
        total_clean = total_memory - total_dirty
        
        # Get real database state
        db_state, total_db_records = await self.get_real_db_state()
        
        print(f"📱 MEMORY STATE:")
        print(f"   Total Records: {total_memory} ({total_dirty} dirty, {total_clean} clean)")
        
        for table_name, table_data in self.db.cache.items():
            if table_data:
                dirty_in_table = len(self.db.dirty_records[table_name])
                clean_in_table = len(table_data) - dirty_in_table
                print(f"   Table '{table_name}': {len(table_data)} records ({dirty_in_table} dirty, {clean_in_table} clean)")
                
                # Show sample records from memory
                sample_count = min(2, len(table_data))
                for i, (key, entry) in enumerate(list(table_data.items())[:sample_count]):
                    status = "🔴 DIRTY" if entry.dirty else "🟢 CLEAN"
                    last_access = datetime.fromtimestamp(entry.last_access).strftime("%H:%M:%S")
                    print(f"      {key}: {status} (accessed: {last_access})")
        
        print(f"\n💾 REAL DATABASE STATE:")
        print(f"   Total Records: {total_db_records}")
        
        for table_name, table_info in db_state.items():
            print(f"   Table '{table_name}': {table_info['count']} records")
            for sample in table_info['samples'][:2]:  # Show 2 samples
                updated_time = sample['updated_at'] or "N/A"
                print(f"      {sample['key']}: saved at {updated_time}")
        
        # Show comparison
        print(f"\n🔄 MEMORY vs DATABASE COMPARISON:")
        memory_vs_db = total_memory - total_db_records
        if memory_vs_db > 0:
            print(f"   📊 {memory_vs_db} records in memory NOT YET saved to database")
        elif memory_vs_db < 0:
            print(f"   📊 {abs(memory_vs_db)} records in database NOT in memory (evicted)")
        else:
            print(f"   ✅ Memory and database are in sync ({total_memory} records)")
        
        # Statistics
        stats = self.db.stats()
        print(f"\n📈 STATISTICS:")
        print(f"   Operations: {stats['inserts']} inserts, {stats['cache_hits']} hits, {stats['cache_misses']} misses")
        print(f"   Persistence: {stats['flushes']} flushes, {stats['evictions']} evictions")

async def test_real_postgres_flow():
    """Test with real PostgreSQL database"""
    
    # Get configuration from environment
    db_url = os.getenv('PG_DSN')
    flush_interval = int(os.getenv('FLUSH_INTERVAL', 10))
    idle_ttl = int(os.getenv('IDLE_TTL', 30))
    max_connections = int(os.getenv('MAX_CONNECTIONS', 5))
    
    if not db_url:
        print("❌ Error: PG_DSN not found in .env file")
        return
    
    print("🚀 REAL POSTGRESQL TEST")
    print(f"📊 Database: {db_url.split('@')[1] if '@' in db_url else db_url}")
    print(f"⏱️  Settings: Flush={flush_interval}s, Evict={idle_ttl}s, Connections={max_connections}")
    
    # Create MemDB with real database
    db = MemDB(
        db_url=db_url,
        flush_interval=flush_interval,
        evict_interval=idle_ttl,
        max_connections=max_connections
    )
    
    tracker = RealDatabaseTracker(db, db_url)
    
    try:
        await db.start()
        print("✅ Connected to real PostgreSQL database")
        
        # Step 1: Initial state
        await tracker.log_comparison("System initialization")
        
        # Step 2: Create tables
        await db.create_table("test_users", {"name": "string", "email": "string"})
        await db.create_table("test_calls", {"caller_id": "string", "status": "string"})
        await tracker.log_comparison("Tables created")
        
        # Step 3: Insert test data
        print(f"\n⏰ {tracker.timestamp()}: Inserting 20 test records...")
        
        # Insert users
        for i in range(10):
            await db.insert("test_users", f"user_{i:03d}", {
                "name": f"Test User {i}",
                "email": f"user{i}@test.com"
            })
        
        # Insert calls
        for i in range(10):
            await db.insert("test_calls", f"call_{i:03d}", {
                "caller_id": f"+123456789{i}",
                "status": "active" if i % 2 == 0 else "completed"
            })
        
        await tracker.log_comparison("20 records inserted (all in memory)")
        
        # Step 4: Test cache performance
        print(f"\n⏰ {tracker.timestamp()}: Testing cache reads...")
        for i in [0, 2, 5, 8]:
            await db.get("test_users", f"user_{i:03d}")
            await db.get("test_calls", f"call_{i:03d}")
        
        await tracker.log_comparison("Cache performance tested")
        
        # Step 5: Wait for automatic flush
        print(f"\n⏰ {tracker.timestamp()}: Waiting for automatic flush ({flush_interval} seconds)...")
        
        # Start background tasks
        import memdb_tasks
        bg_task = asyncio.create_task(memdb_tasks.start_background_tasks(db))
        
        # Wait with countdown
        for remaining in range(flush_interval + 5, 0, -5):
            await asyncio.sleep(5)
            elapsed = tracker.elapsed_time()
            print(f"   ⏳ {tracker.timestamp()}: Waiting... {max(0, remaining-5)}s remaining (elapsed: {elapsed:.1f}s)")
            
            # Check if flush happened
            stats = db.stats()
            if stats['flushes'] > 0:
                print(f"      ✅ Flush detected! {stats['flushes']} records flushed")
                break
        
        await tracker.log_comparison("After automatic flush")
        
        # Step 6: Add more data
        print(f"\n⏰ {tracker.timestamp()}: Adding 5 more records...")
        for i in range(10, 15):
            await db.insert("test_users", f"user_{i:03d}", {
                "name": f"New User {i}",
                "email": f"newuser{i}@test.com"
            })
        
        await tracker.log_comparison("5 new records added")
        
        # Step 7: Manual flush
        print(f"\n⏰ {tracker.timestamp()}: Manual flush...")
        await db.flush()
        await tracker.log_comparison("Manual flush completed")
        
        # Step 8: Wait for eviction
        print(f"\n⏰ {tracker.timestamp()}: Waiting for eviction ({idle_ttl} seconds)...")
        
        # Make some records old for eviction
        current_time = time.time()
        for table_name in db.cache:
            for key, entry in list(db.cache[table_name].items())[:10]:
                if not entry.dirty:
                    entry.last_access = current_time - (idle_ttl + 5)
        
        # Wait for eviction
        await asyncio.sleep(idle_ttl + 5)
        
        await tracker.log_comparison("After eviction period")
        
        # Step 9: Test cache miss (read evicted data)
        print(f"\n⏰ {tracker.timestamp()}: Testing cache miss (reading evicted data)...")
        result = await db.get("test_users", "user_000")  # Should load from DB
        print(f"   📖 Loaded from database: {result['name']}")
        
        await tracker.log_comparison("Cache miss test completed")
        
        # Cancel background tasks
        bg_task.cancel()
        try:
            await bg_task
        except asyncio.CancelledError:
            pass
        
        # Final comparison
        await tracker.log_comparison("Final state")
        
        print(f"\n🎉 Test completed successfully!")
        print(f"⏱️  Total time: {tracker.elapsed_time():.1f} seconds")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise
    
    finally:
        await db.stop()

if __name__ == "__main__":
    asyncio.run(test_real_postgres_flow())