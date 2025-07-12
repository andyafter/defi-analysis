"""
Data fetcher module for interacting with Ethereum blockchain and Uniswap V3 pools.
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
from web3 import Web3
from web3.contract import Contract
import asyncio
from concurrent.futures import ThreadPoolExecutor

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


class DataFetcher:
    """Fetches data from Ethereum blockchain and Uniswap V3 pools."""
    
    def __init__(self, rpc_url: str):
        """Initialize the data fetcher with an RPC URL."""
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        
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
        
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    async def get_pool_state(self, pool_address: str, block_number: int) -> PoolState:
        """Get the state of a Uniswap V3 pool at a specific block."""
        pool_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=POOL_ABI
        )
        
        # Fetch pool state in parallel
        loop = asyncio.get_event_loop()
        
        # Create proper call parameters for newer web3 version
        call_params = {'block_identifier': block_number}
        
        tasks = [
            loop.run_in_executor(self.executor, lambda: pool_contract.functions.slot0().call(**call_params)),
            loop.run_in_executor(self.executor, lambda: pool_contract.functions.liquidity().call(**call_params)),
            loop.run_in_executor(self.executor, lambda: pool_contract.functions.fee().call(**call_params)),
            loop.run_in_executor(self.executor, lambda: pool_contract.functions.tickSpacing().call(**call_params)),
            loop.run_in_executor(self.executor, lambda: pool_contract.functions.token0().call(**call_params)),
            loop.run_in_executor(self.executor, lambda: pool_contract.functions.token1().call(**call_params)),
        ]
        
        results = await asyncio.gather(*tasks)
        
        slot0 = results[0]
        liquidity = results[1]
        fee = results[2]
        tick_spacing = results[3]
        token0 = results[4]
        token1 = results[5]
        
        return PoolState(
            sqrt_price_x96=slot0[0],
            tick=slot0[1],
            liquidity=liquidity,
            fee=fee,
            tick_spacing=tick_spacing,
            token0=token0,
            token1=token1,
            block_number=block_number
        )
    
    async def get_liquidity_distribution(self, 
                                       pool_address: str, 
                                       block_number: int,
                                       tick_lower: int,
                                       tick_upper: int) -> Dict[int, int]:
        """Get liquidity distribution for a range of ticks."""
        pool_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=POOL_ABI
        )
        
        liquidity_by_tick = {}
        
        # Fetch tick data in parallel
        loop = asyncio.get_event_loop()
        tasks = []
        ticks_to_fetch = []
        
        # Get tick spacing
        tick_spacing = await loop.run_in_executor(
            self.executor, 
            lambda: pool_contract.functions.tickSpacing().call(block_identifier=block_number)
        )
        
        # Only fetch initialized ticks (every tick_spacing)
        for tick in range(tick_lower, tick_upper + 1, tick_spacing):
            tasks.append(
                loop.run_in_executor(
                    self.executor,
                    lambda t=tick: pool_contract.functions.ticks(t).call(block_identifier=block_number)
                )
            )
            ticks_to_fetch.append(tick)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        current_liquidity = 0
        for tick, result in zip(ticks_to_fetch, results):
            if isinstance(result, Exception):
                continue
            
            liquidity_gross = result[0]
            liquidity_net = result[1]
            initialized = result[7]
            
            if initialized:
                current_liquidity += liquidity_net
                liquidity_by_tick[tick] = current_liquidity
        
        # Fill in liquidity for all ticks
        filled_liquidity = {}
        current_liquidity = 0
        
        for tick in range(tick_lower, tick_upper + 1):
            if tick in liquidity_by_tick:
                current_liquidity = liquidity_by_tick[tick]
            filled_liquidity[tick] = current_liquidity
        
        return filled_liquidity
    
    async def get_swap_events(self, 
                            pool_address: str, 
                            start_block: int, 
                            end_block: int) -> List[SwapEvent]:
        """Get swap events for a pool between two blocks."""
        pool_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(pool_address),
            abi=POOL_ABI
        )
        
        # Fetch events in chunks to avoid timeouts
        chunk_size = 1000
        all_events = []
        
        for block_start in range(start_block, end_block + 1, chunk_size):
            block_end = min(block_start + chunk_size - 1, end_block)
            
            loop = asyncio.get_event_loop()
            events = await loop.run_in_executor(
                self.executor,
                lambda: pool_contract.events.Swap().get_logs(
                    from_block=block_start, 
                    to_block=block_end
                )
            )
            
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
                all_events.append(swap)
        
        return all_events
    
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
        loop = asyncio.get_event_loop()
        block = await loop.run_in_executor(
            self.executor,
            lambda: self.w3.eth.get_block(block_number)
        )
        return block['timestamp'] 