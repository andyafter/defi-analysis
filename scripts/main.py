#!/usr/bin/env python3
"""
Main entry point for Uniswap V3 liquidity analysis.
Analyzes a liquidity position on USDC/WETH pool from block 17618642 to 17618742.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from datetime import datetime
from decimal import Decimal
from dotenv import load_dotenv
import time

from src.blockchain import DataFetcher
from src.uniswap import UniswapV3Calculator, Position
from src.analysis import PositionAnalyzer
from src.visualization import Visualizer

# Load environment variables
load_dotenv()

# Configuration
POOL_ADDRESS = "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"
START_BLOCK = 17618642
END_BLOCK = 17618742
INITIAL_PORTFOLIO_VALUE = 100000  # USDC
TICK_LOWER = 200540
TICK_UPPER = 200560


class PerformanceTracker:
    """Track and display performance metrics."""
    
    def __init__(self):
        self.metrics = {}
        self.start_time = time.time()
    
    def record(self, operation: str, duration: float, cache_hit: bool = None):
        """Record a performance metric."""
        self.metrics[operation] = {
            'duration': duration,
            'cache_hit': cache_hit
        }
    
    def print_summary(self):
        """Print performance summary."""
        total_time = time.time() - self.start_time
        
        print("\n" + "=" * 80)
        print("PERFORMANCE METRICS")
        print("=" * 80)
        
        for op, data in self.metrics.items():
            status = ""
            if data['cache_hit'] is not None:
                status = " (CACHED)" if data['cache_hit'] else " (FETCHED)"
            print(f"{op:<40} {data['duration']:>8.2f}s{status}")
        
        print("-" * 80)
        print(f"{'Total Execution Time:':<40} {total_time:>8.2f}s")
        
        # Calculate cache performance
        cache_ops = [op for op, data in self.metrics.items() if data['cache_hit'] is not None]
        if cache_ops:
            cache_hits = sum(1 for op in cache_ops if self.metrics[op]['cache_hit'])
            cache_rate = (cache_hits / len(cache_ops)) * 100
            print(f"{'Cache Hit Rate:':<40} {cache_rate:>7.1f}%")
        
        print("=" * 80)


async def main():
    """Main execution function."""
    perf = PerformanceTracker()
    
    print("=" * 80)
    print("Uniswap V3 Liquidity Analysis")
    print("=" * 80)
    print(f"Pool: USDC/WETH ({POOL_ADDRESS})")
    print(f"Analysis period: Block {START_BLOCK} to {END_BLOCK}")
    print(f"Initial portfolio: {INITIAL_PORTFOLIO_VALUE} USDC")
    print(f"Tick range: {TICK_LOWER} to {TICK_UPPER}")
    print("=" * 80)

    # Check for RPC URL
    rpc_url = os.getenv("ETH_RPC_URL")
    if not rpc_url:
        print("ERROR: Please set ETH_RPC_URL in your .env file")
        sys.exit(1)

    # Create output directory
    os.makedirs("output", exist_ok=True)

    try:
        # Initialize components with optimized settings
        print("\n1. Initializing components...")
        init_start = time.time()
        
        # Create cache for storing results
        from src.data.cache import FileCache
        cache = FileCache("cache", default_ttl=86400)  # 24 hour cache
        
        data_fetcher = DataFetcher(
            rpc_url=rpc_url,
            max_workers=20,              # Optimized thread pool size
            max_concurrent_requests=10,  # Rate limiting
            cache=cache                  # Enable caching
        )
        calculator = UniswapV3Calculator()
        analyzer = PositionAnalyzer(calculator, cache=cache)
        visualizer = Visualizer()
        
        perf.record("Component Initialization", time.time() - init_start)

        # Fetch pool data at start block
        print("\n2. Fetching pool data at start block...")
        start_time = time.time()
        pool_data_start = await data_fetcher.get_pool_state(
            POOL_ADDRESS, START_BLOCK
        )
        duration = time.time() - start_time
        perf.record("Pool State (Start Block)", duration, cache_hit=duration < 0.1)
        
        # Get token prices at start
        print("\n3. Fetching token prices...")
        start_time = time.time()
        eth_price_start = await data_fetcher.get_eth_price_in_usdc(START_BLOCK)
        print(f"   ETH price at start: ${eth_price_start:.2f}")
        perf.record("ETH Price Fetch (Start)", time.time() - start_time)

        # Calculate initial position
        print("\n4. Calculating initial position...")
        calc_start = time.time()
        initial_usdc = INITIAL_PORTFOLIO_VALUE / 2
        initial_weth = (INITIAL_PORTFOLIO_VALUE / 2) / eth_price_start
        print(f"   Initial USDC: {initial_usdc:.2f}")
        print(f"   Initial WETH: {initial_weth:.6f}")

        # Calculate liquidity to mint
        print("\n5. Calculating liquidity position...")
        position = calculator.calculate_position(
            pool_data_start,
            TICK_LOWER,
            TICK_UPPER,
            initial_usdc,
            initial_weth
        )
        
        print(f"   Liquidity minted: {position.liquidity}")
        print(f"   USDC used: {position.amount0:.2f}")
        print(f"   WETH used: {position.amount1:.6f}")
        print(f"   USDC remaining: {initial_usdc - position.amount0:.2f}")
        print(f"   WETH remaining: {initial_weth - position.amount1:.6f}")
        perf.record("Position Calculation", time.time() - calc_start)

        # Fetch liquidity distribution
        print("\n6. Fetching liquidity distribution...")
        start_time = time.time()
        liquidity_distribution = await data_fetcher.get_liquidity_distribution(
            POOL_ADDRESS, START_BLOCK, TICK_LOWER, TICK_UPPER
        )
        perf.record("Liquidity Distribution", time.time() - start_time)

        # Fetch swap events between blocks
        print("\n7. Fetching swap events...")
        start_time = time.time()
        swap_events = await data_fetcher.get_swap_events(
            POOL_ADDRESS, START_BLOCK, END_BLOCK, chunk_size=2000
        )
        duration = time.time() - start_time
        print(f"   Found {len(swap_events)} swap events")
        perf.record(f"Swap Events ({len(swap_events)} events)", duration, cache_hit=duration < 0.5)

        # Fetch pool data at end block
        print("\n8. Fetching pool data at end block...")
        start_time = time.time()
        pool_data_end = await data_fetcher.get_pool_state(
            POOL_ADDRESS, END_BLOCK
        )
        eth_price_end = await data_fetcher.get_eth_price_in_usdc(END_BLOCK)
        print(f"   ETH price at end: ${eth_price_end:.2f}")
        duration = time.time() - start_time
        perf.record("Pool State (End Block)", duration, cache_hit=duration < 0.1)

        # Analyze position
        print("\n9. Analyzing position...")
        analysis_start = time.time()
        analysis_results = await analyzer.analyze_position(
            position,
            pool_data_start,
            pool_data_end,
            liquidity_distribution,
            swap_events,
            eth_price_start,
            eth_price_end
        )
        perf.record("Position Analysis", time.time() - analysis_start)

        # Print results
        print("\n" + "=" * 80)
        print("ANALYSIS RESULTS")
        print("=" * 80)
        
        print("\nPosition at End Block:")
        print(f"  USDC balance: {analysis_results['final_usdc']:,.2f}")
        print(f"  WETH balance: {analysis_results['final_weth']:.6f}")
        print(f"  Total value in USDC: ${analysis_results['final_value_usdc']:,.2f}")
        
        print("\nImpermanent Loss:")
        print(f"  IL amount: ${analysis_results['impermanent_loss']:,.2f}")
        print(f"  IL percentage: {analysis_results['impermanent_loss_pct']:.2f}%")
        
        print("\nEstimated Fees Earned:")
        print(f"  USDC fees: {analysis_results['fees_usdc']:,.2f}")
        print(f"  WETH fees: {analysis_results['fees_weth']:.6f}")
        print(f"  Total fees in USDC: ${analysis_results['total_fees_usdc']:,.2f}")
        
        print("\nPortfolio PnL:")
        print(f"  Initial value: ${INITIAL_PORTFOLIO_VALUE:,.2f}")
        print(f"  Final value: ${analysis_results['final_total_value']:,.2f}")
        print(f"  PnL: ${analysis_results['pnl']:,.2f}")
        print(f"  PnL percentage: {analysis_results['pnl_pct']:+.2f}%")
        
        # Print performance summary
        perf.print_summary()
        
        # Save results
        print("\n10. Generating visualizations...")
        viz_start = time.time()
        
        # Generate plots
        visualizer.plot_liquidity_distribution(
            liquidity_distribution,
            position,
            TICK_LOWER,
            TICK_UPPER,
            pool_data_start.tick,  # Add current tick
            "output/liquidity_distribution.png"
        )
        
        if analysis_results['fee_by_tick']:
            visualizer.plot_fee_accumulation(
                analysis_results['fee_by_tick'],
                TICK_LOWER,
                TICK_UPPER,
                eth_price_end,  # Add ETH price for conversion
                "output/fee_accumulation.png"
            )
        
        # Generate position value chart
        visualizer.plot_position_value_chart(
            analysis_results,
            "output/position_value.png"
        )
        
        # Generate HTML report
        visualizer.generate_summary_report(
            analysis_results,
            position,
            pool_data_start,
            pool_data_end,
            "output/analysis_report.html"
        )
        
        perf.record("Visualization Generation", time.time() - viz_start)
        
        print("\n✅ Analysis complete! Results saved to output/")
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 