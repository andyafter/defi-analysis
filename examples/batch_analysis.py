#!/usr/bin/env python3
"""Example script for batch analysis of multiple positions."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import ConfigManager
from src.data.cache import FileCache
from data_fetcher import DataFetcher
from uniswap_v3 import UniswapV3Calculator
from analysis import PositionAnalyzer
from visualization import Visualizer


async def analyze_multiple_positions():
    """Analyze multiple positions across different pools and strategies."""
    
    # Load configuration
    config_manager = ConfigManager("config_examples.yaml")
    config = config_manager.load()
    
    # Initialize components
    cache = FileCache(config.cache.directory) if config.cache.enabled else None
    data_fetcher = DataFetcher(config.ethereum.rpc_url)
    calculator = UniswapV3Calculator()
    analyzer = PositionAnalyzer(calculator)
    visualizer = Visualizer()
    
    # Define combinations to analyze
    combinations = [
        ("usdc_weth_005", "default"),
        ("usdc_weth_005", "conservative"),
        ("usdc_weth_005", "aggressive"),
        ("usdc_weth_03", "default"),
        ("wbtc_weth", "default"),
    ]
    
    results_summary = []
    
    for pool_id, analysis_id in combinations:
        try:
            print(f"\nAnalyzing {pool_id} with {analysis_id} strategy...")
            
            # Get configurations
            pool_config = config_manager.get_pool_config(pool_id)
            analysis_config = config_manager.get_analysis_config(analysis_id)
            
            # Create output directory
            output_dir = Path(config.output.directory) / f"{pool_id}_{analysis_id}"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Fetch pool states
            pool_data_start = await data_fetcher.get_pool_state(
                pool_config.address, 
                analysis_config.start_block
            )
            
            pool_data_end = await data_fetcher.get_pool_state(
                pool_config.address,
                analysis_config.end_block
            )
            
            # Get prices (simplified for example - assumes USDC pricing)
            if pool_config.token0.symbol == "USDC":
                price_start = 1.0 / (pool_data_start.sqrtPriceX96 ** 2 / (2 ** 192))
                price_end = 1.0 / (pool_data_end.sqrtPriceX96 ** 2 / (2 ** 192))
            else:
                # Would need proper price conversion for non-USDC pools
                price_start = 1000.0  # Placeholder
                price_end = 1000.0
            
            # Calculate initial amounts
            initial_token0 = analysis_config.initial_portfolio_value * analysis_config.portfolio_split
            initial_token1 = (analysis_config.initial_portfolio_value * 
                            (1 - analysis_config.portfolio_split)) / price_start
            
            # Calculate position
            position = calculator.calculate_position(
                pool_data_start,
                analysis_config.position.tick_lower,
                analysis_config.position.tick_upper,
                initial_token0,
                initial_token1
            )
            
            # Fetch events
            swap_events = await data_fetcher.get_swap_events(
                pool_config.address,
                analysis_config.start_block,
                analysis_config.end_block
            )
            
            # Get liquidity distribution
            liquidity_distribution = await data_fetcher.get_liquidity_distribution(
                pool_config.address,
                analysis_config.start_block,
                analysis_config.position.tick_lower - 10,
                analysis_config.position.tick_upper + 10
            )
            
            # Analyze position
            results = analyzer.analyze_position(
                position,
                pool_data_start,
                pool_data_end,
                liquidity_distribution,
                swap_events,
                price_start,
                price_end
            )
            
            # Store summary
            results_summary.append({
                'pool': pool_config.name,
                'strategy': analysis_id,
                'initial_value': analysis_config.initial_portfolio_value,
                'final_value': results['final_total_value'],
                'pnl': results['pnl'],
                'pnl_pct': results['pnl_pct'],
                'impermanent_loss': results['impermanent_loss'],
                'fees_earned': results['total_fees_usdc']
            })
            
            # Generate visualizations
            if 'png' in config.output.formats:
                visualizer.plot_liquidity_distribution(
                    liquidity_distribution,
                    position,
                    analysis_config.position.tick_lower,
                    analysis_config.position.tick_upper,
                    str(output_dir / "liquidity_distribution.png")
                )
                
                visualizer.plot_fee_accumulation(
                    results['fee_by_tick'],
                    analysis_config.position.tick_lower - 10,
                    analysis_config.position.tick_upper + 10,
                    str(output_dir / "fee_accumulation.png")
                )
            
            if 'html' in config.output.formats:
                visualizer.generate_summary_report(
                    results,
                    position,
                    pool_data_start,
                    pool_data_end,
                    str(output_dir / "analysis_report.html")
                )
            
            print(f"  ✓ Completed: PnL {results['pnl_pct']:+.2f}%")
            
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            results_summary.append({
                'pool': pool_id,
                'strategy': analysis_id,
                'error': str(e)
            })
    
    # Print summary
    print("\n" + "=" * 80)
    print("BATCH ANALYSIS SUMMARY")
    print("=" * 80)
    
    for result in results_summary:
        if 'error' in result:
            print(f"\n{result['pool']} - {result['strategy']}: ERROR - {result['error']}")
        else:
            print(f"\n{result['pool']} - {result['strategy']}:")
            print(f"  Initial Value: ${result['initial_value']:,.2f}")
            print(f"  Final Value: ${result['final_value']:,.2f}")
            print(f"  PnL: ${result['pnl']:,.2f} ({result['pnl_pct']:+.2f}%)")
            print(f"  Impermanent Loss: ${result['impermanent_loss']:,.2f}")
            print(f"  Fees Earned: ${result['fees_earned']:,.2f}")
    
    # Generate comparison chart
    if len([r for r in results_summary if 'error' not in r]) > 0:
        _generate_comparison_chart(results_summary, config.output.directory)


def _generate_comparison_chart(results_summary, output_dir):
    """Generate a comparison chart of all results."""
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    # Filter out errors
    valid_results = [r for r in results_summary if 'error' not in r]
    
    # Create comparison plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # PnL comparison
    labels = [f"{r['pool']}\n{r['strategy']}" for r in valid_results]
    pnl_pcts = [r['pnl_pct'] for r in valid_results]
    
    ax1.bar(labels, pnl_pcts, color=['green' if p > 0 else 'red' for p in pnl_pcts])
    ax1.set_title('PnL Comparison (%)')
    ax1.set_ylabel('PnL %')
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax1.tick_params(axis='x', rotation=45)
    
    # Fees vs IL comparison
    fees = [r['fees_earned'] for r in valid_results]
    il = [r['impermanent_loss'] for r in valid_results]
    
    x = range(len(valid_results))
    width = 0.35
    
    ax2.bar([i - width/2 for i in x], fees, width, label='Fees Earned', color='green')
    ax2.bar([i + width/2 for i in x], il, width, label='Impermanent Loss', color='red')
    ax2.set_xlabel('Position')
    ax2.set_ylabel('USD')
    ax2.set_title('Fees Earned vs Impermanent Loss')
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=45)
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig(Path(output_dir) / 'batch_comparison.png', dpi=300, bbox_inches='tight')
    print(f"\nComparison chart saved to {output_dir}/batch_comparison.png")


if __name__ == "__main__":
    asyncio.run(analyze_multiple_positions()) 