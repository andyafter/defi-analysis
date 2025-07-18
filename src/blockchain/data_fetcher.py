"""
Data fetcher module for interacting with Ethereum blockchain and Uniswap V3 pools.
Optimized for high-performance RPC calls with connection pooling and batching.
"""

import json
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
from web3 import Web3
from web3.contract import Contract
from web3.providers.rpc import HTTPProvider
from concurrent.futures import ThreadPoolExecutor
import logging
from dataclasses import dataclass
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import requests
from src.data.cache import FileCache, CacheKeyBuilder
from src.core.interfaces import ICacheProvider

# Uniswap V3 Pool ABI (minimal)
POOL_ABI = json.loads('''[
    {
        "inputs": [],
        "name": "slot0",
        "outputs": [
            {"name": "sqrtPriceX96", "type": "uint160"},
            {"name": "tick", "type": "int24"},
            {"name": "observationIndex", "type": "uint16"},
            {"name": "observationCardinality", "type": "uint16"},
            {"name": "observationCardinalityNext", "type": "uint16"},
            {"name": "feeProtocol", "type": "uint8"},
            {"name": "unlocked", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "liquidity",
        "outputs": [{"name": "", "type": "uint128"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "fee",
        "outputs": [{"name": "", "type": "uint24"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "tickSpacing",
        "outputs": [{"name": "", "type": "int24"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token0",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token1",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "", "type": "int24"}],
        "name": "ticks",
        "outputs": [
            {"name": "liquidityGross", "type": "uint128"},
            {"name": "liquidityNet", "type": "int128"},
            {"name": "feeGrowthOutside0X128", "type": "uint256"},
            {"name": "feeGrowthOutside1X128", "type": "uint256"},
            {"name": "tickCumulativeOutside", "type": "int56"},
            {"name": "secondsPerLiquidityOutsideX128", "type": "uint160"},
            {"name": "secondsOutside", "type": "uint32"},
            {"name": "initialized", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": false,
        "inputs": [
            {"indexed": true, "name": "sender", "type": "address"},
            {"indexed": true, "name": "recipient", "type": "address"},
            {"indexed": false, "name": "amount0", "type": "int256"},
            {"indexed": false, "name": "amount1", "type": "int256"},
            {"indexed": false, "name": "sqrtPriceX96", "type": "uint160"},
            {"indexed": false, "name": "liquidity", "type": "uint128"},
            {"indexed": false, "name": "tick", "type": "int24"}
        ],
        "name": "Swap",
        "type": "event"
    }
]''')

# ERC20 ABI (minimal)
ERC20_ABI = json.loads('''[
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]''')


class PoolState:
    """Represents the state of a Uniswap V3 pool at a specific block."""
    
    def __init__(self, 
                 sqrt_price_x96: int,
                 tick: int,
                 liquidity: int,
                 fee: int,
                 tick_spacing: int,
                 token0: str,
                 token1: str,
                 block_number: int):
        self.sqrt_price_x96 = sqrt_price_x96
        self.tick = tick
        self.liquidity = liquidity
        self.fee = fee
        self.tick_spacing = tick_spacing
        self.token0 = token0.lower()
        self.token1 = token1.lower()
        self.block_number = block_number


class SwapEvent:
    """Represents a swap event in a Uniswap V3 pool."""
    
    def __init__(self,
                 sender: str,
                 recipient: str,
                 amount0: int,
                 amount1: int,
                 sqrt_price_x96: int,
                 liquidity: int,
                 tick: int,
                 block_number: int,
                 transaction_hash: str):
        self.sender = sender
        self.recipient = recipient
        self.amount0 = amount0
        self.amount1 = amount1
        self.sqrt_price_x96 = sqrt_price_x96
        self.liquidity = liquidity
        self.tick = tick
        self.block_number = block_number
        self.transaction_hash = transaction_hash


class OptimizedHTTPProvider(HTTPProvider):
    """Optimized HTTP provider with connection pooling and retry logic."""
    
    def __init__(self, endpoint_uri: str, pool_connections: int = 20, pool_maxsize: int = 20, 
                 max_retries: int = 3, backoff_factor: float = 0.1):
        # Create session with connection pooling
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"]
        )
        
        # Configure adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        super().__init__(endpoint_uri, session=session)

class DataFetcher:
    """Optimized data fetcher with connection pooling and batch requests."""
    
    def __init__(self, rpc_url: str, max_workers: int = 20, max_concurrent_requests: int = 10, cache: Optional[ICacheProvider] = None):
        """Initialize optimized data fetcher.
        
        Args:
            rpc_url: Ethereum RPC endpoint URL
            max_workers: Maximum number of thread pool workers
            max_concurrent_requests: Maximum concurrent RPC requests
            cache: Optional cache provider for storing results
        """
        # Initialize Web3 with optimized provider
        self.w3 = Web3(OptimizedHTTPProvider(rpc_url))
        
        # Cache provider
        self.cache = cache
        
        # Retry connection with backoff
        max_retries = 3
        for attempt in range(max_retries):
            if self.w3.is_connected():
                break
            if attempt < max_retries - 1:
                import time
                time.sleep(1)  # Wait 1 second before retry
        
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to Ethereum node at {rpc_url[:50]}... after {max_retries} attempts")
        
        # Optimized executor with more workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Rate limiting semaphore
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        # Logger
        self.logger = logging.getLogger(__name__)
    
    async def _rate_limited_call(self, func, *args, **kwargs):
        """Execute function with rate limiting."""
        async with self.semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self.executor, func, *args, **kwargs)
    
    async def get_pool_state(self, pool_address: str, block_number: int) -> PoolState:
        """Get pool state with optimized batch calls."""
        # Check cache first
        if self.cache:
            cache_key = CacheKeyBuilder.pool_state_key(pool_address, block_number)
            cached_state = await self.cache.get(cache_key)
            if cached_state:
                self.logger.debug(f"Cache hit for pool state at block {block_number}")
                return cached_state
        
        pool_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=POOL_ABI
        )
        
        # Batch all contract calls together
        call_params = {'block_identifier': block_number}
        
        # Create batch of calls
        calls = [
            ('slot0', pool_contract.functions.slot0().call),
            ('liquidity', pool_contract.functions.liquidity().call),
            ('fee', pool_contract.functions.fee().call),
            ('tickSpacing', pool_contract.functions.tickSpacing().call),
            ('token0', pool_contract.functions.token0().call),
            ('token1', pool_contract.functions.token1().call),
        ]
        
        # Execute all calls concurrently with rate limiting
        tasks = []
        for name, call_func in calls:
            task = self._rate_limited_call(lambda f=call_func: f(**call_params))
            tasks.append(task)
        
        try:
            results = await asyncio.gather(*tasks)
            
            slot0, liquidity, fee, tick_spacing, token0, token1 = results
            
            self.logger.debug(f"Fetched pool state for {pool_address} at block {block_number}")
            
            pool_state = PoolState(
                sqrt_price_x96=slot0[0],
                tick=slot0[1],
                liquidity=liquidity,
                fee=fee,
                tick_spacing=tick_spacing,
                token0=token0,
                token1=token1,
                block_number=block_number
            )
            
            # Cache the result
            if self.cache:
                await self.cache.set(cache_key, pool_state, ttl=86400)  # Cache for 24 hours
                self.logger.debug(f"Cached pool state for block {block_number}")
            
            return pool_state
            
        except Exception as e:
            self.logger.error(f"Error fetching pool state: {e}")
            raise
    
    async def get_liquidity_distribution(self, 
                                       pool_address: str, 
                                       block_number: int,
                                       tick_lower: int,
                                       tick_upper: int) -> Dict[int, int]:
        """
        Get liquidity distribution across a tick range.
        
        This method correctly handles Uniswap V3's tick-based liquidity by:
        1. Starting from the pool's actual liquidity at the current tick
        2. Walking backwards/forwards and applying liquidity changes
        3. Ensuring liquidity never goes negative
        
        Args:
            pool_address: The Uniswap V3 pool address
            block_number: Block number to query at
            tick_lower: Lower bound of tick range (inclusive)
            tick_upper: Upper bound of tick range (inclusive)
            
        Returns:
            Dict mapping tick -> liquidity amount at that tick
            
        Example:
            >>> # Get liquidity distribution for USDC/WETH pool
            >>> distribution = await fetcher.get_liquidity_distribution(
            ...     pool_address="0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
            ...     block_number=17618642,
            ...     tick_lower=200540,
            ...     tick_upper=200560
            ... )
            >>> # Result: {200540: 1500000, 200541: 1500000, ..., 200560: 2000000}
            
        Technical Details:
            In Uniswap V3, liquidity is concentrated in tick ranges. Each tick
            stores a 'liquidity_net' value which represents the change in 
            liquidity when the price crosses that tick:
            
            - Positive liquidity_net: Liquidity is added (positions enter range)
            - Negative liquidity_net: Liquidity is removed (positions exit range)
            
            To calculate total liquidity at any tick, we start from a known 
            reference point (current tick with current liquidity) and walk
            through ticks, applying these changes.
        """
        # Step 1: Set up pool contract
        pool_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=POOL_ABI
        )
        
        # Step 2: Get pool configuration (tick spacing)
        tick_spacing = await self._rate_limited_call(
            lambda: pool_contract.functions.tickSpacing().call(block_identifier=block_number)
        )
        
        # Step 3: Get current pool state (current tick and liquidity)
        slot0_task = self._rate_limited_call(
            lambda: pool_contract.functions.slot0().call(block_identifier=block_number)
        )
        liquidity_task = self._rate_limited_call(
            lambda: pool_contract.functions.liquidity().call(block_identifier=block_number)
        )
        
        slot0, current_pool_liquidity = await asyncio.gather(slot0_task, liquidity_task)
        current_tick = slot0[1]  # Extract current tick from slot0
        
        # Step 4: Determine which ticks to fetch (must be aligned with tick spacing)
        tick_lower_aligned = self._align_tick_lower(tick_lower, tick_spacing)
        tick_upper_aligned = self._align_tick_upper(tick_upper, tick_spacing)
        ticks_to_fetch = list(range(tick_lower_aligned, tick_upper_aligned + 1, tick_spacing))
        
        # Step 5: Fetch tick data in parallel for efficiency
        tick_data = await self._fetch_tick_data(
            pool_contract, ticks_to_fetch, block_number
        )
        
        # Step 6: Calculate liquidity distribution
        filled_liquidity = self._calculate_liquidity_distribution(
            tick_lower, tick_upper, tick_spacing,
            current_tick, current_pool_liquidity, tick_data
        )
        
        self.logger.debug(
            f"Fetched liquidity distribution for {len(ticks_to_fetch)} ticks, "
            f"range [{tick_lower}, {tick_upper}]"
        )
        return filled_liquidity
    
    def _align_tick_lower(self, tick: int, tick_spacing: int) -> int:
        """Align tick to be a multiple of tick_spacing (round down)."""
        return tick - (tick % tick_spacing)
    
    def _align_tick_upper(self, tick: int, tick_spacing: int) -> int:
        """Align tick to be a multiple of tick_spacing (round up)."""
        return tick + (tick_spacing - (tick % tick_spacing)) % tick_spacing
    
    async def _fetch_tick_data(self, 
                              pool_contract: Contract,
                              ticks_to_fetch: List[int],
                              block_number: int) -> Dict[int, Dict[str, int]]:
        """
        Fetch tick data for multiple ticks in parallel.
        
        Returns:
            Dict mapping tick -> {'liquidity_gross': int, 'liquidity_net': int}
        """
        # Create tasks for parallel execution
        tasks = []
        for tick in ticks_to_fetch:
            task = self._rate_limited_call(
                lambda t=tick: pool_contract.functions.ticks(t).call(
                    block_identifier=block_number
                )
            )
            tasks.append(task)
        
        # Execute all tick queries in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results into tick data dictionary
        tick_data = {}
        for tick, result in zip(ticks_to_fetch, results):
            if isinstance(result, Exception):
                self.logger.warning(f"Error fetching tick {tick}: {result}")
                continue
            
            # Unpack tick data tuple
            liquidity_gross = result[0]
            liquidity_net = result[1]
            initialized = result[7]
            
            # Only store data for initialized ticks
            if initialized:
                tick_data[tick] = {
                    'liquidity_gross': liquidity_gross,
                    'liquidity_net': liquidity_net
                }
        
        return tick_data
    
    def _calculate_liquidity_distribution(self,
                                        tick_lower: int,
                                        tick_upper: int,
                                        tick_spacing: int,
                                        current_tick: int,
                                        current_pool_liquidity: int,
                                        tick_data: Dict[int, Dict[str, int]]) -> Dict[int, int]:
        """
        Calculate liquidity at each tick by walking from the current tick.
        
        Key insight: liquidity_net represents the CHANGE in liquidity when
        crossing a tick. We need to apply these changes correctly based on
        the direction we're walking.
        
        Visual Example:
        
            tick:    199990    200000    200010    200020    200030
            liq_net:   +500k    -300k    current    +200k    -100k
                         |         |         |         |         |
        walking  <--------<--------    [5M]   -------->-------->  walking
        backwards: reverse changes            apply changes      forwards
        
        If current liquidity at tick 200010 is 5M:
        - At 200000: 5M - (-300k) = 5.3M (reverse the exit)
        - At 199990: 5.3M - (+500k) = 4.8M (reverse the entry)
        - At 200020: 5M + (+200k) = 5.2M (apply the entry)
        - At 200030: 5.2M + (-100k) = 5.1M (apply the exit)
        
        Returns:
            Dict mapping tick -> liquidity at that tick
        """
        filled_liquidity = {}
        
        # Find the nearest initialized tick to use as reference
        reference_tick = current_tick - (current_tick % tick_spacing)
        
        # Calculate liquidity for each tick in the range
        for tick in range(tick_lower, tick_upper + 1):
            if tick < reference_tick:
                # Walking backwards from reference tick
                liquidity = self._calculate_liquidity_backwards(
                    current_pool_liquidity, reference_tick, tick, 
                    tick_spacing, tick_data
                )
            elif tick == reference_tick:
                # At reference tick, use current pool liquidity
                liquidity = current_pool_liquidity
            else:
                # Walking forwards from reference tick
                liquidity = self._calculate_liquidity_forwards(
                    current_pool_liquidity, reference_tick, tick,
                    tick_spacing, tick_data
                )
            
            # Ensure liquidity never goes negative (safety check)
            filled_liquidity[tick] = max(0, liquidity)
        
        return filled_liquidity
    
    def _calculate_liquidity_backwards(self,
                                     start_liquidity: int,
                                     start_tick: int,
                                     target_tick: int,
                                     tick_spacing: int,
                                     tick_data: Dict[int, Dict[str, int]]) -> int:
        """
        Calculate liquidity when walking backwards from start_tick to target_tick.
        
        When moving backwards, we need to REVERSE the liquidity changes:
        - If liquidity_net is positive at a tick, it means liquidity enters when
          price crosses UP through that tick, so when going backwards (down),
          we need to subtract it.
        """
        liquidity = start_liquidity
        
        # Walk backwards through ticks
        for tick in range(start_tick, target_tick, -tick_spacing):
            if tick in tick_data:
                # Reverse the liquidity change
                liquidity -= tick_data[tick]['liquidity_net']
        
        return liquidity
    
    def _calculate_liquidity_forwards(self,
                                    start_liquidity: int,
                                    start_tick: int,
                                    target_tick: int,
                                    tick_spacing: int,
                                    tick_data: Dict[int, Dict[str, int]]) -> int:
        """
        Calculate liquidity when walking forwards from start_tick to target_tick.
        
        When moving forwards, we apply liquidity changes as-is:
        - Positive liquidity_net means liquidity enters
        - Negative liquidity_net means liquidity exits
        """
        liquidity = start_liquidity
        
        # Walk forwards through ticks
        for tick in range(start_tick + tick_spacing, target_tick + 1, tick_spacing):
            if tick in tick_data:
                # Apply the liquidity change
                liquidity += tick_data[tick]['liquidity_net']
        
        return liquidity
    
    async def get_swap_events(self, 
                            pool_address: str, 
                            start_block: int, 
                            end_block: int,
                            chunk_size: int = 2000) -> List[SwapEvent]:
        """Get swap events with optimized chunking and parallel processing."""
        # Check cache first
        if self.cache:
            cache_key = CacheKeyBuilder.swap_events_key(pool_address, start_block, end_block)
            cached_events = await self.cache.get(cache_key)
            if cached_events:
                self.logger.debug(f"Cache hit for swap events blocks {start_block}-{end_block}")
                return cached_events
        
        pool_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=POOL_ABI
        )
        
        # Calculate optimal chunk size based on block range
        total_blocks = end_block - start_block
        if total_blocks < 100:
            chunk_size = total_blocks
        elif total_blocks > 10000:
            chunk_size = min(chunk_size, total_blocks // 10)
        
        # Create chunks for parallel processing
        chunks = []
        for block_start in range(start_block, end_block + 1, chunk_size):
            block_end = min(block_start + chunk_size - 1, end_block)
            chunks.append((block_start, block_end))
        
        # Process chunks in parallel with rate limiting
        tasks = []
        for chunk_start, chunk_end in chunks:
            task = self._fetch_events_chunk(pool_contract, chunk_start, chunk_end)
            tasks.append(task)
        
        # Execute all chunks concurrently
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        all_events = []
        for result in chunk_results:
            if isinstance(result, Exception):
                self.logger.warning(f"Error fetching events chunk: {result}")
                continue
            all_events.extend(result)
        
        self.logger.info(f"Fetched {len(all_events)} swap events from {len(chunks)} chunks")
        
        # Cache the result
        if self.cache and all_events:
            await self.cache.set(cache_key, all_events, ttl=86400)  # Cache for 24 hours
            self.logger.debug(f"Cached {len(all_events)} swap events")
        
        return all_events
    
    async def _fetch_events_chunk(self, pool_contract: Contract, start_block: int, end_block: int) -> List[SwapEvent]:
        """Fetch events for a single chunk with rate limiting."""
        loop = asyncio.get_event_loop()
        events = await loop.run_in_executor(
            self.executor,
            lambda: pool_contract.events.Swap().get_logs(
                fromBlock=start_block, 
                toBlock=end_block
            )
        )
        
        swap_events = []
        for event in events:
            swap = SwapEvent(
                sender=event['args']['sender'],
                recipient=event['args']['recipient'],
                amount0=event['args']['amount0'],
                amount1=event['args']['amount1'],
                sqrt_price_x96=event['args']['sqrtPriceX96'],
                liquidity=event['args']['liquidity'],
                tick=event['args']['tick'],
                block_number=event['blockNumber'],
                transaction_hash=event['transactionHash'].hex()
            )
            swap_events.append(swap)
        
        return swap_events
    
    async def get_eth_price_in_usdc(self, block_number: int) -> float:
        """
        Get ETH price in USDC at a specific block.
        Uses the same pool to get the price.
        """
        # For USDC/WETH pool, token0 is USDC and token1 is WETH
        pool_state = await self.get_pool_state(
            "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
            block_number
        )
        
        # Calculate price from sqrtPriceX96
        # sqrtPriceX96 = sqrt(reserve1/reserve0) * 2^96
        # where reserve1 is in wei and reserve0 is in USDC smallest units
        
        sqrt_price = pool_state.sqrt_price_x96 / (2 ** 96)
        price_raw = sqrt_price ** 2
        
        # price_raw = reserve1/reserve0 = wei per USDC smallest unit
        # To get USDC per ETH:
        # 1. Invert to get USDC smallest units per wei
        # 2. Scale by decimals: multiply by 10^18 (wei per ETH) and divide by 10^6 (USDC units per USDC)
        
        if price_raw > 0:
            # USDC smallest units per wei = 1 / price_raw
            # USDC per ETH = (1 / price_raw) * 10^18 / 10^6 = 10^12 / price_raw
            usdc_per_eth = (10 ** 12) / price_raw
        else:
            usdc_per_eth = 0
        
        return float(usdc_per_eth)
    
    async def get_block_timestamp(self, block_number: int) -> int:
        """Get timestamp of a block."""
        # Check cache first
        if self.cache:
            cache_key = CacheKeyBuilder.block_timestamp_key(block_number)
            cached_timestamp = await self.cache.get(cache_key)
            if cached_timestamp:
                self.logger.debug(f"Cache hit for block timestamp {block_number}")
                return cached_timestamp
        
        loop = asyncio.get_event_loop()
        block = await loop.run_in_executor(
            self.executor,
            lambda: self.w3.eth.get_block(block_number)
        )
        timestamp = block['timestamp']
        
        # Cache the result
        if self.cache:
            await self.cache.set(cache_key, timestamp, ttl=86400 * 7)  # Cache for 7 days
            self.logger.debug(f"Cached timestamp for block {block_number}")
        
        return timestamp 