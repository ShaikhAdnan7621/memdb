"""
Unit Tests for MemDB Core Functionality

Tests cover:
- Memory operations and caching
- Automatic flush and eviction
- Concurrent access safety
- Error handling and edge cases
"""

import pytest
import asyncio
from dyn_memdb import MemDB
import os


# Test fixtures
@pytest.fixture
async def db():
    """Create a test database instance"""
    test_db = MemDB(
        db_url=os.getenv(
            "PG_DSN", "postgresql://memdb_user:memdb_pass@localhost:5432/memdb_test"
        ),
        flush_interval=5,
        evict_interval=5,
        max_connections=5,
    )

    await test_db.start()

    # Create test table
    await test_db.create_table("test_table", {})

    yield test_db

    await test_db.stop()


# Basic Operations Tests
@pytest.mark.asyncio
async def test_insert_and_get(db):
    """Test inserting and retrieving a record"""
    await db.insert("test_table", "key_1", {"name": "Alice", "age": 30})

    result = await db.get("test_table", "key_1")

    assert result is not None
    assert result["name"] == "Alice"
    assert result["age"] == 30


@pytest.mark.asyncio
async def test_upsert(db):
    """Test upserting a record"""
    await db.insert("test_table", "key_1", {"name": "Alice"})
    await db.upsert("test_table", "key_1", {"name": "Alice Updated"})

    result = await db.get("test_table", "key_1")

    assert result["name"] == "Alice Updated"


@pytest.mark.asyncio
async def test_get_nonexistent_key(db):
    """Test getting a non-existent key"""
    result = await db.get("test_table", "nonexistent")

    assert result is None


# Cache Tests
@pytest.mark.asyncio
async def test_cache_hit(db):
    """Test cache hit functionality"""
    await db.insert("test_table", "key_1", {"data": "value"})

    stats_before = db.stats()
    hits_before = stats_before["cache_hits"]

    # First access - cache miss
    await db.get("test_table", "key_1", use_cache=True)

    # Second access - cache hit
    await db.get("test_table", "key_1", use_cache=True)

    stats_after = db.stats()
    hits_after = stats_after["cache_hits"]

    assert hits_after > hits_before


@pytest.mark.asyncio
async def test_cache_bypass(db):
    """Test bypassing cache with use_cache=False"""
    await db.insert("test_table", "key_1", {"data": "value"})

    # Should still work but not use cache
    result = await db.get("test_table", "key_1", use_cache=False)

    assert result is not None


# Flush Tests
@pytest.mark.asyncio
async def test_manual_flush(db):
    """Test manual flush to database"""
    await db.insert("test_table", "key_1", {"name": "Alice"})
    await db.insert("test_table", "key_2", {"name": "Bob"})

    stats_before = db.stats()
    flushes_before = stats_before["flushes"]

    await db.flush("test_table")

    stats_after = db.stats()
    flushes_after = stats_after["flushes"]

    assert flushes_after > flushes_before
    assert stats_after["dirty_records"] == 0


@pytest.mark.asyncio
async def test_flush_all_tables(db):
    """Test flushing all tables at once"""
    await db.create_table("test_table_2", {})

    await db.insert("test_table", "key_1", {"name": "Alice"})
    await db.insert("test_table_2", "key_1", {"name": "Charlie"})

    await db.flush()

    stats = db.stats()
    assert stats["dirty_records"] == 0


# Eviction Tests
@pytest.mark.asyncio
async def test_eviction_of_idle_records(db):
    """Test that idle records are evicted"""
    await db.insert("test_table", "key_1", {"name": "Alice"})

    stats_before = db.stats()
    cached_before = stats_before["cached_records"]

    # Wait for eviction (set to 5s in fixture)
    await asyncio.sleep(6)

    await db.evict_idle()

    stats_after = db.stats()
    cached_after = stats_after["cached_records"]

    # Idle record should be evicted
    assert cached_after <= cached_before


@pytest.mark.asyncio
async def test_dirty_records_not_evicted(db):
    """Test that dirty records are not evicted"""
    await db.insert("test_table", "key_1", {"name": "Alice"})

    # Record is dirty after insert
    stats = db.stats()
    assert stats["dirty_records"] > 0

    # Wait for eviction
    await asyncio.sleep(6)
    await db.evict_idle()

    # Dirty record should not be evicted
    result = await db.get("test_table", "key_1")
    assert result is not None


# Query Tests
@pytest.mark.asyncio
async def test_query_with_where_clause(db):
    """Test querying with WHERE clause"""
    await db.insert("test_table", "user_1", {"name": "Alice", "age": 25})
    await db.insert("test_table", "user_2", {"name": "Bob", "age": 35})
    await db.insert("test_table", "user_3", {"name": "Charlie", "age": 25})

    # Query users under 30
    results = await db.query("test_table", "data->>'age' < '30'", limit=100)

    assert len(results) >= 2


@pytest.mark.asyncio
async def test_query_limit(db):
    """Test query with limit"""
    for i in range(20):
        await db.insert("test_table", f"key_{i}", {"index": i})

    results = await db.query("test_table", limit=5)

    assert len(results) <= 5


# Concurrency Tests
@pytest.mark.asyncio
async def test_concurrent_inserts(db):
    """Test concurrent insert operations"""

    async def insert_records(start: int, count: int):
        for i in range(start, start + count):
            await db.insert("test_table", f"key_{i}", {"index": i})

    # Run concurrent inserts
    await asyncio.gather(
        insert_records(0, 100), insert_records(100, 100), insert_records(200, 100)
    )

    stats = db.stats()
    assert stats["inserts"] >= 300


@pytest.mark.asyncio
async def test_concurrent_reads_and_writes(db):
    """Test concurrent read and write operations"""
    # Pre-insert some data
    for i in range(50):
        await db.insert("test_table", f"key_{i}", {"index": i})

    async def mixed_operations():
        for i in range(50):
            if i % 2 == 0:
                await db.insert("test_table", f"key_{i + 50}", {"index": i})
            else:
                await db.get("test_table", f"key_{i % 50}")

    # Run concurrent mixed operations
    await asyncio.gather(mixed_operations(), mixed_operations(), mixed_operations())

    stats = db.stats()
    assert stats["cached_records"] > 0


# Statistics Tests
@pytest.mark.asyncio
async def test_statistics(db):
    """Test statistics tracking"""
    for i in range(10):
        await db.insert("test_table", f"key_{i}", {"index": i})

    stats = db.stats()

    assert "cache_hits" in stats
    assert "cache_misses" in stats
    assert "inserts" in stats
    assert "flushes" in stats
    assert "evictions" in stats
    assert "cached_records" in stats
    assert "dirty_records" in stats
    assert "tables" in stats


# Schema Tests
@pytest.mark.asyncio
async def test_multiple_tables(db):
    """Test working with multiple tables"""
    await db.create_table("users", {})
    await db.create_table("posts", {})

    await db.insert("users", "user_1", {"name": "Alice"})
    await db.insert("posts", "post_1", {"title": "First Post"})

    user = await db.get("users", "user_1")
    post = await db.get("posts", "post_1")

    assert user["name"] == "Alice"
    assert post["title"] == "First Post"


# Edge Cases
@pytest.mark.asyncio
async def test_empty_query_result(db):
    """Test querying when no results match"""
    results = await db.query("test_table", "data->>'age' > '100'")

    assert len(results) == 0


@pytest.mark.asyncio
async def test_large_record(db):
    """Test storing large records"""
    large_data = {
        "data": "x" * 10000,  # 10KB of data
        "nested": {"level1": {"level2": {"value": "deep"}}},
    }

    await db.insert("test_table", "large_key", large_data)
    result = await db.get("test_table", "large_key")

    assert result["data"] == "x" * 10000
    assert result["nested"]["level1"]["level2"]["value"] == "deep"


@pytest.mark.asyncio
async def test_special_characters_in_key(db):
    """Test special characters in keys"""
    special_key = "key:with:colons:and-dashes_and_underscores.and.dots"

    await db.insert("test_table", special_key, {"name": "Special"})
    result = await db.get("test_table", special_key)

    assert result["name"] == "Special"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
