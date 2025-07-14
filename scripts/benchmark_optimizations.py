#!/usr/bin/env python3
"""Simple benchmark to measure RPC optimization performance improvements."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.blockchain import DataFetcher
from src.config import ConfigManager
from src.data.cache import FileCache

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
    
    # Create cache to help with rate limiting
    cache = FileCache("cache", default_ttl=86400)
    
    # Test with optimizations
    print("\nWith optimizations (parallel + connection pooling):")
    optimized_fetcher = DataFetcher(
        rpc_url=rpc_url,
        max_workers=10,  # Reduced for rate limiting
        max_concurrent_requests=5,  # Reduced to avoid 429 errors
        cache=cache
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
    try:
        basic_fetcher = DataFetcher(
            rpc_url=rpc_url, 
            max_workers=1, 
            max_concurrent_requests=1,
            cache=None  # No cache for fair comparison
        )
        
        start_time = time.time()
        successful = 0
        for i, block in enumerate(TEST_BLOCKS):
            try:
                await basic_fetcher.get_pool_state(TEST_POOL, block)
                successful += 1
                # Add small delay to avoid rate limiting
                if i < len(TEST_BLOCKS) - 1:
                    await asyncio.sleep(0.2)
            except Exception as e:
                print(f"    Error on block {block}: {str(e)[:50]}...")
        basic_time = time.time() - start_time
    except Exception as e:
        print(f"  ❌ Sequential test failed: {e}")
        basic_time = 0
        successful = 0
    
    print(f"  ✅ Fetched {successful}/{len(TEST_BLOCKS)} pool states")
    if basic_time > 0:
        print(f"  Total time: {basic_time:.2f}s")
        print(f"  Average per block: {basic_time/len(TEST_BLOCKS):.2f}s")
        print(f"  Blocks per second: {len(TEST_BLOCKS)/basic_time:.1f}")
    
    # Calculate improvement
    if optimized_time > 0 and basic_time > 0:
        improvement = basic_time / optimized_time
        print(f"\n🚀 Performance improvement: {improvement:.1f}x faster with optimizations")
    
    # Test cache performance
    print("\n📊 Testing cache performance...")
    cache_start = time.time()
    cached_results = await asyncio.gather(*[
        optimized_fetcher.get_pool_state(TEST_POOL, block)
        for block in TEST_BLOCKS[:3]  # Test just 3 blocks
    ], return_exceptions=True)
    cache_time = time.time() - cache_start
    cached_success = sum(1 for r in cached_results if not isinstance(r, Exception))
    print(f"  ✅ Cache test: {cached_success}/3 blocks in {cache_time:.2f}s")


async def benchmark_event_fetching():
    """Benchmark event fetching with optimizations."""
    print("\n📈 Benchmarking Event Fetching (100 blocks)")
    print("=" * 50)
    
    rpc_url = os.getenv("ETH_RPC_URL")
    if not rpc_url:
        return
    
    # Load config
    config = ConfigManager('config.yaml').load()
    
    # Create cache
    cache = FileCache("cache", default_ttl=86400)
    
    # Test with optimized chunking
    print("\nWith optimizations (parallel chunks):")
    optimized_fetcher = DataFetcher(
        rpc_url=rpc_url,
        max_workers=10,
        max_concurrent_requests=5,
        cache=cache
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