"""
Comprehensive test scenarios for Uniswap V3 position analysis.
Covers all major edge cases and real-world scenarios.
"""

import unittest
import asyncio
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from decimal import Decimal

from src.blockchain import DataFetcher, PoolState, SwapEvent
from src.uniswap import UniswapV3Calculator, Position
from src.analysis import PositionAnalyzer


class TestLiquidityDistributionScenarios(unittest.TestCase):
    """Test various liquidity distribution scenarios."""
    
    def setUp(self):
        self.data_fetcher = DataFetcher("http://mock-rpc", cache=None)
    
    @patch('src.blockchain.data_fetcher.Web3')
    async def test_negative_liquidity_net_accumulation(self, mock_web3):
        """Test handling of multiple negative liquidity_net values."""
        mock_contract = Mock()
        mock_web3.return_value.eth.contract.return_value = mock_contract
        
        mock_contract.functions.tickSpacing.return_value.call.return_value = 10
        mock_contract.functions.slot0.return_value.call.return_value = [0, 200000, 0, 0, 0, 0, True]
        mock_contract.functions.liquidity.return_value.call.return_value = 10000000
        
        # All negative liquidity_net values
        tick_data = {
            199980: (1000000, -1000000, 0, 0, 0, 0, 0, True),
            199990: (2000000, -2000000, 0, 0, 0, 0, 0, True),
            200000: (3000000, -3000000, 0, 0, 0, 0, 0, True),
            200010: (1500000, -1500000, 0, 0, 0, 0, 0, True),
            200020: (500000, -500000, 0, 0, 0, 0, 0, True),
        }
        
        mock_contract.functions.ticks.return_value.call.side_effect = lambda t: tick_data.get(t, (0, 0, 0, 0, 0, 0, 0, False))
        
        distribution = await self.data_fetcher.get_liquidity_distribution(
            "0x1234", 1000, 199970, 200030
        )
        
        # All liquidity values should be non-negative
        for tick, liquidity in distribution.items():
            self.assertGreaterEqual(liquidity, 0)
    
    @patch('src.blockchain.data_fetcher.Web3')
    async def test_sparse_tick_data(self, mock_web3):
        """Test with very sparse tick data (most ticks uninitialized)."""
        mock_contract = Mock()
        mock_web3.return_value.eth.contract.return_value = mock_contract
        
        mock_contract.functions.tickSpacing.return_value.call.return_value = 60  # Wide spacing
        mock_contract.functions.slot0.return_value.call.return_value = [0, 200040, 0, 0, 0, 0, True]
        mock_contract.functions.liquidity.return_value.call.return_value = 5000000
        
        # Only 2 initialized ticks in a wide range
        tick_data = {
            199980: (100000, 100000, 0, 0, 0, 0, 0, True),
            200040: (200000, -50000, 0, 0, 0, 0, 0, True),
        }
        
        mock_contract.functions.ticks.return_value.call.side_effect = lambda t: tick_data.get(t, (0, 0, 0, 0, 0, 0, 0, False))
        
        distribution = await self.data_fetcher.get_liquidity_distribution(
            "0x1234", 1000, 199900, 200100
        )
        
        # Should interpolate liquidity correctly
        self.assertEqual(distribution[200040], 5000000)  # Current tick
        # Ticks between should maintain liquidity levels
        for tick in range(199981, 200040):
            self.assertGreaterEqual(distribution[tick], 0)
    
    @patch('src.blockchain.data_fetcher.Web3')
    async def test_current_tick_at_boundary(self, mock_web3):
        """Test when current tick is at the extreme boundary."""
        mock_contract = Mock()
        mock_web3.return_value.eth.contract.return_value = mock_contract
        
        mock_contract.functions.tickSpacing.return_value.call.return_value = 10
        # Current tick at the lower boundary of our range
        mock_contract.functions.slot0.return_value.call.return_value = [0, 199980, 0, 0, 0, 0, True]
        mock_contract.functions.liquidity.return_value.call.return_value = 1000000
        
        tick_data = {
            199980: (100000, 50000, 0, 0, 0, 0, 0, True),
            199990: (150000, -30000, 0, 0, 0, 0, 0, True),
            200000: (200000, 100000, 0, 0, 0, 0, 0, True),
        }
        
        mock_contract.functions.ticks.return_value.call.side_effect = lambda t: tick_data.get(t, (0, 0, 0, 0, 0, 0, 0, False))
        
        distribution = await self.data_fetcher.get_liquidity_distribution(
            "0x1234", 1000, 199980, 200010
        )
        
        # Verify correct liquidity at boundaries
        self.assertEqual(distribution[199980], 1000000)  # Current tick
        self.assertGreaterEqual(distribution[200000], 0)


class TestFeeCalculationScenarios(unittest.TestCase):
    """Test various fee calculation scenarios."""
    
    def setUp(self):
        self.calculator = UniswapV3Calculator()
        self.analyzer = PositionAnalyzer(self.calculator)
    
    async def test_100_percent_liquidity_share(self):
        """Test fee calculation when position has 100% of pool liquidity."""
        position = Position(
            liquidity=10000000,
            tick_lower=100,
            tick_upper=200,
            amount0=50000,
            amount1=25
        )
        
        # Position has all the liquidity
        liquidity_distribution = {tick: 10000000 for tick in range(50, 250)}
        
        swap_events = [
            SwapEvent(
                sender="0x1",
                recipient="0x2",
                amount0=-10000000000,  # 10,000 USDC
                amount1=5000000000000000000,  # 5 ETH
                sqrt_price_x96=0,
                liquidity=0,
                tick=150,
                block_number=1,
                transaction_hash="0xabc"
            )
        ]
        
        fee_by_tick = await self.analyzer.estimate_fees_from_swaps(
            position, swap_events, liquidity_distribution, 3000  # 0.3% fee
        )
        
        # Should get 100% of fees
        total_usdc_fees = sum(fees[0] for fees in fee_by_tick.values())
        expected_fees = 10000 * 0.003  # 30 USDC
        self.assertAlmostEqual(total_usdc_fees, expected_fees, places=2)
    
    async def test_swap_entirely_outside_range(self):
        """Test when swap occurs entirely outside position range."""
        position = Position(
            liquidity=1000000,
            tick_lower=100,
            tick_upper=200,
            amount0=10000,
            amount1=5
        )
        
        liquidity_distribution = {tick: 10000000 for tick in range(0, 300)}
        
        # Swap from tick 250 to 280 (outside our 100-200 range)
        swap_events = [
            SwapEvent(
                sender="0x1",
                recipient="0x2",
                amount0=-5000000000,
                amount1=2500000000000000000,
                sqrt_price_x96=0,
                liquidity=0,
                tick=280,
                block_number=1,
                transaction_hash="0xabc"
            )
        ]
        
        # Assuming previous tick was 250
        fee_by_tick = await self.analyzer.estimate_fees_from_swaps(
            position, swap_events, liquidity_distribution, 500
        )
        
        # Should earn no fees
        total_fees = sum(fees[0] + fees[1] for fees in fee_by_tick.values())
        self.assertEqual(total_fees, 0)
    
    async def test_large_swap_crossing_many_ticks(self):
        """Test a large swap crossing many ticks."""
        position = Position(
            liquidity=1000000,
            tick_lower=100,
            tick_upper=300,
            amount0=100000,
            amount1=50
        )
        
        # Varying liquidity across ticks
        liquidity_distribution = {}
        for tick in range(50, 350):
            # Liquidity increases towards middle of range
            distance_from_200 = abs(tick - 200)
            liquidity_distribution[tick] = max(1000000, 10000000 - distance_from_200 * 50000)
        
        # Large swap crossing 100 ticks
        swap_events = [
            SwapEvent(
                sender="0x1",
                recipient="0x2",
                amount0=-100000000000,  # 100,000 USDC
                amount1=50000000000000000000,  # 50 ETH
                sqrt_price_x96=0,
                liquidity=0,
                tick=250,  # End tick
                block_number=1,
                transaction_hash="0xabc"
            )
        ]
        
        fee_by_tick = await self.analyzer.estimate_fees_from_swaps(
            position, swap_events, liquidity_distribution, 500
        )
        
        # Fees should be distributed across many ticks
        active_ticks = [t for t, fees in fee_by_tick.items() if fees[0] > 0]
        self.assertGreater(len(active_ticks), 50)  # Should span many ticks
    
    async def test_bidirectional_swaps(self):
        """Test swaps in both directions (buy and sell)."""
        position = Position(
            liquidity=1000000,
            tick_lower=100,
            tick_upper=200,
            amount0=10000,
            amount1=5
        )
        
        liquidity_distribution = {tick: 10000000 for tick in range(50, 250)}
        
        swap_events = [
            # Buy ETH (negative USDC, positive ETH)
            SwapEvent(
                sender="0x1",
                recipient="0x2",
                amount0=-5000000000,  # -5000 USDC
                amount1=2500000000000000000,  # +2.5 ETH
                sqrt_price_x96=0,
                liquidity=0,
                tick=160,
                block_number=1,
                transaction_hash="0xabc"
            ),
            # Sell ETH (positive USDC, negative ETH)
            SwapEvent(
                sender="0x1",
                recipient="0x2",
                amount0=4000000000,  # +4000 USDC
                amount1=-2000000000000000000,  # -2 ETH
                sqrt_price_x96=0,
                liquidity=0,
                tick=140,
                block_number=2,
                transaction_hash="0xdef"
            )
        ]
        
        fee_by_tick = await self.analyzer.estimate_fees_from_swaps(
            position, swap_events, liquidity_distribution, 500
        )
        
        # Should earn fees from both swaps
        total_usdc_fees = sum(fees[0] for fees in fee_by_tick.values())
        total_eth_fees = sum(fees[1] for fees in fee_by_tick.values())
        
        self.assertGreater(total_usdc_fees, 0)
        self.assertGreater(total_eth_fees, 0)


class TestImpermanentLossScenarios(unittest.TestCase):
    """Test various impermanent loss scenarios."""
    
    def setUp(self):
        self.calculator = UniswapV3Calculator()
        self.analyzer = PositionAnalyzer(self.calculator)
    
    def test_small_price_changes(self):
        """Test IL with small price changes (1%, 5%, 10%)."""
        initial_usdc = 50000
        initial_weth = 25
        initial_eth_price = 2000
        
        test_cases = [
            (1.01, "1% increase"),
            (0.99, "1% decrease"),
            (1.05, "5% increase"),
            (0.95, "5% decrease"),
            (1.10, "10% increase"),
            (0.90, "10% decrease"),
        ]
        
        for price_multiplier, description in test_cases:
            final_eth_price = initial_eth_price * price_multiplier
            
            # Calculate expected position after rebalancing
            # Using constant product formula: k = x * y
            k = initial_usdc * initial_weth
            price_ratio = np.sqrt(price_multiplier)
            
            final_usdc = initial_usdc * price_ratio
            final_weth = initial_weth / price_ratio
            
            il_amount, il_pct = self.analyzer.calculate_impermanent_loss(
                initial_usdc, initial_weth,
                final_usdc, final_weth,
                initial_eth_price, final_eth_price
            )
            
            # Small price changes should have small IL
            self.assertLess(abs(il_pct), 1, f"IL too high for {description}")
            
            # IL should always be negative (loss)
            self.assertGreaterEqual(il_amount, 0, f"IL should be non-negative for {description}")
    
    def test_extreme_price_changes(self):
        """Test IL with extreme price changes."""
        initial_usdc = 50000
        initial_weth = 25
        initial_eth_price = 2000
        
        # Test 10x price increase
        il_amount_10x, il_pct_10x = self.analyzer.calculate_impermanent_loss(
            initial_usdc, initial_weth,
            initial_usdc * np.sqrt(10), initial_weth / np.sqrt(10),
            initial_eth_price, initial_eth_price * 10
        )
        
        # IL should be significant but not exceed theoretical maximum
        self.assertGreater(il_pct_10x, 10)  # Should be > 10%
        self.assertLess(il_pct_10x, 50)     # But < 50%
        
        # Test 90% price drop
        il_amount_drop, il_pct_drop = self.analyzer.calculate_impermanent_loss(
            initial_usdc, initial_weth,
            initial_usdc * np.sqrt(0.1), initial_weth / np.sqrt(0.1),
            initial_eth_price, initial_eth_price * 0.1
        )
        
        # Should also have significant IL
        self.assertGreater(il_pct_drop, 10)
    
    def test_price_recovery_scenario(self):
        """Test IL when price moves and then recovers."""
        initial_usdc = 50000
        initial_weth = 25
        initial_eth_price = 2000
        
        # Price returns to original
        il_amount, il_pct = self.analyzer.calculate_impermanent_loss(
            initial_usdc, initial_weth,
            initial_usdc, initial_weth,  # Same as initial
            initial_eth_price, initial_eth_price  # Same price
        )
        
        # Should have no IL if back to original state
        self.assertAlmostEqual(il_amount, 0, places=2)
        self.assertAlmostEqual(il_pct, 0, places=2)


class TestPositionCalculationScenarios(unittest.TestCase):
    """Test various position calculation scenarios."""
    
    def setUp(self):
        self.calculator = UniswapV3Calculator()
    
    def test_single_tick_position(self):
        """Test position spanning only one tick."""
        pool_state = PoolState(
            sqrt_price_x96=self.calculator.get_sqrt_ratio_at_tick(100),
            tick=100,
            liquidity=1000000000,
            fee=500,
            tick_spacing=1,
            token0="0xusdc",
            token1="0xweth",
            block_number=1000
        )
        
        # Position at exactly current tick
        position = self.calculator.calculate_position(
            pool_state,
            tick_lower=100,
            tick_upper=100,  # Same as lower
            amount0_desired=10000,
            amount1_desired=5
        )
        
        # Should still calculate valid liquidity
        self.assertGreaterEqual(position.liquidity, 0)
    
    def test_extremely_wide_position(self):
        """Test position with very wide range."""
        pool_state = PoolState(
            sqrt_price_x96=self.calculator.get_sqrt_ratio_at_tick(0),
            tick=0,
            liquidity=1000000000,
            fee=500,
            tick_spacing=60,
            token0="0xusdc",
            token1="0xweth",
            block_number=1000
        )
        
        # Extremely wide range
        position = self.calculator.calculate_position(
            pool_state,
            tick_lower=-100000,
            tick_upper=100000,
            amount0_desired=100000,
            amount1_desired=50
        )
        
        # Should handle extreme ranges
        self.assertGreater(position.liquidity, 0)
        self.assertGreater(position.amount0, 0)
        self.assertGreater(position.amount1, 0)
    
    def test_out_of_range_positions(self):
        """Test positions entirely outside current price."""
        current_tick = 200000
        pool_state = PoolState(
            sqrt_price_x96=self.calculator.get_sqrt_ratio_at_tick(current_tick),
            tick=current_tick,
            liquidity=1000000000,
            fee=500,
            tick_spacing=10,
            token0="0xusdc",
            token1="0xweth",
            block_number=1000
        )
        
        # Position below current price (all token0)
        position_below = self.calculator.calculate_position(
            pool_state,
            tick_lower=199000,
            tick_upper=199500,
            amount0_desired=10000,
            amount1_desired=5
        )
        
        # Should use only token0
        self.assertGreater(position_below.amount0, 0)
        self.assertEqual(position_below.amount1, 0)
        
        # Position above current price (all token1)
        position_above = self.calculator.calculate_position(
            pool_state,
            tick_lower=200500,
            tick_upper=201000,
            amount0_desired=10000,
            amount1_desired=5
        )
        
        # Should use only token1
        self.assertEqual(position_above.amount0, 0)
        self.assertGreater(position_above.amount1, 0)
    
    def test_unbalanced_token_amounts(self):
        """Test with very unbalanced initial token amounts."""
        pool_state = PoolState(
            sqrt_price_x96=self.calculator.get_sqrt_ratio_at_tick(200000),
            tick=200000,
            liquidity=1000000000,
            fee=500,
            tick_spacing=10,
            token0="0xusdc",
            token1="0xweth",
            block_number=1000
        )
        
        # Lots of USDC, very little WETH
        position1 = self.calculator.calculate_position(
            pool_state,
            tick_lower=199950,
            tick_upper=200050,
            amount0_desired=1000000,  # 1M USDC
            amount1_desired=0.1       # 0.1 WETH
        )
        
        # Lots of WETH, very little USDC
        position2 = self.calculator.calculate_position(
            pool_state,
            tick_lower=199950,
            tick_upper=200050,
            amount0_desired=100,      # 100 USDC
            amount1_desired=500       # 500 WETH
        )
        
        # Both should create valid positions
        self.assertGreater(position1.liquidity, 0)
        self.assertGreater(position2.liquidity, 0)


class TestEdgeCasesAndBoundaries(unittest.TestCase):
    """Test edge cases and boundary conditions."""
    
    def setUp(self):
        self.calculator = UniswapV3Calculator()
        self.analyzer = PositionAnalyzer(self.calculator)
    
    def test_tick_spacing_alignment_issues(self):
        """Test positions not aligned with tick spacing."""
        pool_state = PoolState(
            sqrt_price_x96=self.calculator.get_sqrt_ratio_at_tick(200000),
            tick=200000,
            liquidity=1000000000,
            fee=500,
            tick_spacing=60,  # Large tick spacing
            token0="0xusdc",
            token1="0xweth",
            block_number=1000
        )
        
        # Ticks not aligned with spacing
        # Should ideally be adjusted or raise error
        with self.assertRaises(Exception) as context:
            position = self.calculator.calculate_position(
                pool_state,
                tick_lower=199983,  # Not divisible by 60
                tick_upper=200017,  # Not divisible by 60
                amount0_desired=10000,
                amount1_desired=5
            )
    
    def test_zero_liquidity_pool(self):
        """Test calculations with zero liquidity pool."""
        pool_state = PoolState(
            sqrt_price_x96=self.calculator.get_sqrt_ratio_at_tick(0),
            tick=0,
            liquidity=0,  # Zero liquidity
            fee=500,
            tick_spacing=10,
            token0="0xusdc",
            token1="0xweth",
            block_number=1000
        )
        
        position = self.calculator.calculate_position(
            pool_state,
            tick_lower=-100,
            tick_upper=100,
            amount0_desired=10000,
            amount1_desired=5
        )
        
        # Should still calculate position
        self.assertGreaterEqual(position.liquidity, 0)
    
    def test_precision_limits(self):
        """Test calculations near precision limits."""
        # Very small amounts
        pool_state = PoolState(
            sqrt_price_x96=self.calculator.get_sqrt_ratio_at_tick(0),
            tick=0,
            liquidity=1000000000,
            fee=500,
            tick_spacing=1,
            token0="0xusdc",
            token1="0xweth",
            block_number=1000
        )
        
        position = self.calculator.calculate_position(
            pool_state,
            tick_lower=-10,
            tick_upper=10,
            amount0_desired=0.000001,  # 1 micro USDC
            amount1_desired=0.000000001  # 1 gwei
        )
        
        # Should handle small amounts without errors
        self.assertGreaterEqual(position.liquidity, 0)
    
    async def test_empty_swap_events(self):
        """Test fee calculation with no swaps."""
        position = Position(
            liquidity=1000000,
            tick_lower=100,
            tick_upper=200,
            amount0=10000,
            amount1=5
        )
        
        liquidity_distribution = {tick: 10000000 for tick in range(50, 250)}
        swap_events = []  # No swaps
        
        fee_by_tick = await self.analyzer.estimate_fees_from_swaps(
            position, swap_events, liquidity_distribution, 500
        )
        
        # Should return zero fees
        total_fees = sum(fees[0] + fees[1] for fees in fee_by_tick.values())
        self.assertEqual(total_fees, 0)


class TestRealWorldScenarios(unittest.TestCase):
    """Test scenarios based on real-world conditions."""
    
    def setUp(self):
        self.calculator = UniswapV3Calculator()
        self.analyzer = PositionAnalyzer(self.calculator)
    
    async def test_high_volatility_period(self):
        """Test during high volatility with many rapid swaps."""
        position = Position(
            liquidity=5000000,
            tick_lower=199000,
            tick_upper=201000,
            amount0=50000,
            amount1=25
        )
        
        liquidity_distribution = {tick: 50000000 for tick in range(198000, 202000)}
        
        # Simulate rapid price swings
        swap_events = []
        current_tick = 200000
        
        for i in range(100):  # 100 swaps
            # Oscillating price
            if i % 2 == 0:
                new_tick = current_tick + np.random.randint(50, 200)
                amount0 = -np.random.randint(1000, 10000) * 1000000
                amount1 = np.random.randint(500, 5000) * 1000000000000000
            else:
                new_tick = current_tick - np.random.randint(50, 200)
                amount0 = np.random.randint(1000, 10000) * 1000000
                amount1 = -np.random.randint(500, 5000) * 1000000000000000
            
            swap_events.append(SwapEvent(
                sender=f"0x{i}",
                recipient=f"0x{i+1000}",
                amount0=amount0,
                amount1=amount1,
                sqrt_price_x96=0,
                liquidity=0,
                tick=new_tick,
                block_number=i,
                transaction_hash=f"0x{i:064x}"
            ))
            current_tick = new_tick
        
        fee_by_tick = await self.analyzer.estimate_fees_from_swaps(
            position, swap_events, liquidity_distribution, 500
        )
        
        # Should accumulate significant fees from high volume
        total_fees_usdc = sum(fees[0] for fees in fee_by_tick.values())
        self.assertGreater(total_fees_usdc, 0)
    
    def test_stablecoin_pair_scenario(self):
        """Test with stablecoin pair (minimal price movement)."""
        # USDC/USDT pair with very tight range
        pool_state = PoolState(
            sqrt_price_x96=self.calculator.get_sqrt_ratio_at_tick(0),  # 1:1 price
            tick=0,
            liquidity=1000000000000,  # Very high liquidity
            fee=100,  # 0.01% fee tier
            tick_spacing=1,
            token0="0xusdc",
            token1="0xusdt",
            block_number=1000
        )
        
        # Very tight range around 1:1
        position = self.calculator.calculate_position(
            pool_state,
            tick_lower=-10,
            tick_upper=10,
            amount0_desired=1000000,  # 1M USDC
            amount1_desired=1000000   # 1M USDT
        )
        
        # Calculate IL with minimal price change
        il_amount, il_pct = self.analyzer.calculate_impermanent_loss(
            position.amount0, position.amount1,
            position.amount0 * 1.0001, position.amount1 * 0.9999,  # 0.01% price change
            1.0, 1.0001
        )
        
        # IL should be negligible for stablecoins
        self.assertLess(il_pct, 0.001)  # Less than 0.001%
    
    def test_new_pool_initialization(self):
        """Test position in newly initialized pool."""
        # New pool with minimal liquidity
        pool_state = PoolState(
            sqrt_price_x96=self.calculator.get_sqrt_ratio_at_tick(250000),
            tick=250000,
            liquidity=1000,  # Very low initial liquidity
            fee=3000,  # 0.3% fee
            tick_spacing=60,
            token0="0xnewtoken",
            token1="0xweth",
            block_number=1
        )
        
        # First liquidity provider
        position = self.calculator.calculate_position(
            pool_state,
            tick_lower=249940,
            tick_upper=250060,
            amount0_desired=10000,
            amount1_desired=5
        )
        
        # Should be able to provide liquidity
        self.assertGreater(position.liquidity, 0)
        
        # With minimal pool liquidity, position should dominate
        position_ratio = position.liquidity / (pool_state.liquidity + position.liquidity)
        self.assertGreater(position_ratio, 0.99)  # Should have >99% of pool


def run_scenario_tests():
    """Run all scenario tests with proper async handling."""
    import sys
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestLiquidityDistributionScenarios,
        TestFeeCalculationScenarios,
        TestImpermanentLossScenarios,
        TestPositionCalculationScenarios,
        TestEdgeCasesAndBoundaries,
        TestRealWorldScenarios
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_scenario_tests()
    sys.exit(0 if success else 1) 