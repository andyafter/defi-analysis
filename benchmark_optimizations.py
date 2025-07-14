#!/usr/bin/env python3
"""Simple benchmark to measure RPC optimization performance improvements."""

import asyncio
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from data_fetcher import DataFetcher
from src.config import ConfigManager

# Test parameters
TEST_POOL = "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"
TEST_BLOCKS = list(range(17618642, 17618652))  # 10 blocks
EVENT_BLOCK_RANGE = (17618642, 17618742)  # 100 blocks


async def benchmark_pool_state_fetching():
    """Benchmark pool state fetching with optimizations."""
    print("\n📊 Benchmarking Pool State Fetching (10 blocks)")
    print("=" * 50)
    
    rpc_url = os.getenv("ETH_RPC_URL")
    if not rpc_url:
        print("❌ ETH_RPC_URL not set")
        return
    
    # Load config
    config = ConfigManager('config.yaml').load()
    
    # Test with optimizations
    print("\nWith optimizations (parallel + connection pooling):")
    optimized_fetcher = DataFetcher(
        rpc_url=rpc_url,
        max_workers=config.performance.max_workers,
        max_concurrent_requests=config.performance.max_concurrent_requests
    )
    
    start_time = time.time()
    tasks = [
        optimized_fetcher.get_pool_state(TEST_POOL, block)
        for block in TEST_BLOCKS
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    optimized_time = time.time() - start_time
    
    successful = sum(1 for r in results if not isinstance(r, Exception))
    print(f"  ✅ Fetched {successful}/{len(TEST_BLOCKS)} pool states")
    print(f"  Total time: {optimized_time:.2f}s")
    print(f"  Average per block: {optimized_time/len(TEST_BLOCKS):.2f}s")
    print(f"  Blocks per second: {len(TEST_BLOCKS)/optimized_time:.1f}")
    
    # Test without optimizations (sequential)
    print("\nWithout optimizations (sequential):")
    basic_fetcher = DataFetcher(rpc_url, max_workers=1, max_concurrent_requests=1)
    
    start_time = time.time()
    successful = 0
    for block in TEST_BLOCKS:
        try:
            await basic_fetcher.get_pool_state(TEST_POOL, block)
            successful += 1
        except:
            pass
    basic_time = time.time() - start_time
    
    print(f"  ✅ Fetched {successful}/{len(TEST_BLOCKS)} pool states")
    print(f"  Total time: {basic_time:.2f}s")
    print(f"  Average per block: {basic_time/len(TEST_BLOCKS):.2f}s")
    print(f"  Blocks per second: {len(TEST_BLOCKS)/basic_time:.1f}")
    
    # Calculate improvement
    improvement = (basic_time / optimized_time - 1) * 100
    print(f"\n🚀 Performance improvement: {improvement:.1f}% faster")


async def benchmark_event_fetching():
    """Benchmark event fetching with optimizations."""
    print("\n📈 Benchmarking Event Fetching (100 blocks)")
    print("=" * 50)
    
    rpc_url = os.getenv("ETH_RPC_URL")
    if not rpc_url:
        return
    
    # Load config
    config = ConfigManager('config.yaml').load()
    
    # Test with optimized chunking
    print("\nWith optimizations (parallel chunks):")
    optimized_fetcher = DataFetcher(
        rpc_url=rpc_url,
        max_workers=config.performance.max_workers,
        max_concurrent_requests=config.performance.max_concurrent_requests
    )
    
    start_time = time.time()
    events = await optimized_fetcher.get_swap_events(
        TEST_POOL,
        EVENT_BLOCK_RANGE[0],
        EVENT_BLOCK_RANGE[1],
        chunk_size=config.performance.chunk_size
    )
    optimized_time = time.time() - start_time
    
    print(f"  ✅ Fetched {len(events)} events")
    print(f"  Total time: {optimized_time:.2f}s")
    print(f"  Events per second: {len(events)/optimized_time:.1f}")
    
    # Test with smaller chunks (less parallel)
    print("\nWith smaller chunks (less parallelism):")
    start_time = time.time()
    events_small = await optimized_fetcher.get_swap_events(
        TEST_POOL,
        EVENT_BLOCK_RANGE[0],
        EVENT_BLOCK_RANGE[1],
        chunk_size=500  # Smaller chunks
    )
    small_chunk_time = time.time() - start_time
    
    print(f"  ✅ Fetched {len(events_small)} events")
    print(f"  Total time: {small_chunk_time:.2f}s")
    print(f"  Events per second: {len(events_small)/small_chunk_time:.1f}")
    
    # Calculate improvement
    improvement = (small_chunk_time / optimized_time - 1) * 100
    print(f"\n🚀 Large chunk improvement: {improvement:.1f}% faster")


async def main():
    """Run benchmarks."""
    print("=" * 60)
    print("🏁 RPC OPTIMIZATION BENCHMARKS")
    print("=" * 60)
    
    await benchmark_pool_state_fetching()
    await benchmark_event_fetching()
    
    print("\n" + "=" * 60)
    print("✅ Benchmarks complete!")
    print("\nKey improvements from optimizations:")
    print("  • Connection pooling reduces connection overhead")
    print("  • Parallel requests utilize bandwidth efficiently")
    print("  • Rate limiting prevents RPC endpoint overload")
    print("  • Adaptive chunking optimizes for different block ranges")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main()) 