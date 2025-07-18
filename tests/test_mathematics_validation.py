"""
Comprehensive test suite for mathematical validation.
Tests all core calculations to ensure correctness and prevent issues like negative liquidity.
"""

import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import numpy as np

from src.uniswap import UniswapV3Calculator, Position
from src.analysis import PositionAnalyzer
from src.blockchain import PoolState, SwapEvent


class TestLiquidityDistribution(unittest.TestCase):
    """Test liquidity distribution calculations."""
    
    @patch('src.blockchain.data_fetcher.Web3')
    async def test_liquidity_never_negative(self, mock_web3_class):
        """Liquidity should never be negative."""
        from src.blockchain import DataFetcher
        
        # Mock Web3 instance
        mock_web3 = Mock()
        mock_web3_class.return_value = mock_web3
        mock_web3.is_connected.return_value = True
        mock_web3.eth.contract.return_value = Mock()
        
        # Create DataFetcher with mocked Web3
        data_fetcher = DataFetcher("http://mock-rpc", cache=None)
        
        # Mock the contract and its methods
        mock_contract = MagicMock()
        data_fetcher.w3.eth.contract.return_value = mock_contract
        
        # Mock tick spacing
        mock_contract.functions.tickSpacing.return_value.call.return_value = 10
        
        # Mock slot0 (current tick at 200000)
        mock_contract.functions.slot0.return_value.call.return_value = [
            0, 200000, 0, 0, 0, 0, True  # [sqrtPriceX96, tick, ...]
        ]
        
        # Mock current liquidity
        mock_contract.functions.liquidity.return_value.call.return_value = 1000000000
        
        # Mock tick data with negative liquidity_net
        tick_data = {
            199980: (100000, -500000, 0, 0, 0, 0, 0, True),  # negative net
            199990: (200000, -300000, 0, 0, 0, 0, 0, True),  # negative net
            200000: (300000, -300000, 0, 0, 0, 0, 0, True),  # negative net
            200010: (150000, 200000, 0, 0, 0, 0, 0, True),   # positive net
            200020: (100000, -100000, 0, 0, 0, 0, 0, True),  # negative net
        }
        
        def mock_ticks(tick):
            return Mock(call=Mock(return_value=tick_data.get(tick, (0, 0, 0, 0, 0, 0, 0, False))))
        
        mock_contract.functions.ticks.side_effect = mock_ticks
        
        # Override rate limiting
        data_fetcher._rate_limited_call = AsyncMock(side_effect=lambda func: func())
        
        # Get liquidity distribution
        distribution = await data_fetcher.get_liquidity_distribution(
            "0x1234", 1000, 199970, 200030
        )
        
        # Assert all values are non-negative
        for tick, liquidity in distribution.items():
            self.assertGreaterEqual(liquidity, 0, 
                f"Liquidity at tick {tick} is negative: {liquidity}")
    
    def test_tick_alignment(self):
        """Test that ticks are properly aligned with tick spacing."""
        tick_spacing = 10
        
        # Test lower bound alignment
        tick_lower = 199983
        aligned_lower = tick_lower - (tick_lower % tick_spacing)
        self.assertEqual(aligned_lower, 199980)
        
        # Test upper bound alignment
        tick_upper = 200017
        aligned_upper = tick_upper + (tick_spacing - (tick_upper % tick_spacing)) % tick_spacing
        self.assertEqual(aligned_upper, 200020)


class TestFeeCalculations(unittest.TestCase):
    """Test fee calculation logic."""
    
    def setUp(self):
        self.calculator = UniswapV3Calculator()
        self.analyzer = PositionAnalyzer(self.calculator)
    
    def test_fee_distribution_logic(self):
        """Test that fees are distributed correctly across ticks."""
        position = Position(
            liquidity=1000000,
            tick_lower=100,
            tick_upper=110,
            amount0=1000,
            amount1=1
        )
        
        # Mock liquidity distribution - our position has 10% of pool
        liquidity_distribution = {tick: 10000000 for tick in range(90, 120)}
        
        swap_events = [
            SwapEvent(
                sender="0x1",
                recipient="0x2",
                amount0=-1000000000,  # 1000 USDC
                amount1=500000000000000000,  # 0.5 ETH
                sqrt_price_x96=0,
                liquidity=0,
                tick=105,
                block_number=1,
                transaction_hash="0xabc"
            )
        ]
        
        # Run synchronously for testing
        async def run_test():
            return await self.analyzer.estimate_fees_from_swaps(
                position, swap_events, liquidity_distribution, 500  # 0.05% fee
            )
        
        fee_by_tick = asyncio.run(run_test())
        
        # Calculate expected fees
        # Fee = 1000 USDC * 0.05% = 0.5 USDC
        # Our share = 10% = 0.05 USDC
        # Distributed across 6 ticks (100-105) = 0.05/6 ≈ 0.00833 USDC per tick
        
        total_usdc_fees = sum(fees[0] for fees in fee_by_tick.values())
        self.assertAlmostEqual(total_usdc_fees, 0.05, places=4)
        
        # Verify no fees outside position range
        for tick, fees in fee_by_tick.items():
            if tick < 100 or tick > 110:
                self.assertEqual(fees[0], 0)
                self.assertEqual(fees[1], 0)
    
    def test_zero_liquidity_handling(self):
        """Test fee calculation when liquidity is zero."""
        position = Position(
            liquidity=1000000,
            tick_lower=100,
            tick_upper=110,
            amount0=1000,
            amount1=1
        )
        
        # Zero liquidity at some ticks
        liquidity_distribution = {
            tick: 0 if tick == 105 else 10000000 
            for tick in range(90, 120)
        }
        
        swap_events = [
            SwapEvent(
                sender="0x1",
                recipient="0x2",
                amount0=-1000000000,
                amount1=500000000000000000,
                sqrt_price_x96=0,
                liquidity=0,
                tick=106,
                block_number=1,
                transaction_hash="0xabc"
            )
        ]
        
        # Should not crash with zero liquidity
        async def run_test():
            return await self.analyzer.estimate_fees_from_swaps(
                position, swap_events, liquidity_distribution, 500
            )
        
        fee_by_tick = asyncio.run(run_test())
        
        # Verify it handled zero liquidity gracefully
        self.assertIsInstance(fee_by_tick, dict)


class TestImpermanentLoss(unittest.TestCase):
    """Test impermanent loss calculations."""
    
    def setUp(self):
        self.calculator = UniswapV3Calculator()
        self.analyzer = PositionAnalyzer(self.calculator)
    
    def test_no_il_without_price_change(self):
        """No IL when price doesn't change."""
        il_amount, il_pct = self.analyzer.calculate_impermanent_loss(
            initial_usdc=50000,
            initial_weth=25,
            final_usdc=50000,
            final_weth=25,
            initial_eth_price=2000,
            final_eth_price=2000
        )
        
        self.assertAlmostEqual(il_amount, 0, places=2)
        self.assertAlmostEqual(il_pct, 0, places=2)
    
    def test_il_with_price_increase(self):
        """IL calculation when ETH price increases."""
        # Price doubles: more USDC, less WETH in position
        il_amount, il_pct = self.analyzer.calculate_impermanent_loss(
            initial_usdc=50000,
            initial_weth=25,
            final_usdc=70710.68,  # sqrt(2) * 50000
            final_weth=17.677,     # 25 / sqrt(2)
            initial_eth_price=2000,
            final_eth_price=4000
        )
        
        # With 2x price change, IL should be around 5.72%
        self.assertGreater(il_amount, 0)  # Should have IL
        self.assertLess(il_pct, 10)  # But less than 10%
    
    def test_il_calculation_correctness(self):
        """Verify IL calculation matches expected formula."""
        # Test with known values
        initial_value = 100000
        
        # For a 50% price increase:
        # - Price ratio = 1.5
        # - sqrt(1.5) ≈ 1.2247
        # - Final USDC ≈ 50000 * 1.2247 = 61235
        # - Final WETH ≈ 25 / 1.2247 = 20.412
        
        # IL calculation:
        # HODL value = 50000 + 25 * 3000 = 125000
        # LP value = 61235 + 20.412 * 3000 = 122471
        # IL = 125000 - 122471 = 2529
        # IL% = 2529 / 100000 = 2.529%
        
        il_amount, il_pct = self.analyzer.calculate_impermanent_loss(
            initial_usdc=50000,
            initial_weth=25,
            final_usdc=61237.24,  # sqrt(1.5) * 50000
            final_weth=20.412,     # 25 / sqrt(1.5)
            initial_eth_price=2000,
            final_eth_price=3000
        )
        
        # Updated expectation based on our IL calculation method
        self.assertAlmostEqual(il_pct, 2.53, places=1)


class TestPositionCalculations(unittest.TestCase):
    """Test position calculation logic."""
    
    def setUp(self):
        self.calculator = UniswapV3Calculator()
    
    def test_position_liquidity_positive(self):
        """Position liquidity should always be positive."""
        pool_state = PoolState(
            sqrt_price_x96=self.calculator.get_sqrt_ratio_at_tick(200550),
            tick=200550,
            liquidity=1000000000,
            fee=500,
            tick_spacing=10,
            token0="0xusdc",
            token1="0xweth",
            block_number=1000
        )
        
        position = self.calculator.calculate_position(
            pool_state,
            tick_lower=200540,
            tick_upper=200560,
            amount0_desired=10000,
            amount1_desired=5
        )
        
        self.assertGreater(position.liquidity, 0)
        self.assertGreaterEqual(position.amount0, 0)
        self.assertGreaterEqual(position.amount1, 0)
    
    def test_position_amounts_at_boundaries(self):
        """Test position calculations at range boundaries."""
        # Below range - all in token0
        position = Position(liquidity=1000000, tick_lower=100, tick_upper=200, amount0=1000, amount1=0.5)
        
        sqrt_price_below = self.calculator.get_sqrt_ratio_at_tick(50)
        amount0, amount1 = self.calculator.get_position_amounts(position, sqrt_price_below)
        
        self.assertGreater(amount0, 0)
        self.assertEqual(amount1, 0)
        
        # Above range - all in token1
        sqrt_price_above = self.calculator.get_sqrt_ratio_at_tick(250)
        amount0, amount1 = self.calculator.get_position_amounts(position, sqrt_price_above)
        
        self.assertEqual(amount0, 0)
        self.assertGreater(amount1, 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""
    
    def test_extreme_tick_values(self):
        """Test calculations with extreme tick values."""
        calculator = UniswapV3Calculator()
        
        # Maximum tick
        max_tick = 887272
        sqrt_max = calculator.get_sqrt_ratio_at_tick(max_tick)
        self.assertGreater(sqrt_max, 0)
        
        # Minimum tick
        min_tick = -887272
        sqrt_min = calculator.get_sqrt_ratio_at_tick(min_tick)
        self.assertGreater(sqrt_min, 0)
        self.assertLess(sqrt_min, sqrt_max)
    
    def test_zero_amounts(self):
        """Test handling of zero token amounts."""
        calculator = UniswapV3Calculator()
        pool_state = PoolState(
            sqrt_price_x96=calculator.get_sqrt_ratio_at_tick(0),
            tick=0,
            liquidity=1000000,
            fee=500,
            tick_spacing=10,
            token0="0xusdc",
            token1="0xweth",
            block_number=1000
        )
        
        # Zero amounts should result in zero liquidity
        position = calculator.calculate_position(
            pool_state,
            tick_lower=-100,
            tick_upper=100,
            amount0_desired=0,
            amount1_desired=0
        )
        
        self.assertEqual(position.liquidity, 0)


if __name__ == '__main__':
    # Run tests
    unittest.main() 