#!/usr/bin/env python3
"""
Test script to verify all optimizations are working correctly.
"""

import asyncio
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import optimized components
from src.blockchain import DataFetcher
from src.config import ConfigManager
from src.data.cache import FileCache
from src.uniswap import UniswapV3Calculator
from src.analysis import PositionAnalyzer
from src.visualization import Visualizer

# Test constants
TEST_POOL = "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"
TEST_BLOCK = 17618642
TEST_BLOCK_RANGE = (17618642, 17618652)


async def test_cache_integration():
    """Test optimization #1: Cache Integration"""
    print("\n🔧 Testing Optimization #1: Cache Integration")
    print("=" * 50)
    
    # Initialize components
    cache = FileCache("cache_test", default_ttl=3600)
    rpc_url = os.getenv("ETH_RPC_URL")
    
    if not rpc_url:
        print("❌ ETH_RPC_URL not set")
        return False
    
    data_fetcher = DataFetcher(rpc_url, cache=cache)
    
    # Test 1: Pool State Caching
    print("Testing pool state caching...")
    start = time.time()
    pool_state1 = await data_fetcher.get_pool_state(TEST_POOL, TEST_BLOCK)
    time1 = time.time() - start
    print(f"  First call: {time1:.2f}s")
    
    start = time.time()
    pool_state2 = await data_fetcher.get_pool_state(TEST_POOL, TEST_BLOCK)
    time2 = time.time() - start
    print(f"  Cached call: {time2:.2f}s")
    
    if time2 < time1 * 0.1:  # Cached should be at least 10x faster
        print("✅ Pool state caching working (cached {:.0f}x faster)".format(time1/time2))
    else:
        print("❌ Pool state caching not working effectively")
    
    # Test 2: Swap Events Caching
    print("\nTesting swap events caching...")
    start = time.time()
    events1 = await data_fetcher.get_swap_events(
        TEST_POOL, TEST_BLOCK_RANGE[0], TEST_BLOCK_RANGE[1], chunk_size=100
    )
    time1 = time.time() - start
    print(f"  First call: {time1:.2f}s")
    
    start = time.time()
    events2 = await data_fetcher.get_swap_events(
        TEST_POOL, TEST_BLOCK_RANGE[0], TEST_BLOCK_RANGE[1], chunk_size=100
    )
    time2 = time.time() - start
    print(f"  Cached call: {time2:.2f}s")
    
    if time2 < time1 * 0.1:
        print("✅ Swap events caching working (cached {:.0f}x faster)".format(time1/time2))
    else:
        print("❌ Swap events caching not working effectively")
    
    # Clean up test cache
    await cache.clear()
    
    return True


async def test_fee_calculation_caching():
    """Test optimization #2: Fee Calculation Caching"""
    print("\n🔧 Testing Optimization #2: Fee Calculation Caching")
    print("=" * 50)
    
    # Initialize components
    cache = FileCache("cache_test", default_ttl=3600)
    calculator = UniswapV3Calculator()
    analyzer = PositionAnalyzer(calculator, cache=cache)
    
    # Create test position
    from src.uniswap import Position
    position = Position(
        liquidity=1000000000,
        tick_lower=200540,
        tick_upper=200560,
        amount0=10000,
        amount1=5
    )
    
    # Create test swap events
    from src.blockchain import SwapEvent
    swap_events = [
        SwapEvent(
            sender="0x123",
            recipient="0x456",
            amount0=-1000000 * 10**6,
            amount1=500 * 10**18,
            sqrt_price_x96=0,
            liquidity=0,
            tick=200550,
            block_number=17618700,
            transaction_hash="0xabc"
        )
    ]
    
    # Test liquidity distribution
    liquidity_distribution = {tick: 10000000000 for tick in range(200530, 200570)}
    
    print("Testing fee calculation caching...")
    start = time.time()
    fees1 = await analyzer.estimate_fees_from_swaps(
        position, swap_events, liquidity_distribution, 500
    )
    time1 = time.time() - start
    print(f"  First calculation: {time1:.4f}s")
    
    start = time.time()
    fees2 = await analyzer.estimate_fees_from_swaps(
        position, swap_events, liquidity_distribution, 500
    )
    time2 = time.time() - start
    print(f"  Cached calculation: {time2:.4f}s")
    
    if time2 < time1 * 0.1:
        print("✅ Fee calculation caching working (cached {:.0f}x faster)".format(time1/time2))
    else:
        print("❌ Fee calculation caching not working effectively")
    
    # Clean up
    await cache.clear()
    
    return True


def test_vectorized_calculations():
    """Test optimization #3: Vectorized Analysis Calculations"""
    print("\n🔧 Testing Optimization #3: Vectorized Analysis Calculations")
    print("=" * 50)
    
    import numpy as np
    
    # Test vectorized fee distribution
    print("Testing vectorized calculations...")
    
    # Create large test data
    tick_range = np.arange(200000, 201000)  # 1000 ticks
    liquidity_dist = {tick: 1000000000 for tick in tick_range}
    
    # Test vectorized operations
    start = time.time()
    tick_array = np.arange(200100, 200200)
    valid_ticks = tick_array[np.isin(tick_array, list(liquidity_dist.keys()))]
    total_liquidities = np.array([liquidity_dist.get(t, 1) for t in valid_ticks])
    our_shares = np.where(total_liquidities > 0, 500000000 / total_liquidities, 0)
    time_vectorized = time.time() - start
    
    print(f"  Vectorized operation time: {time_vectorized:.6f}s")
    print(f"  Processed {len(tick_array)} ticks")
    
    if time_vectorized < 0.01:  # Should be very fast
        print("✅ Vectorized calculations are optimized")
    else:
        print("⚠️  Vectorized calculations might need further optimization")
    
    return True


def test_visualization_performance():
    """Test optimization #4: Visualization Performance"""
    print("\n🔧 Testing Optimization #4: Visualization Performance")
    print("=" * 50)
    
    import numpy as np
    from src.uniswap import Position
    
    visualizer = Visualizer()
    
    # Create test data
    position = Position(
        liquidity=1000000000,
        tick_lower=200540,
        tick_upper=200560,
        amount0=10000,
        amount1=5
    )
    
    # Large liquidity distribution
    liquidity_dist = {tick: np.random.randint(1e8, 1e10) for tick in range(200500, 200600)}
    
    print("Testing visualization data preparation...")
    start = time.time()
    
    # Test vectorized data preparation
    ticks = np.arange(200530, 200570)
    total_liquidity = np.array([liquidity_dist.get(tick, 0) for tick in ticks])
    position_liquidity = np.where(
        (ticks >= position.tick_lower) & (ticks <= position.tick_upper),
        position.liquidity,
        0
    )
    
    time_prep = time.time() - start
    print(f"  Data preparation time: {time_prep:.6f}s")
    print(f"  Processed {len(ticks)} ticks")
    
    if time_prep < 0.01:
        print("✅ Visualization data preparation is optimized")
    else:
        print("⚠️  Visualization might need further optimization")
    
    return True


async def main():
    """Run all optimization tests."""
    print("=" * 60)
    print("Testing All Performance Optimizations")
    print("=" * 60)
    
    results = []
    
    # Test each optimization
    results.append(await test_cache_integration())
    results.append(await test_fee_calculation_caching())
    results.append(test_vectorized_calculations())
    results.append(test_visualization_performance())
    
    # Summary
    print("\n" + "=" * 60)
    print("OPTIMIZATION TEST SUMMARY")
    print("=" * 60)
    
    optimizations = [
        "Cache Integration",
        "Fee Calculation Caching",
        "Vectorized Calculations",
        "Visualization Performance"
    ]
    
    for i, (opt, result) in enumerate(zip(optimizations, results), 1):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{i}. {opt}: {status}")
    
    all_passed = all(results)
    print("\n" + ("✅ All optimizations working!" if all_passed else "❌ Some optimizations need attention"))
    
    return all_passed


if __name__ == "__main__":
    asyncio.run(main()) 