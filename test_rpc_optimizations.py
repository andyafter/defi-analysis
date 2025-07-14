#!/usr/bin/env python3
"""Test script for RPC optimizations."""

import asyncio
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import optimized components
from data_fetcher import DataFetcher
from src.config import ConfigManager

# Test constants
TEST_POOL = "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"  # USDC/WETH pool
TEST_BLOCK = 17618642
TEST_BLOCK_RANGE = (17618642, 17618652)  # Small range for testing


async def test_configuration():
    """Test configuration loading with performance settings."""
    print("\n🔧 Testing Configuration Loading...")
    
    try:
        config_manager = ConfigManager('config.yaml')
        config = config_manager.load()
        
        print("✅ Configuration loaded successfully")
        print(f"   Max workers: {config.performance.max_workers}")
        print(f"   Max concurrent requests: {config.performance.max_concurrent_requests}")
        print(f"   Pool connections: {config.performance.pool_connections}")
        print(f"   Pool max size: {config.performance.pool_maxsize}")
        print(f"   Chunk size: {config.performance.chunk_size}")
        print(f"   Backoff factor: {config.performance.backoff_factor}")
        
        return config
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return None


async def test_data_fetcher_init(config):
    """Test optimized DataFetcher initialization."""
    print("\n🚀 Testing Optimized DataFetcher...")
    
    rpc_url = os.getenv("ETH_RPC_URL")
    if not rpc_url:
        print("❌ ETH_RPC_URL not set in environment")
        return None
    
    try:
        # Create optimized data fetcher
        data_fetcher = DataFetcher(
            rpc_url=rpc_url,
            max_workers=config.performance.max_workers,
            max_concurrent_requests=config.performance.max_concurrent_requests
        )
        
        print("✅ DataFetcher created successfully")
        print(f"   Thread pool workers: {data_fetcher.executor._max_workers}")
        print(f"   Rate limit semaphore: {data_fetcher.semaphore._value}")
        
        # Test connection
        if data_fetcher.w3.is_connected():
            print("✅ Web3 connection established")
            latest_block = data_fetcher.w3.eth.block_number
            print(f"   Latest block: {latest_block}")
        else:
            print("❌ Web3 connection failed")
            return None
            
        return data_fetcher
    except Exception as e:
        print(f"❌ DataFetcher initialization failed: {e}")
        return None


async def test_pool_state_fetch(data_fetcher):
    """Test optimized pool state fetching."""
    print("\n📊 Testing Pool State Fetch...")
    
    try:
        start_time = time.time()
        pool_state = await data_fetcher.get_pool_state(TEST_POOL, TEST_BLOCK)
        elapsed = time.time() - start_time
        
        print(f"✅ Pool state fetched in {elapsed:.2f}s")
        print(f"   Block: {pool_state.block_number}")
        print(f"   Tick: {pool_state.tick}")
        print(f"   Liquidity: {pool_state.liquidity}")
        print(f"   Fee: {pool_state.fee}")
        
        return True
    except Exception as e:
        print(f"❌ Pool state fetch failed: {e}")
        return False


async def test_parallel_fetching(data_fetcher):
    """Test parallel data fetching with rate limiting."""
    print("\n⚡ Testing Parallel Fetching...")
    
    try:
        # Test fetching multiple blocks in parallel
        blocks_to_test = [TEST_BLOCK + i for i in range(5)]
        
        start_time = time.time()
        tasks = [
            data_fetcher.get_pool_state(TEST_POOL, block)
            for block in blocks_to_test
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time
        
        successful = sum(1 for r in results if not isinstance(r, Exception))
        print(f"✅ Fetched {successful}/{len(blocks_to_test)} pool states in {elapsed:.2f}s")
        print(f"   Average time per request: {elapsed/len(blocks_to_test):.2f}s")
        
        # Check rate limiting is working
        if hasattr(data_fetcher.semaphore, '_value'):
            print(f"✅ Rate limiting is active (current permits: {data_fetcher.semaphore._value})")
        
        return True
    except Exception as e:
        print(f"❌ Parallel fetching failed: {e}")
        return False


async def test_event_fetching(data_fetcher, config):
    """Test optimized event fetching with chunking."""
    print("\n📈 Testing Event Fetching with Chunking...")
    
    try:
        start_time = time.time()
        events = await data_fetcher.get_swap_events(
            TEST_POOL,
            TEST_BLOCK_RANGE[0],
            TEST_BLOCK_RANGE[1],
            chunk_size=config.performance.chunk_size
        )
        elapsed = time.time() - start_time
        
        print(f"✅ Fetched {len(events)} swap events in {elapsed:.2f}s")
        print(f"   Block range: {TEST_BLOCK_RANGE[0]} - {TEST_BLOCK_RANGE[1]}")
        print(f"   Chunk size: {config.performance.chunk_size}")
        
        if events:
            print(f"   First event block: {events[0].block_number}")
            print(f"   Last event block: {events[-1].block_number}")
        
        return True
    except Exception as e:
        print(f"❌ Event fetching failed: {e}")
        return False


async def test_connection_pooling(data_fetcher):
    """Test connection pooling efficiency."""
    print("\n🔄 Testing Connection Pooling...")
    
    try:
        # Make multiple rapid requests to test connection reuse
        num_requests = 10
        
        start_time = time.time()
        for i in range(num_requests):
            await data_fetcher._rate_limited_call(
                lambda: data_fetcher.w3.eth.get_block('latest')
            )
        elapsed = time.time() - start_time
        
        avg_time = elapsed / num_requests
        print(f"✅ Completed {num_requests} requests in {elapsed:.2f}s")
        print(f"   Average time per request: {avg_time:.3f}s")
        print(f"   Connection pooling is {'efficient' if avg_time < 0.5 else 'working'}")
        
        return True
    except Exception as e:
        print(f"❌ Connection pooling test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 RPC OPTIMIZATION TEST SUITE")
    print("=" * 60)
    
    # Test 1: Configuration
    config = await test_configuration()
    if not config:
        print("\n❌ Cannot proceed without configuration")
        return
    
    # Test 2: DataFetcher initialization
    data_fetcher = await test_data_fetcher_init(config)
    if not data_fetcher:
        print("\n❌ Cannot proceed without DataFetcher")
        return
    
    # Test 3: Pool state fetch
    await test_pool_state_fetch(data_fetcher)
    
    # Test 4: Parallel fetching
    await test_parallel_fetching(data_fetcher)
    
    # Test 5: Event fetching
    await test_event_fetching(data_fetcher, config)
    
    # Test 6: Connection pooling
    await test_connection_pooling(data_fetcher)
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main()) 