"""
Basic Usage Example - Getting Started with MemDB

This example shows the simplest way to use MemDB for caching
temporary data with eventual persistence.
"""

import asyncio
from dyn_memdb import MemDB


async def main():
    """Basic MemDB usage example"""

    # Initialize MemDB
    db = MemDB(
        db_url="postgresql://memdb_user:memdb_pass@localhost:5432/memdb_db",
        flush_interval=30,  # Auto-flush every 30 seconds
        evict_interval=60,  # Evict idle records after 60 seconds
        max_connections=5,
    )

    print("🚀 Starting MemDB...")
    await db.start()

    # Create a table
    print("📋 Creating table...")
    await db.create_table(
        "users", {"name": "string", "email": "string", "age": "integer"}
    )

    # Insert data (goes to memory immediately)
    print("📝 Inserting users...")
    await db.insert(
        "users", "user_001", {"name": "Alice", "email": "alice@example.com", "age": 28}
    )

    await db.insert(
        "users", "user_002", {"name": "Bob", "email": "bob@example.com", "age": 32}
    )

    await db.insert(
        "users",
        "user_003",
        {"name": "Charlie", "email": "charlie@example.com", "age": 25},
    )

    # Read data (from cache)
    print("📖 Reading from cache...")
    user1 = await db.get("users", "user_001")
    print(f"   User 1: {user1}")

    # Query data
    print("🔍 Querying data...")
    young_users = await db.query("users", "data->>'age' < '30'", limit=100)
    print(f"   Users under 30: {len(young_users)}")
    for user in young_users:
        print(f"   - {user}")

    # Get statistics
    print("📊 Database statistics:")
    stats = db.stats()
    print(f"   Cache hits: {stats['cache_hits']}")
    print(f"   Cache misses: {stats['cache_misses']}")
    print(f"   Cached records: {stats['cached_records']}")
    print(f"   Dirty records: {stats['dirty_records']}")
    print(f"   Total flushes: {stats['flushes']}")

    # Wait for automatic flush
    print("⏳ Waiting for auto-flush...")
    await asyncio.sleep(35)

    # Check updated stats
    stats = db.stats()
    print(f"   Records flushed: {stats['flushes']}")

    # Cleanup
    print("🛑 Shutting down MemDB...")
    await db.stop()
    print("✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())
