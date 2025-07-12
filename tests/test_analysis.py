"""
Unit tests for the analysis module.
"""

import unittest
from unittest.mock import Mock, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis import PositionAnalyzer
from uniswap_v3 import UniswapV3Calculator, Position
from data_fetcher import PoolState, SwapEvent


class TestPositionAnalyzer(unittest.TestCase):
    """Test cases for PositionAnalyzer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calculator = UniswapV3Calculator()
        self.analyzer = PositionAnalyzer(self.calculator)
    
    def test_calculate_impermanent_loss(self):
        """Test impermanent loss calculation."""
        # Test case 1: No price change, no IL
        initial_usdc = 5000.0
        initial_weth = 2.5
        final_usdc = 5000.0
        final_weth = 2.5
        eth_price_start = 2000.0
        eth_price_end = 2000.0
        
        il_amount, il_pct = self.analyzer.calculate_impermanent_loss(
            initial_usdc, initial_weth,
            final_usdc, final_weth,
            eth_price_start, eth_price_end
        )
        
        self.assertAlmostEqual(il_amount, 0.0, places=2)
        self.assertAlmostEqual(il_pct, 0.0, places=2)
        
        # Test case 2: Price increase with rebalancing
        final_usdc_2 = 6000.0  # More USDC (sold WETH)
        final_weth_2 = 2.0     # Less WETH
        eth_price_end_2 = 2500.0
        
        il_amount_2, il_pct_2 = self.analyzer.calculate_impermanent_loss(
            initial_usdc, initial_weth,
            final_usdc_2, final_weth_2,
            eth_price_start, eth_price_end_2
        )
        
        # There should be some IL when price changes
        self.assertGreater(il_amount_2, 0)
        self.assertGreater(il_pct_2, 0)
    
    def test_estimate_fees_from_swaps(self):
        """Test fee estimation from swap events."""
        # Create test position
        position = Position(
            liquidity=1000000,
            tick_lower=200540,
            tick_upper=200560,
            amount0=5000.0,
            amount1=2.5
        )
        
        # Create test swap events
        swap_events = [
            SwapEvent(
                sender="0x123",
                recipient="0x456",
                amount0=-1000000,  # 1 USDC sold (negative)
                amount1=500000000000000000,  # 0.5 WETH bought
                sqrt_price_x96=1000000000000000000000,
                liquidity=10000000,
                tick=200545,
                block_number=17618650,
                transaction_hash="0xabc"
            ),
            SwapEvent(
                sender="0x789",
                recipient="0xdef",
                amount0=2000000,  # 2 USDC bought
                amount1=-1000000000000000000,  # 1 WETH sold (negative)
                sqrt_price_x96=1100000000000000000000,
                liquidity=10000000,
                tick=200550,
                block_number=17618700,
                transaction_hash="0xdef"
            )
        ]
        
        # Create liquidity distribution
        liquidity_distribution = {tick: 10000000 for tick in range(200530, 200571)}
        
        # Pool fee is 500 (0.05%)
        pool_fee = 500
        
        fee_by_tick = self.analyzer.estimate_fees_from_swaps(
            position, swap_events, liquidity_distribution, pool_fee
        )
        
        # Verify fees are calculated
        self.assertIsInstance(fee_by_tick, dict)
        self.assertGreater(len(fee_by_tick), 0)
        
        # Verify all ticks in position range have fee entries
        for tick in range(position.tick_lower, position.tick_upper + 1):
            self.assertIn(tick, fee_by_tick)
            self.assertIsInstance(fee_by_tick[tick], tuple)
            self.assertEqual(len(fee_by_tick[tick]), 2)
        
        # Verify some fees were earned
        total_usdc_fees = sum(fees[0] for fees in fee_by_tick.values())
        total_weth_fees = sum(fees[1] for fees in fee_by_tick.values())
        self.assertGreaterEqual(total_usdc_fees, 0)
        self.assertGreaterEqual(total_weth_fees, 0)
    
    def test_analyze_position(self):
        """Test complete position analysis."""
        # Create test position
        position = Position(
            liquidity=1000000,
            tick_lower=200540,
            tick_upper=200560,
            amount0=45000.0,  # USDC
            amount1=22.5      # WETH
        )
        
        # Create mock pool states
        pool_state_start = PoolState(
            sqrt_price_x96=1000000000000000000000,
            tick=200550,
            liquidity=10000000,
            fee=500,
            tick_spacing=10,
            token0="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            token1="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            block_number=17618642
        )
        
        pool_state_end = PoolState(
            sqrt_price_x96=1100000000000000000000,
            tick=200555,
            liquidity=10000000,
            fee=500,
            tick_spacing=10,
            token0="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            token1="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            block_number=17618742
        )
        
        # Mock liquidity distribution and swap events
        liquidity_distribution = {tick: 10000000 for tick in range(200530, 200571)}
        swap_events = []  # Empty for simplicity
        
        eth_price_start = 2000.0
        eth_price_end = 2100.0
        
        # Analyze position
        results = self.analyzer.analyze_position(
            position,
            pool_state_start,
            pool_state_end,
            liquidity_distribution,
            swap_events,
            eth_price_start,
            eth_price_end
        )
        
        # Verify results structure
        expected_keys = [
            'final_usdc', 'final_weth', 'final_value_usdc',
            'impermanent_loss', 'impermanent_loss_pct',
            'fees_usdc', 'fees_weth', 'total_fees_usdc',
            'fee_by_tick', 'unused_usdc', 'unused_weth',
            'unused_value', 'final_total_value', 'pnl', 'pnl_pct',
            'eth_price_start', 'eth_price_end', 'position_liquidity',
            'initial_usdc_in_position', 'initial_weth_in_position'
        ]
        
        for key in expected_keys:
            self.assertIn(key, results)
        
        # Verify some basic properties
        self.assertEqual(results['eth_price_start'], eth_price_start)
        self.assertEqual(results['eth_price_end'], eth_price_end)
        self.assertEqual(results['position_liquidity'], position.liquidity)
        self.assertGreaterEqual(results['final_total_value'], 0)


if __name__ == '__main__':
    unittest.main() 