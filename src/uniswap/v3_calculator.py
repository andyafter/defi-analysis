"""
Uniswap V3 liquidity mathematics and position calculations.
"""

import math
from typing import Tuple, Optional
from dataclasses import dataclass
from decimal import Decimal

# Constants
Q96 = 2 ** 96
Q128 = 2 ** 128


@dataclass
class Position:
    """Represents a Uniswap V3 liquidity position."""
    liquidity: int
    tick_lower: int
    tick_upper: int
    amount0: float  # USDC amount
    amount1: float  # WETH amount
    
    
class UniswapV3Calculator:
    """Handles Uniswap V3 mathematical calculations."""
    
    @staticmethod
    def tick_to_sqrt_price_x96(tick: int) -> int:
        """Convert tick to sqrt price in Q96 format."""
        return int(math.sqrt(1.0001 ** tick) * Q96)
    
    @staticmethod
    def sqrt_price_x96_to_tick(sqrt_price_x96: int) -> int:
        """Convert sqrt price in Q96 format to tick."""
        price = (sqrt_price_x96 / Q96) ** 2
        return int(math.floor(math.log(price) / math.log(1.0001)))
    
    @staticmethod
    def get_sqrt_ratio_at_tick(tick: int) -> int:
        """Get sqrt price ratio at a specific tick."""
        abs_tick = abs(tick)
        
        # Precomputed values for efficiency
        if abs_tick & 0x1 != 0:
            ratio = 0xfffcb933bd6fad37aa2d162d1a594001
        else:
            ratio = 0x100000000000000000000000000000000
            
        if abs_tick & 0x2 != 0:
            ratio = (ratio * 0xfff97272373d413259a46990580e213a) >> 128
        if abs_tick & 0x4 != 0:
            ratio = (ratio * 0xfff2e50f5f656932ef12357cf3c7fdcc) >> 128
        if abs_tick & 0x8 != 0:
            ratio = (ratio * 0xffe5caca7e10e4e61c3624eaa0941cd0) >> 128
        if abs_tick & 0x10 != 0:
            ratio = (ratio * 0xffcb9843d60f6159c9db58835c926644) >> 128
        if abs_tick & 0x20 != 0:
            ratio = (ratio * 0xff973b41fa98c081472e6896dfb254c0) >> 128
        if abs_tick & 0x40 != 0:
            ratio = (ratio * 0xff2ea16466c96a3843ec78b326b52861) >> 128
        if abs_tick & 0x80 != 0:
            ratio = (ratio * 0xfe5dee046a99a2a811c461f1969c3053) >> 128
        if abs_tick & 0x100 != 0:
            ratio = (ratio * 0xfcbe86c7900a88aedcffc83b479aa3a4) >> 128
        if abs_tick & 0x200 != 0:
            ratio = (ratio * 0xf987a7253ac413176f2b074cf7815e54) >> 128
        if abs_tick & 0x400 != 0:
            ratio = (ratio * 0xf3392b0822b70005940c7a398e4b70f3) >> 128
        if abs_tick & 0x800 != 0:
            ratio = (ratio * 0xe7159475a2c29b7443b29c7fa6e889d9) >> 128
        if abs_tick & 0x1000 != 0:
            ratio = (ratio * 0xd097f3bdfd2022b8845ad8f792aa5825) >> 128
        if abs_tick & 0x2000 != 0:
            ratio = (ratio * 0xa9f746462d870fdf8a65dc1f90e061e5) >> 128
        if abs_tick & 0x4000 != 0:
            ratio = (ratio * 0x70d869a156d2a1b890bb3df62baf32f7) >> 128
        if abs_tick & 0x8000 != 0:
            ratio = (ratio * 0x31be135f97d08fd981231505542fcfa6) >> 128
        if abs_tick & 0x10000 != 0:
            ratio = (ratio * 0x9aa508b5b7a84e1c677de54f3e99bc9) >> 128
        if abs_tick & 0x20000 != 0:
            ratio = (ratio * 0x5d6af8dedb81196699c329225ee604) >> 128
        if abs_tick & 0x40000 != 0:
            ratio = (ratio * 0x2216e584f5fa1ea926041bedfe98) >> 128
        if abs_tick & 0x80000 != 0:
            ratio = (ratio * 0x48a170391f7dc42444e8fa2) >> 128
            
        if tick > 0:
            ratio = (2**256 - 1) // ratio
            
        # Round down to nearest uint160
        return ratio >> 32
    
    @staticmethod
    def get_amount0_for_liquidity(
        sqrt_ratio_a_x96: int,
        sqrt_ratio_b_x96: int,
        liquidity: int
    ) -> int:
        """Calculate amount0 for a given liquidity."""
        if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
            sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96
            
        numerator = liquidity * Q96 * (sqrt_ratio_b_x96 - sqrt_ratio_a_x96)
        denominator = sqrt_ratio_b_x96 * sqrt_ratio_a_x96
        
        return numerator // denominator
    
    @staticmethod
    def get_amount1_for_liquidity(
        sqrt_ratio_a_x96: int,
        sqrt_ratio_b_x96: int,
        liquidity: int
    ) -> int:
        """Calculate amount1 for a given liquidity."""
        if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
            sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96
            
        return liquidity * (sqrt_ratio_b_x96 - sqrt_ratio_a_x96) // Q96
    
    @staticmethod
    def get_liquidity_for_amounts(
        sqrt_ratio_x96: int,
        sqrt_ratio_a_x96: int,
        sqrt_ratio_b_x96: int,
        amount0: int,
        amount1: int
    ) -> int:
        """Calculate liquidity for given token amounts."""
        if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
            sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96
            
        if sqrt_ratio_x96 <= sqrt_ratio_a_x96:
            # Current price below range, only amount0 is active
            liquidity = UniswapV3Calculator.get_liquidity_for_amount0(
                sqrt_ratio_a_x96, sqrt_ratio_b_x96, amount0
            )
        elif sqrt_ratio_x96 < sqrt_ratio_b_x96:
            # Current price within range, both tokens active
            liquidity0 = UniswapV3Calculator.get_liquidity_for_amount0(
                sqrt_ratio_x96, sqrt_ratio_b_x96, amount0
            )
            liquidity1 = UniswapV3Calculator.get_liquidity_for_amount1(
                sqrt_ratio_a_x96, sqrt_ratio_x96, amount1
            )
            liquidity = min(liquidity0, liquidity1)
        else:
            # Current price above range, only amount1 is active
            liquidity = UniswapV3Calculator.get_liquidity_for_amount1(
                sqrt_ratio_a_x96, sqrt_ratio_b_x96, amount1
            )
            
        return liquidity
    
    @staticmethod
    def get_liquidity_for_amount0(
        sqrt_ratio_a_x96: int,
        sqrt_ratio_b_x96: int,
        amount0: int
    ) -> int:
        """Calculate liquidity for a given amount0."""
        if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
            sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96
            
        intermediate = sqrt_ratio_a_x96 * sqrt_ratio_b_x96 // Q96
        return amount0 * intermediate // (sqrt_ratio_b_x96 - sqrt_ratio_a_x96)
    
    @staticmethod
    def get_liquidity_for_amount1(
        sqrt_ratio_a_x96: int,
        sqrt_ratio_b_x96: int,
        amount1: int
    ) -> int:
        """Calculate liquidity for a given amount1."""
        if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
            sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96
            
        return amount1 * Q96 // (sqrt_ratio_b_x96 - sqrt_ratio_a_x96)
    
    def calculate_position(
        self,
        pool_state,
        tick_lower: int,
        tick_upper: int,
        amount0_desired: float,
        amount1_desired: float
    ) -> Position:
        """
        Calculate optimal liquidity position given desired amounts.
        Returns the actual amounts that will be used.
        """
        # Convert amounts to proper units
        amount0_wei = int(amount0_desired * 10**6)  # USDC has 6 decimals
        amount1_wei = int(amount1_desired * 10**18)  # WETH has 18 decimals
        
        # Get sqrt prices at boundaries
        sqrt_ratio_a = self.get_sqrt_ratio_at_tick(tick_lower)
        sqrt_ratio_b = self.get_sqrt_ratio_at_tick(tick_upper)
        sqrt_ratio_current = pool_state.sqrt_price_x96
        
        # Calculate liquidity
        liquidity = self.get_liquidity_for_amounts(
            sqrt_ratio_current,
            sqrt_ratio_a,
            sqrt_ratio_b,
            amount0_wei,
            amount1_wei
        )
        
        # Calculate actual amounts used
        if sqrt_ratio_current <= sqrt_ratio_a:
            # Below range
            amount0_actual = self.get_amount0_for_liquidity(
                sqrt_ratio_a, sqrt_ratio_b, liquidity
            )
            amount1_actual = 0
        elif sqrt_ratio_current < sqrt_ratio_b:
            # In range
            amount0_actual = self.get_amount0_for_liquidity(
                sqrt_ratio_current, sqrt_ratio_b, liquidity
            )
            amount1_actual = self.get_amount1_for_liquidity(
                sqrt_ratio_a, sqrt_ratio_current, liquidity
            )
        else:
            # Above range
            amount0_actual = 0
            amount1_actual = self.get_amount1_for_liquidity(
                sqrt_ratio_a, sqrt_ratio_b, liquidity
            )
        
        return Position(
            liquidity=liquidity,
            tick_lower=tick_lower,
            tick_upper=tick_upper,
            amount0=amount0_actual / 10**6,  # Convert back to USDC
            amount1=amount1_actual / 10**18  # Convert back to WETH
        )
    
    def get_position_amounts(
        self,
        position: Position,
        sqrt_price_x96: int
    ) -> Tuple[float, float]:
        """Get current token amounts for a position at given price."""
        sqrt_ratio_a = self.get_sqrt_ratio_at_tick(position.tick_lower)
        sqrt_ratio_b = self.get_sqrt_ratio_at_tick(position.tick_upper)
        
        if sqrt_price_x96 <= sqrt_ratio_a:
            # Below range - all liquidity is in token0
            amount0 = self.get_amount0_for_liquidity(
                sqrt_ratio_a, sqrt_ratio_b, position.liquidity
            )
            amount1 = 0
        elif sqrt_price_x96 < sqrt_ratio_b:
            # In range - liquidity is split between both tokens
            amount0 = self.get_amount0_for_liquidity(
                sqrt_price_x96, sqrt_ratio_b, position.liquidity
            )
            amount1 = self.get_amount1_for_liquidity(
                sqrt_ratio_a, sqrt_price_x96, position.liquidity
            )
        else:
            # Above range - all liquidity is in token1
            amount0 = 0
            amount1 = self.get_amount1_for_liquidity(
                sqrt_ratio_a, sqrt_ratio_b, position.liquidity
            )
        
        return (
            amount0 / 10**6,   # USDC
            amount1 / 10**18   # WETH
        ) 