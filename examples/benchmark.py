"""
Benchmarking MemDB Performance

This script demonstrates the performance characteristics of MemDB
including throughput and latency measurements.
"""

import asyncio
import time
from dyn_memdb import MemDB


async def benchmark_writes(db: MemDB, count: int = 10000):
    """Benchmark write operations"""
    print(f"\n📊 Benchmarking {count} write operations...")

    await db.create_table("bench_writes", {})

    start = time.time()
    for i in range(count):
        await db.insert(
            "bench_writes",
            f"key_{i}",
            {"index": i, "data": f"value_{i}", "timestamp": time.time()},
        )
    end = time.time()

    elapsed = end - start
    throughput = count / elapsed

    print(f"   Total time: {elapsed:.2f}s")
    print(f"   Throughput: {throughput:,.0f} writes/sec")
    print(f"   Per-operation: {(elapsed / count) * 1000:.3f}ms")

    return throughput


async def benchmark_reads_cache(db: MemDB, count: int = 10000):
    """Benchmark read operations (cache hits)"""
    print(f"\n📊 Benchmarking {count} read operations (cache hits)...")

    # Insert data first
    await db.create_table("bench_reads", {})
    for i in range(100):  # Small dataset for cache testing
        await db.insert("bench_reads", f"key_{i}", {"index": i, "data": f"value_{i}"})

    # Clear stats
    db.stats_data["cache_hits"] = 0
    db.stats_data["cache_misses"] = 0

    start = time.time()
    for i in range(count):
        await db.get("bench_reads", f"key_{i % 100}", use_cache=True)
    end = time.time()

    elapsed = end - start
    throughput = count / elapsed

    stats = db.stats()
    cache_hits = stats["cache_hits"]
    cache_misses = stats["cache_misses"]

    print(f"   Total time: {elapsed:.2f}s")
    print(f"   Throughput: {throughput:,.0f} reads/sec")
    print(f"   Per-operation: {(elapsed / count) * 1000:.3f}ms")
    print(f"   Cache hits: {cache_hits}")
    print(f"   Cache misses: {cache_misses}")

    return throughput


async def benchmark_mixed_workload(db: MemDB, operations: int = 5000):
    """Benchmark mixed read/write operations"""
    print(f"\n📊 Benchmarking mixed workload ({operations} operations)...")

    await db.create_table("bench_mixed", {})

    # Reset stats
    db.stats_data["cache_hits"] = 0
    db.stats_data["cache_misses"] = 0
    db.stats_data["inserts"] = 0

    start = time.time()
    for i in range(operations):
        if i % 2 == 0:
            # Write operation
            await db.insert(
                "bench_mixed", f"key_{i}", {"index": i, "data": f"value_{i}"}
            )
        else:
            # Read operation
            await db.get("bench_mixed", f"key_{i - 1}", use_cache=True)
    end = time.time()

    elapsed = end - start
    throughput = operations / elapsed

    stats = db.stats()

    print(f"   Total time: {elapsed:.2f}s")
    print(f"   Throughput: {throughput:,.0f} ops/sec")
    print(f"   Per-operation: {(elapsed / operations) * 1000:.3f}ms")
    print(f"   Total inserts: {stats['inserts']}")
    print(f"   Cache hits: {stats['cache_hits']}")
    print(f"   Cache misses: {stats['cache_misses']}")

    return throughput


async def main():
    """Run all benchmarks"""
    print("=" * 60)
    print("MemDB Performance Benchmarking")
    print("=" * 60)

    db = MemDB(
        db_url="postgresql://memdb_user:memdb_pass@localhost:5432/memdb_db",
        flush_interval=3600,  # Don't auto-flush during benchmark
        evict_interval=3600,  # Don't auto-evict during benchmark
        max_connections=20,
    )

    await db.start()

    try:
        # Run benchmarks
        write_throughput = await benchmark_writes(db, 10000)
        read_throughput = await benchmark_reads_cache(db, 50000)
        mixed_throughput = await benchmark_mixed_workload(db, 10000)

        # Print summary
        print("\n" + "=" * 60)
        print("📈 Benchmark Summary")
        print("=" * 60)
        print(f"Write throughput:  {write_throughput:>15,.0f} ops/sec")
        print(f"Read throughput:   {read_throughput:>15,.0f} ops/sec")
        print(f"Mixed throughput:  {mixed_throughput:>15,.0f} ops/sec")

        # Print final stats
        print("\n📊 Final Database Statistics:")
        stats = db.stats()
        print(f"   Cached records: {stats['cached_records']}")
        print(f"   Dirty records: {stats['dirty_records']}")
        print(f"   Total tables: {stats['tables']}")

    finally:
        await db.stop()
        print("\n✅ Benchmarking complete!")


if __name__ == "__main__":
    asyncio.run(main())
