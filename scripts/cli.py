#!/usr/bin/env python3
"""Command-line interface for Uniswap V3 analysis."""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
import asyncio
import logging
from pathlib import Path
from typing import Optional

from src.config import ConfigManager
from src.data.cache import FileCache
from src.blockchain import DataFetcher
from src.uniswap import UniswapV3Calculator, Position
from src.analysis import PositionAnalyzer  
from src.visualization import Visualizer


@click.group()
@click.option('--config', '-c', default='config.yaml', help='Path to configuration file')
@click.option('--log-level', '-l', default='INFO', 
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              help='Logging level')
@click.pass_context
def cli(ctx, config: str, log_level: str):
    """Uniswap V3 Liquidity Analysis Tool."""
    # Setup context
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config
    ctx.obj['log_level'] = log_level
    
    # Load configuration
    config_manager = ConfigManager(config)
    ctx.obj['config_manager'] = config_manager
    
    # Setup basic logging (will be overridden by config)
    logging.basicConfig(level=getattr(logging, log_level))


@cli.command()
@click.option('--pool', '-p', default='usdc_weth', help='Pool identifier from config')
@click.option('--analysis', '-a', default='default', help='Analysis profile from config')
@click.option('--cache/--no-cache', default=True, help='Enable/disable caching')
@click.option('--output-dir', '-o', help='Override output directory')
@click.pass_context
def analyze(ctx, pool: str, analysis: str, cache: bool, output_dir: Optional[str]):
    """Run liquidity analysis for a position."""
    config_manager = ctx.obj['config_manager']
    config = config_manager.load()
    
    # Get configurations
    pool_config = config_manager.get_pool_config(pool)
    analysis_config = config_manager.get_analysis_config(analysis)
    
    # Override output directory if specified
    if output_dir:
        config.output.directory = output_dir
    
    # Run analysis
    asyncio.run(_run_analysis(
        config=config,
        pool_config=pool_config,
        analysis_config=analysis_config,
        use_cache=cache
    ))


@cli.command()
@click.option('--start-block', '-s', type=int, required=True, help='Start block number')
@click.option('--end-block', '-e', type=int, required=True, help='End block number')
@click.option('--pool-address', '-p', required=True, help='Pool contract address')
@click.option('--tick-lower', type=int, required=True, help='Lower tick bound')
@click.option('--tick-upper', type=int, required=True, help='Upper tick bound')
@click.option('--initial-value', type=float, default=100000, help='Initial portfolio value in USDC')
@click.option('--split', type=float, default=0.5, help='Portfolio split ratio (0-1)')
@click.pass_context
def analyze_custom(ctx, start_block: int, end_block: int, pool_address: str,
                  tick_lower: int, tick_upper: int, initial_value: float, split: float):
    """Run analysis with custom parameters."""
    config_manager = ctx.obj['config_manager']
    config = config_manager.load()
    
    # Create custom configs
    from src.config.config_manager import (
        PoolConfig, TokenConfig, AnalysisConfig, PositionConfig
    )
    
    # Create minimal pool config (will fetch details from chain)
    pool_config = PoolConfig(
        address=pool_address,
        name="Custom Pool",
        fee_tier=500,  # Default to 0.05%
        token0=TokenConfig(address="", symbol="TOKEN0", decimals=18),
        token1=TokenConfig(address="", symbol="TOKEN1", decimals=18)
    )
    
    # Create analysis config
    analysis_config = AnalysisConfig(
        start_block=start_block,
        end_block=end_block,
        initial_portfolio_value=initial_value,
        portfolio_split=split,
        position=PositionConfig(tick_lower=tick_lower, tick_upper=tick_upper)
    )
    
    # Run analysis
    asyncio.run(_run_analysis(
        config=config,
        pool_config=pool_config,
        analysis_config=analysis_config,
        use_cache=True
    ))


@cli.command()
@click.option('--pool', '-p', help='Pool identifier to get info for')
@click.option('--block', '-b', type=int, help='Block number (default: latest)')
@click.pass_context
def pool_info(ctx, pool: Optional[str], block: Optional[int]):
    """Get information about a pool."""
    config_manager = ctx.obj['config_manager']
    config = config_manager.load()
    
    if pool:
        pool_config = config_manager.get_pool_config(pool)
        asyncio.run(_show_pool_info(config, pool_config, block))
    else:
        # Show all configured pools
        click.echo("Configured pools:")
        for pool_id, pool_config in config.pools.items():
            click.echo(f"  - {pool_id}: {pool_config.name} ({pool_config.address})")


@cli.command()
@click.pass_context
def clear_cache(ctx):
    """Clear all cached data."""
    config_manager = ctx.obj['config_manager']
    config = config_manager.load()
    
    if config.cache.enabled:
        cache = FileCache(config.cache.directory)
        asyncio.run(cache.clear())
        click.echo("Cache cleared successfully")
    else:
        click.echo("Cache is disabled in configuration")


@cli.command()
@click.pass_context
def validate_config(ctx):
    """Validate configuration file."""
    config_manager = ctx.obj['config_manager']
    
    try:
        config = config_manager.load()
        click.echo("✅ Configuration is valid")
        
        # Show summary
        click.echo(f"\nConfiguration summary:")
        click.echo(f"  Pools: {len(config.pools)}")
        click.echo(f"  Analysis profiles: {len(config.analysis)}")
        click.echo(f"  Cache: {'enabled' if config.cache.enabled else 'disabled'}")
        click.echo(f"  Output directory: {config.output.directory}")
        
    except Exception as e:
        click.echo(f"❌ Configuration error: {e}", err=True)
        ctx.exit(1)


async def _run_analysis(config, pool_config, analysis_config, use_cache: bool):
    """Run the actual analysis."""
    logger = logging.getLogger(__name__)
    import time
    
    class PerformanceLogger:
        def __init__(self):
            self.start_time = time.time()
            
        def log(self, operation: str, duration: float, cached: bool = None):
            status = ""
            if cached is not None:
                status = " (CACHED)" if cached else " (FETCHED)"
            logger.info(f"Performance: {operation} - {duration:.2f}s{status}")
    
    perf = PerformanceLogger()
    
    try:
        # Initialize components with optimized settings
        init_start = time.time()
        cache = FileCache(config.cache.directory) if use_cache and config.cache.enabled else None
        
        # Create optimized data fetcher with performance settings
        data_fetcher = DataFetcher(
            rpc_url=config.ethereum.rpc_url,
            max_workers=config.performance.max_workers,
            max_concurrent_requests=config.performance.max_concurrent_requests,
            cache=cache
        )
        
        calculator = UniswapV3Calculator()
        analyzer = PositionAnalyzer(calculator, cache=cache)
        visualizer = Visualizer()
        
        # Create output directory
        output_dir = Path(config.output.directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Starting analysis for pool {pool_config.address}")
        logger.info(f"Block range: {analysis_config.start_block} - {analysis_config.end_block}")
        logger.info(f"Performance settings: {config.performance.max_workers} workers, {config.performance.max_concurrent_requests} concurrent requests")
        
        # Fetch pool data
        pool_data_start = await data_fetcher.get_pool_state(
            pool_config.address, 
            analysis_config.start_block
        )
        
        pool_data_end = await data_fetcher.get_pool_state(
            pool_config.address,
            analysis_config.end_block
        )
        
        # Get prices
        eth_price_start = await data_fetcher.get_eth_price_in_usdc(
            analysis_config.start_block
        )
        eth_price_end = await data_fetcher.get_eth_price_in_usdc(
            analysis_config.end_block
        )
        
        # Calculate initial amounts
        initial_token0 = analysis_config.initial_portfolio_value * analysis_config.portfolio_split
        initial_token1 = (analysis_config.initial_portfolio_value * (1 - analysis_config.portfolio_split)) / eth_price_start
        
        # Calculate position
        position = calculator.calculate_position(
            pool_data_start,
            analysis_config.position.tick_lower,
            analysis_config.position.tick_upper,
            initial_token0,
            initial_token1
        )
        
        logger.info(f"Position created with liquidity: {position.liquidity}")
        
        # Fetch events and liquidity distribution with optimized chunk size
        swap_events = await data_fetcher.get_swap_events(
            pool_config.address,
            analysis_config.start_block,
            analysis_config.end_block,
            chunk_size=config.performance.chunk_size
        )
        
        liquidity_distribution = await data_fetcher.get_liquidity_distribution(
            pool_config.address,
            analysis_config.start_block,
            analysis_config.position.tick_lower - 10,
            analysis_config.position.tick_upper + 10
        )
        
        # Analyze position
        results = await analyzer.analyze_position(
            position,
            pool_data_start,
            pool_data_end,
            liquidity_distribution,
            swap_events,
            eth_price_start,
            eth_price_end
        )
        
        # Print results
        _print_results(results)
        
        # Generate visualizations
        if 'png' in config.output.formats:
            visualizer.plot_liquidity_distribution(
                liquidity_distribution,
                position,
                analysis_config.position.tick_lower,
                analysis_config.position.tick_upper,
                pool_data_start.tick,  # Add current tick
                str(output_dir / "liquidity_distribution.png")
            )
            
            visualizer.plot_fee_accumulation(
                results['fee_by_tick'],
                analysis_config.position.tick_lower - 10,
                analysis_config.position.tick_upper + 10,
                eth_price_end,  # Add ETH price for conversion
                str(output_dir / "fee_accumulation.png")
            )
            
            # Generate position value chart
            visualizer.plot_position_value_chart(
                results,
                str(output_dir / "position_value.png")
            )
        
        if 'html' in config.output.formats:
            visualizer.generate_summary_report(
                results,
                position,
                pool_data_start,
                pool_data_end,
                str(output_dir / "analysis_report.html")
            )
        
        logger.info(f"Analysis complete. Results saved to {output_dir}")
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise


async def _show_pool_info(config, pool_config, block_number: Optional[int]):
    """Show pool information."""
    # Create cache if enabled
    cache = FileCache(config.cache.directory) if config.cache.enabled else None
    
    data_fetcher = DataFetcher(
        rpc_url=config.ethereum.rpc_url,
        max_workers=config.performance.max_workers,
        max_concurrent_requests=config.performance.max_concurrent_requests,
        cache=cache
    )
    
    # Use latest block if not specified
    if block_number is None:
        # This is a simplified approach - in real implementation, 
        # you'd get the latest block number
        block_number = "latest"
    
    # Fetch pool state
    pool_state = await data_fetcher.get_pool_state(pool_config.address, block_number)
    
    click.echo(f"\nPool: {pool_config.name}")
    click.echo(f"Address: {pool_config.address}")
    click.echo(f"Token0: {pool_config.token0.symbol} ({pool_config.token0.address})")
    click.echo(f"Token1: {pool_config.token1.symbol} ({pool_config.token1.address})")
    click.echo(f"Fee Tier: {pool_config.fee_tier / 10000}%")
    click.echo(f"\nCurrent State (Block {pool_state.block_number}):")
    click.echo(f"  Current Tick: {pool_state.tick}")
    click.echo(f"  Liquidity: {pool_state.liquidity}")


def _print_results(results: dict):
    """Print analysis results."""
    click.echo("\n" + "=" * 60)
    click.echo("ANALYSIS RESULTS")
    click.echo("=" * 60)
    
    click.echo("\nPosition at End Block:")
    click.echo(f"  USDC balance: {results['final_usdc']:,.2f}")
    click.echo(f"  WETH balance: {results['final_weth']:,.6f}")
    click.echo(f"  Total value in USDC: ${results['final_value_usdc']:,.2f}")
    
    click.echo("\nImpermanent Loss:")
    click.echo(f"  IL amount: ${results['impermanent_loss']:,.2f}")
    click.echo(f"  IL percentage: {results['impermanent_loss_pct']:.2f}%")
    
    click.echo("\nEstimated Fees Earned:")
    click.echo(f"  USDC fees: {results['fees_usdc']:,.2f}")
    click.echo(f"  WETH fees: {results['fees_weth']:,.6f}")
    click.echo(f"  Total fees in USDC: ${results['total_fees_usdc']:,.2f}")
    
    click.echo("\nPortfolio PnL:")
    click.echo(f"  Initial value: $100,000.00")
    click.echo(f"  Final value: ${results['final_total_value']:,.2f}")
    click.echo(f"  PnL: ${results['pnl']:,.2f}")
    click.echo(f"  PnL percentage: {results['pnl_pct']:+.2f}%")


if __name__ == '__main__':
    cli() 