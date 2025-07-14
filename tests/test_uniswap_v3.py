"""
Unit tests for Uniswap V3 calculator module.
"""

import unittest
import math
from decimal import Decimal

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.uniswap import UniswapV3Calculator, Position, Q96


class TestUniswapV3Calculator(unittest.TestCase):
    """Test cases for UniswapV3Calculator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calculator = UniswapV3Calculator()
    
    def test_tick_to_sqrt_price_conversion(self):
        """Test tick to sqrt price conversion."""
        # Test tick 0 should give sqrt(1) * Q96
        tick_0_price = self.calculator.tick_to_sqrt_price_x96(0)
        expected = Q96
        self.assertAlmostEqual(tick_0_price, expected, delta=Q96 // 1000)
        
        # Test positive tick
        tick_100_price = self.calculator.tick_to_sqrt_price_x96(100)
        expected_100 = int(math.sqrt(1.0001 ** 100) * Q96)
        self.assertAlmostEqual(tick_100_price, expected_100, delta=expected_100 // 1000)
        
        # Test negative tick
        tick_neg_100_price = self.calculator.tick_to_sqrt_price_x96(-100)
        expected_neg_100 = int(math.sqrt(1.0001 ** -100) * Q96)
        self.assertAlmostEqual(tick_neg_100_price, expected_neg_100, delta=expected_neg_100 // 1000)
    
    def test_sqrt_price_to_tick_conversion(self):
        """Test sqrt price to tick conversion."""
        # Test sqrt price at tick 0
        tick = self.calculator.sqrt_price_x96_to_tick(Q96)
        self.assertEqual(tick, 0)
        
        # Test round trip conversion
        original_tick = 1000
        sqrt_price = self.calculator.tick_to_sqrt_price_x96(original_tick)
        converted_tick = self.calculator.sqrt_price_x96_to_tick(sqrt_price)
        self.assertAlmostEqual(converted_tick, original_tick, delta=1)
    
    def test_get_sqrt_ratio_at_tick(self):
        """Test get_sqrt_ratio_at_tick function."""
        # Test tick 0
        ratio_0 = self.calculator.get_sqrt_ratio_at_tick(0)
        expected_0 = Q96
        # Allow for some precision loss in the optimized calculation
        self.assertAlmostEqual(ratio_0 / Q96, 1.0, places=10)
        
        # Test maximum tick
        max_tick = 887272
        ratio_max = self.calculator.get_sqrt_ratio_at_tick(max_tick)
        self.assertGreater(ratio_max, 0)
        
        # Test minimum tick
        min_tick = -887272
        ratio_min = self.calculator.get_sqrt_ratio_at_tick(min_tick)
        self.assertGreater(ratio_min, 0)
        self.assertLess(ratio_min, ratio_0)
    
    def test_liquidity_calculations(self):
        """Test liquidity calculation functions."""
        sqrt_ratio_a = self.calculator.get_sqrt_ratio_at_tick(0)
        sqrt_ratio_b = self.calculator.get_sqrt_ratio_at_tick(100)
        liquidity = 1000000
        
        # Test amount0 calculation
        amount0 = self.calculator.get_amount0_for_liquidity(
            sqrt_ratio_a, sqrt_ratio_b, liquidity
        )
        self.assertGreater(amount0, 0)
        
        # Test amount1 calculation
        amount1 = self.calculator.get_amount1_for_liquidity(
            sqrt_ratio_a, sqrt_ratio_b, liquidity
        )
        self.assertGreater(amount1, 0)
        
        # Test that swapping sqrt ratios doesn't change results
        amount0_swapped = self.calculator.get_amount0_for_liquidity(
            sqrt_ratio_b, sqrt_ratio_a, liquidity
        )
        self.assertEqual(amount0, amount0_swapped)
    
    def test_position_calculation(self):
        """Test position calculation."""
        # Mock pool state
        class MockPoolState:
            def __init__(self):
                self.sqrt_price_x96 = UniswapV3Calculator.get_sqrt_ratio_at_tick(200550)
                self.tick = 200550
        
        pool_state = MockPoolState()
        tick_lower = 200540
        tick_upper = 200560
        amount0_desired = 10000.0  # USDC
        amount1_desired = 5.0       # WETH
        
        position = self.calculator.calculate_position(
            pool_state,
            tick_lower,
            tick_upper,
            amount0_desired,
            amount1_desired
        )
        
        # Verify position properties
        self.assertIsInstance(position, Position)
        self.assertEqual(position.tick_lower, tick_lower)
        self.assertEqual(position.tick_upper, tick_upper)
        self.assertGreater(position.liquidity, 0)
        
        # Verify amounts are within desired bounds
        self.assertLessEqual(position.amount0, amount0_desired)
        self.assertLessEqual(position.amount1, amount1_desired)
        
        # At least one amount should be close to desired
        # (due to the nature of concentrated liquidity)
        amount0_ratio = position.amount0 / amount0_desired if amount0_desired > 0 else 0
        amount1_ratio = position.amount1 / amount1_desired if amount1_desired > 0 else 0
        self.assertTrue(amount0_ratio > 0.9 or amount1_ratio > 0.9)
    
    def test_get_position_amounts(self):
        """Test getting position amounts at different prices."""
        # Create a position properly using calculate_position
        class MockPoolState:
            def __init__(self, tick):
                self.sqrt_price_x96 = UniswapV3Calculator.get_sqrt_ratio_at_tick(tick)
                self.tick = tick
        
        # Create position at tick 200550 (within range)
        pool_state = MockPoolState(200550)
        position = self.calculator.calculate_position(
            pool_state,
            tick_lower=200540,
            tick_upper=200560,
            amount0_desired=10000.0,  # USDC
            amount1_desired=5.0       # WETH
        )
        
        # Test at different price points
        # Below range
        sqrt_price_below = self.calculator.get_sqrt_ratio_at_tick(200530)
        amount0_below, amount1_below = self.calculator.get_position_amounts(
            position, sqrt_price_below
        )
        # When below range, all liquidity converts to token0
        if position.liquidity > 0:
            self.assertGreater(amount0_below, 0)
        self.assertEqual(amount1_below, 0)
        
        # Within range
        sqrt_price_within = self.calculator.get_sqrt_ratio_at_tick(200550)
        amount0_within, amount1_within = self.calculator.get_position_amounts(
            position, sqrt_price_within
        )
        # When in range, both tokens should have value
        if position.liquidity > 0:
            self.assertGreater(amount0_within, 0)
            self.assertGreater(amount1_within, 0)
        
        # Above range
        sqrt_price_above = self.calculator.get_sqrt_ratio_at_tick(200570)
        amount0_above, amount1_above = self.calculator.get_position_amounts(
            position, sqrt_price_above
        )
        # When above range, all liquidity converts to token1
        self.assertEqual(amount0_above, 0)
        if position.liquidity > 0:
            self.assertGreater(amount1_above, 0)


if __name__ == '__main__':
    unittest.main() 