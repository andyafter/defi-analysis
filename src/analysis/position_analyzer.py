"""
Analysis module for calculating impermanent loss, fees, and PnL.
"""

from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import math
import hashlib
import json
import numpy as np

from src.uniswap import UniswapV3Calculator, Position
from src.blockchain import PoolState, SwapEvent
from src.core.interfaces import ICacheProvider


class PositionAnalyzer:
    """Analyzes Uniswap V3 positions for IL, fees, and PnL."""
    
    def __init__(self, calculator: UniswapV3Calculator, cache: Optional[ICacheProvider] = None):
        self.calculator = calculator
        self.cache = cache
        
    def calculate_impermanent_loss(
        self,
        initial_usdc: float,
        initial_weth: float,
        final_usdc: float,
        final_weth: float,
        initial_eth_price: float,
        final_eth_price: float
    ) -> Tuple[float, float]:
        """
        Calculate impermanent loss.
        Returns (IL in USDC, IL percentage).
        """
        # Initial portfolio value in USDC
        initial_value = initial_usdc + (initial_weth * initial_eth_price)
        
        # Final value if just held (no LP)
        hodl_value = initial_usdc + (initial_weth * final_eth_price)
        
        # Actual final value
        final_value = final_usdc + (final_weth * final_eth_price)
        
        # IL is the difference between holding and LP
        il_amount = hodl_value - final_value
        il_percentage = (il_amount / initial_value) * 100 if initial_value > 0 else 0
        
        return il_amount, il_percentage
    
    def _get_fee_cache_key(self, position: Position, swap_events: List[SwapEvent], pool_fee: int) -> str:
        """Generate a cache key for fee calculations."""
        # Create a hash of the position and swap events
        position_hash = f"{position.liquidity}_{position.tick_lower}_{position.tick_upper}"
        
        # Hash swap events (use first/last block and count for efficiency)
        if swap_events:
            swap_hash = f"{swap_events[0].block_number}_{swap_events[-1].block_number}_{len(swap_events)}"
        else:
            swap_hash = "no_swaps"
        
        return f"fees:{position_hash}:{swap_hash}:{pool_fee}"

    async def estimate_fees_from_swaps(
        self,
        position: Position,
        swap_events: List[SwapEvent],
        liquidity_distribution: Dict[int, int],
        pool_fee: int
    ) -> Dict[int, Tuple[float, float]]:
        """
        Estimate fees earned from swap events.
        Returns fees by tick as {tick: (usdc_fees, weth_fees)}.
        """
        # Check cache first
        if self.cache:
            cache_key = self._get_fee_cache_key(position, swap_events, pool_fee)
            cached_fees = await self.cache.get(cache_key)
            if cached_fees:
                return cached_fees
        
        fee_by_tick = {}
        
        # Initialize fee accumulation for our tick range - vectorized
        tick_range = np.arange(position.tick_lower, position.tick_upper + 1)
        fee_by_tick = {tick: (0.0, 0.0) for tick in tick_range}
        
        # Process each swap event
        for i, swap in enumerate(swap_events):
            # Determine tick range crossed by this swap
            if i == 0:
                prev_tick = swap.tick  # Assume starting at current tick
            else:
                prev_tick = swap_events[i-1].tick
                
            current_tick = swap.tick
            
            # Calculate fee for this swap
            # Fee rate is pool_fee / 1e6 (e.g., 500 / 1e6 = 0.05%)
            fee_rate = pool_fee / 1e6
            
            # Fees in terms of traded amounts
            fee0 = abs(swap.amount0) * fee_rate / 10**6  # USDC
            fee1 = abs(swap.amount1) * fee_rate / 10**18  # WETH
            
            # Distribute fees across ticks that were crossed
            tick_start = min(prev_tick, current_tick)
            tick_end = max(prev_tick, current_tick)
            
            # Only consider ticks within our position range
            tick_start = max(tick_start, position.tick_lower)
            tick_end = min(tick_end, position.tick_upper)
            
            if tick_start <= tick_end:
                ticks_crossed = tick_end - tick_start + 1
                
                # Vectorized fee distribution
                tick_array = np.arange(tick_start, tick_end + 1)
                valid_ticks = tick_array[np.isin(tick_array, list(fee_by_tick.keys()))]
                
                if len(valid_ticks) > 0:
                    # Calculate liquidity shares for all ticks at once
                    total_liquidities = np.array([liquidity_distribution.get(t, 1) for t in valid_ticks])
                    our_shares = np.where(total_liquidities > 0, position.liquidity / total_liquidities, 0)
                    
                    # Distribute fees
                    tick_fee0_array = (fee0 / ticks_crossed) * our_shares
                    tick_fee1_array = (fee1 / ticks_crossed) * our_shares
                    
                    # Update fee_by_tick
                    for i, tick in enumerate(valid_ticks):
                        old_fees = fee_by_tick[tick]
                        fee_by_tick[tick] = (
                            old_fees[0] + tick_fee0_array[i],
                            old_fees[1] + tick_fee1_array[i]
                        )
        
        # Cache the result
        if self.cache:
            await self.cache.set(cache_key, fee_by_tick, ttl=86400)  # Cache for 24 hours
        
        return fee_by_tick
    
    async def analyze_position(
        self,
        position: Position,
        pool_state_start: PoolState,
        pool_state_end: PoolState,
        liquidity_distribution: Dict[int, int],
        swap_events: List[SwapEvent],
        eth_price_start: float,
        eth_price_end: float
    ) -> Dict[str, Any]:
        """
        Perform complete position analysis.
        Returns dictionary with all analysis results.
        """
        # Get final position amounts
        final_usdc, final_weth = self.calculator.get_position_amounts(
            position, pool_state_end.sqrt_price_x96
        )
        
        # Calculate impermanent loss
        il_amount, il_pct = self.calculate_impermanent_loss(
            position.amount0,
            position.amount1,
            final_usdc,
            final_weth,
            eth_price_start,
            eth_price_end
        )
        
        # Estimate fees
        fee_by_tick = await self.estimate_fees_from_swaps(
            position,
            swap_events,
            liquidity_distribution,
            pool_state_start.fee
        )
        
        # Sum total fees
        total_fees_usdc = 0
        total_fees_weth = 0
        for fees in fee_by_tick.values():
            total_fees_usdc += fees[0]
            total_fees_weth += fees[1]
        
        # Calculate final values
        final_value_from_position = final_usdc + (final_weth * eth_price_end)
        total_fees_value = total_fees_usdc + (total_fees_weth * eth_price_end)
        
        # Include unused funds (if any)
        initial_total_usdc = 50000  # Half of 100k portfolio
        initial_total_weth = 50000 / eth_price_start
        unused_usdc = initial_total_usdc - position.amount0
        unused_weth = initial_total_weth - position.amount1
        unused_value = unused_usdc + (unused_weth * eth_price_end)
        
        # Total final value including fees and unused funds
        final_total_value = final_value_from_position + total_fees_value + unused_value
        
        # Calculate PnL
        initial_value = 100000  # Initial portfolio value
        pnl = final_total_value - initial_value
        pnl_pct = (pnl / initial_value) * 100
        
        return {
            'final_usdc': final_usdc,
            'final_weth': final_weth,
            'final_value_usdc': final_value_from_position,
            'impermanent_loss': il_amount,
            'impermanent_loss_pct': il_pct,
            'fees_usdc': total_fees_usdc,
            'fees_weth': total_fees_weth,
            'total_fees_usdc': total_fees_value,
            'fee_by_tick': fee_by_tick,
            'unused_usdc': unused_usdc,
            'unused_weth': unused_weth,
            'unused_value': unused_value,
            'final_total_value': final_total_value,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'eth_price_start': eth_price_start,
            'eth_price_end': eth_price_end,
            'position_liquidity': position.liquidity,
            'initial_usdc_in_position': position.amount0,
            'initial_weth_in_position': position.amount1
        } 