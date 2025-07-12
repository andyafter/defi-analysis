#!/usr/bin/env python3
"""Simple entry point for backward compatibility."""

import asyncio
from pathlib import Path
from dotenv import load_dotenv
import os

from data_fetcher import DataFetcher
from uniswap_v3 import UniswapV3Calculator
from analysis import PositionAnalyzer
from visualization import Visualizer


async def main():
    """Run the analysis with hardcoded parameters."""
    # Load environment variables
    load_dotenv()
    
    # Configuration
    RPC_URL = os.getenv("ETH_RPC_URL")
    if not RPC_URL:
        raise ValueError("ETH_RPC_URL environment variable not set")
    
    # Default analysis parameters
    POOL_ADDRESS = "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"
    START_BLOCK = 17618642
    END_BLOCK = 17618742
    TICK_LOWER = 200540
    TICK_UPPER = 200560
    INITIAL_PORTFOLIO_VALUE_USDC = 100000
    
    # Initialize components
    data_fetcher = DataFetcher(RPC_URL)
    calculator = UniswapV3Calculator()
    analyzer = PositionAnalyzer(calculator)
    visualizer = Visualizer()
    
    try:
        print("Starting Uniswap V3 Liquidity Analysis...")
        print(f"Pool: {POOL_ADDRESS}")
        print(f"Block range: {START_BLOCK} - {END_BLOCK}")
        print(f"Tick range: {TICK_LOWER} - {TICK_UPPER}")
        print(f"Initial portfolio: ${INITIAL_PORTFOLIO_VALUE_USDC:,}")
        
        # Fetch pool states
        print("\nFetching pool data...")
        pool_data_start = await data_fetcher.get_pool_state(POOL_ADDRESS, START_BLOCK)
        pool_data_end = await data_fetcher.get_pool_state(POOL_ADDRESS, END_BLOCK)
        
        # Get ETH prices
        print("Getting ETH prices...")
        eth_price_start = await data_fetcher.get_eth_price_in_usdc(START_BLOCK)
        eth_price_end = await data_fetcher.get_eth_price_in_usdc(END_BLOCK)
        
        print(f"ETH price at start: ${eth_price_start:,.2f}")
        print(f"ETH price at end: ${eth_price_end:,.2f}")
        
        # Calculate initial amounts (50/50 split)
        initial_usdc = INITIAL_PORTFOLIO_VALUE_USDC * 0.5
        initial_weth = (INITIAL_PORTFOLIO_VALUE_USDC * 0.5) / eth_price_start
        
        print(f"\nInitial allocation:")
        print(f"  USDC: {initial_usdc:,.2f}")
        print(f"  WETH: {initial_weth:,.6f}")
        
        # Calculate position
        position = calculator.calculate_position(
            pool_data_start,
            TICK_LOWER,
            TICK_UPPER,
            initial_usdc,
            initial_weth
        )
        
        print(f"\nPosition created:")
        print(f"  Liquidity: {position.liquidity:,.0f}")
        
        # Fetch events
        print("\nFetching swap events...")
        swap_events = await data_fetcher.get_swap_events(
            POOL_ADDRESS,
            START_BLOCK,
            END_BLOCK
        )
        print(f"Found {len(swap_events)} swap events")
        
        # Get liquidity distribution
        print("\nFetching liquidity distribution...")
        liquidity_distribution = await data_fetcher.get_liquidity_distribution(
            POOL_ADDRESS,
            START_BLOCK,
            TICK_LOWER - 10,
            TICK_UPPER + 10
        )
        
        # Analyze position
        print("\nAnalyzing position...")
        results = analyzer.analyze_position(
            position,
            pool_data_start,
            pool_data_end,
            liquidity_distribution,
            swap_events,
            eth_price_start,
            eth_price_end
        )
        
        # Print results
        print("\n" + "=" * 60)
        print("ANALYSIS RESULTS")
        print("=" * 60)
        
        print("\nPosition at End Block:")
        print(f"  USDC balance: {results['final_usdc']:,.2f}")
        print(f"  WETH balance: {results['final_weth']:,.6f}")
        print(f"  Total value in USDC: ${results['final_value_usdc']:,.2f}")
        
        print("\nImpermanent Loss:")
        print(f"  IL amount: ${results['impermanent_loss']:,.2f}")
        print(f"  IL percentage: {results['impermanent_loss_pct']:.2f}%")
        
        print("\nEstimated Fees Earned:")
        print(f"  USDC fees: {results['fees_usdc']:,.2f}")
        print(f"  WETH fees: {results['fees_weth']:,.6f}")
        print(f"  Total fees in USDC: ${results['total_fees_usdc']:,.2f}")
        
        print("\nPortfolio PnL:")
        print(f"  Initial value: $100,000.00")
        print(f"  Final value: ${results['final_total_value']:,.2f}")
        print(f"  PnL: ${results['pnl']:,.2f}")
        print(f"  PnL percentage: {results['pnl_pct']:+.2f}%")
        
        # Generate visualizations
        print("\nGenerating visualizations...")
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        visualizer.plot_liquidity_distribution(
            liquidity_distribution,
            position,
            TICK_LOWER,
            TICK_UPPER,
            str(output_dir / "liquidity_distribution.png")
        )
        
        visualizer.plot_fee_accumulation(
            results['fee_by_tick'],
            TICK_LOWER - 10,
            TICK_UPPER + 10,
            str(output_dir / "fee_accumulation.png")
        )
        
        visualizer.generate_summary_report(
            results,
            position,
            pool_data_start,
            pool_data_end,
            str(output_dir / "analysis_report.html")
        )
        
        print(f"\nAnalysis complete! Results saved to {output_dir.absolute()}")
        
    except Exception as e:
        print(f"\nError: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 