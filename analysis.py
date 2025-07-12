"""
Analysis module for calculating impermanent loss, fees, and PnL.
"""

from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
import math

from uniswap_v3 import UniswapV3Calculator, Position
from data_fetcher import PoolState, SwapEvent


class PositionAnalyzer:
    """Analyzes Uniswap V3 positions for IL, fees, and PnL."""
    
    def __init__(self, calculator: UniswapV3Calculator):
        self.calculator = calculator
        
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
    
    def estimate_fees_from_swaps(
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
        fee_by_tick = {}
        
        # Initialize fee accumulation for our tick range
        for tick in range(position.tick_lower, position.tick_upper + 1):
            fee_by_tick[tick] = (0.0, 0.0)
        
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
                
                for tick in range(tick_start, tick_end + 1):
                    if tick in fee_by_tick:
                        # Calculate our share of liquidity at this tick
                        total_liquidity = liquidity_distribution.get(tick, 1)
                        if total_liquidity > 0:
                            our_share = position.liquidity / total_liquidity
                            
                            # Proportional fee share
                            tick_fee0 = (fee0 / ticks_crossed) * our_share
                            tick_fee1 = (fee1 / ticks_crossed) * our_share
                            
                            old_fees = fee_by_tick[tick]
                            fee_by_tick[tick] = (
                                old_fees[0] + tick_fee0,
                                old_fees[1] + tick_fee1
                            )
        
        return fee_by_tick
    
    def analyze_position(
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
        fee_by_tick = self.estimate_fees_from_swaps(
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