#!/usr/bin/env python3
"""
Main entry point for Uniswap V3 liquidity analysis.
Analyzes a liquidity position on USDC/WETH pool from block 17618642 to 17618742.
"""

import os
import sys
import asyncio
from datetime import datetime
from decimal import Decimal
from dotenv import load_dotenv

from data_fetcher import DataFetcher
from uniswap_v3 import UniswapV3Calculator, Position
from analysis import PositionAnalyzer
from visualization import Visualizer

# Load environment variables
load_dotenv()

# Constants
POOL_ADDRESS = "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"  # USDC/WETH 0.05% pool
START_BLOCK = 17618642
END_BLOCK = 17618742
INITIAL_PORTFOLIO_VALUE = 100000  # USDC
TICK_LOWER = 200540
TICK_UPPER = 200560
USDC_DECIMALS = 6
WETH_DECIMALS = 18

# Token addresses
USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"


async def main():
    """Main execution function."""
    print("=" * 80)
    print("Uniswap V3 Liquidity Analysis - Tokka Labs Assignment")
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
        # Initialize components
        print("\n1. Initializing components...")
        data_fetcher = DataFetcher(rpc_url)
        calculator = UniswapV3Calculator()
        analyzer = PositionAnalyzer(calculator)
        visualizer = Visualizer()

        # Fetch pool data at start block
        print("\n2. Fetching pool data at start block...")
        pool_data_start = await data_fetcher.get_pool_state(
            POOL_ADDRESS, START_BLOCK
        )
        
        # Get token prices at start
        print("\n3. Fetching token prices...")
        eth_price_start = await data_fetcher.get_eth_price_in_usdc(START_BLOCK)
        print(f"   ETH price at start: ${eth_price_start:.2f}")

        # Calculate initial position
        print("\n4. Calculating initial position...")
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

        # Fetch liquidity distribution at start block
        print("\n6. Fetching liquidity distribution...")
        liquidity_distribution = await data_fetcher.get_liquidity_distribution(
            POOL_ADDRESS, START_BLOCK, TICK_LOWER - 10, TICK_UPPER + 10
        )

        # Fetch swap events between blocks
        print("\n7. Fetching swap events...")
        swap_events = await data_fetcher.get_swap_events(
            POOL_ADDRESS, START_BLOCK, END_BLOCK
        )
        print(f"   Found {len(swap_events)} swap events")

        # Fetch pool data at end block
        print("\n8. Fetching pool data at end block...")
        pool_data_end = await data_fetcher.get_pool_state(
            POOL_ADDRESS, END_BLOCK
        )
        eth_price_end = await data_fetcher.get_eth_price_in_usdc(END_BLOCK)
        print(f"   ETH price at end: ${eth_price_end:.2f}")

        # Analyze position
        print("\n9. Analyzing position...")
        analysis_results = analyzer.analyze_position(
            position,
            pool_data_start,
            pool_data_end,
            liquidity_distribution,
            swap_events,
            eth_price_start,
            eth_price_end
        )

        # Print results
        print("\n" + "=" * 80)
        print("ANALYSIS RESULTS")
        print("=" * 80)
        
        print("\nPosition at End Block:")
        print(f"  USDC balance: {analysis_results['final_usdc']:.2f}")
        print(f"  WETH balance: {analysis_results['final_weth']:.6f}")
        print(f"  Total value in USDC: ${analysis_results['final_value_usdc']:.2f}")
        
        print("\nImpermanent Loss:")
        print(f"  IL amount: ${analysis_results['impermanent_loss']:.2f}")
        print(f"  IL percentage: {analysis_results['impermanent_loss_pct']:.2f}%")
        
        print("\nEstimated Fees Earned:")
        print(f"  USDC fees: {analysis_results['fees_usdc']:.2f}")
        print(f"  WETH fees: {analysis_results['fees_weth']:.6f}")
        print(f"  Total fees in USDC: ${analysis_results['total_fees_usdc']:.2f}")
        
        print("\nPortfolio PnL:")
        print(f"  Initial value: ${INITIAL_PORTFOLIO_VALUE:.2f}")
        print(f"  Final value: ${analysis_results['final_total_value']:.2f}")
        print(f"  PnL: ${analysis_results['pnl']:.2f}")
        print(f"  PnL percentage: {analysis_results['pnl_pct']:.2f}%")

        # Generate visualizations
        print("\n10. Generating visualizations...")
        
        # Plot liquidity distribution
        visualizer.plot_liquidity_distribution(
            liquidity_distribution,
            position,
            TICK_LOWER,
            TICK_UPPER,
            "output/liquidity_distribution.png"
        )
        
        # Plot fee accumulation
        visualizer.plot_fee_accumulation(
            analysis_results['fee_by_tick'],
            TICK_LOWER - 10,
            TICK_UPPER + 10,
            "output/fee_accumulation.png"
        )
        
        # Generate summary report
        visualizer.generate_summary_report(
            analysis_results,
            position,
            pool_data_start,
            pool_data_end,
            "output/analysis_report.html"
        )
        
        print("\nAnalysis complete! Results saved to output/ directory.")
        print("  - liquidity_distribution.png")
        print("  - fee_accumulation.png")
        print("  - analysis_report.html")

    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 