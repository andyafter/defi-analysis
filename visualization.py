"""
Visualization module for generating plots and reports.
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from typing import Dict, Any, Tuple
import numpy as np
from datetime import datetime

from uniswap_v3 import Position
from data_fetcher import PoolState


class Visualizer:
    """Handles visualization of Uniswap V3 analysis results."""
    
    def __init__(self):
        # Set style
        try:
            plt.style.use('seaborn-v0_8-darkgrid')
        except:
            plt.style.use('seaborn-darkgrid')
        sns.set_palette("husl")
    
    def plot_liquidity_distribution(
        self,
        liquidity_distribution: Dict[int, int],
        position: Position,
        tick_lower: int,
        tick_upper: int,
        output_path: str
    ):
        """Plot liquidity distribution with position overlay."""
        # Prepare data
        tick_range = range(tick_lower - 10, tick_upper + 11)
        ticks = list(tick_range)
        
        # Get total liquidity for each tick
        total_liquidity = [liquidity_distribution.get(tick, 0) for tick in ticks]
        
        # Calculate position liquidity for visualization
        position_liquidity = []
        for tick in ticks:
            if position.tick_lower <= tick <= position.tick_upper:
                position_liquidity.append(position.liquidity)
            else:
                position_liquidity.append(0)
        
        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))
        
        # Plot total liquidity
        ax.bar(ticks, total_liquidity, alpha=0.7, label='Pool Total Liquidity', color='steelblue')
        
        # Plot position liquidity
        ax.bar(ticks, position_liquidity, alpha=0.8, label='Our Position Liquidity', color='orange')
        
        # Mark position range
        ax.axvline(x=position.tick_lower, color='red', linestyle='--', alpha=0.8, label='Position Range')
        ax.axvline(x=position.tick_upper, color='red', linestyle='--', alpha=0.8)
        
        # Labels and title
        ax.set_xlabel('Tick', fontsize=12)
        ax.set_ylabel('Liquidity', fontsize=12)
        ax.set_title('Liquidity Distribution at Start Block', fontsize=14, fontweight='bold')
        ax.legend(loc='upper right')
        
        # Format y-axis to show scientific notation
        ax.ticklabel_format(axis='y', style='scientific', scilimits=(0,0))
        
        # Set x-axis limits
        ax.set_xlim(tick_lower - 11, tick_upper + 11)
        
        # Grid
        ax.grid(True, alpha=0.3)
        
        # Save figure
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
    
    def plot_fee_accumulation(
        self,
        fee_by_tick: Dict[int, Tuple[float, float]],
        tick_lower: int,
        tick_upper: int,
        output_path: str
    ):
        """Plot fee accumulation by tick."""
        # Prepare data
        ticks = sorted(fee_by_tick.keys())
        usdc_fees = [fee_by_tick[tick][0] for tick in ticks]
        weth_fees = [fee_by_tick[tick][1] for tick in ticks]
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Plot USDC fees
        ax1.bar(ticks, usdc_fees, alpha=0.8, color='green', label='USDC Fees')
        ax1.set_xlabel('Tick', fontsize=12)
        ax1.set_ylabel('USDC Fees', fontsize=12)
        ax1.set_title('USDC Fee Accumulation by Tick', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(tick_lower - 1, tick_upper + 1)
        
        # Plot WETH fees
        ax2.bar(ticks, weth_fees, alpha=0.8, color='purple', label='WETH Fees')
        ax2.set_xlabel('Tick', fontsize=12)
        ax2.set_ylabel('WETH Fees', fontsize=12)
        ax2.set_title('WETH Fee Accumulation by Tick', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(tick_lower - 1, tick_upper + 1)
        
        # Save figure
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
    
    def generate_summary_report(
        self,
        analysis_results: Dict[str, Any],
        position: Position,
        pool_state_start: PoolState,
        pool_state_end: PoolState,
        output_path: str
    ):
        """Generate HTML summary report."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Uniswap V3 Position Analysis Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            max-width: 1000px;
            margin: 0 auto;
        }}
        h1, h2 {{
            color: #333;
        }}
        h1 {{
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        h2 {{
            margin-top: 30px;
            color: #007bff;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-top: 20px;
        }}
        th, td {{
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #007bff;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px 10px 0;
        }}
        .metric-label {{
            font-weight: bold;
            color: #666;
        }}
        .metric-value {{
            font-size: 1.2em;
            color: #333;
        }}
        .positive {{
            color: #28a745;
        }}
        .negative {{
            color: #dc3545;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .timestamp {{
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Uniswap V3 Liquidity Position Analysis</h1>
        <p class="timestamp">Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="section">
            <h2>Position Overview</h2>
            <div class="metric">
                <span class="metric-label">Pool:</span>
                <span class="metric-value">USDC/WETH 0.05%</span>
            </div>
            <div class="metric">
                <span class="metric-label">Analysis Period:</span>
                <span class="metric-value">Block {pool_state_start.block_number} → {pool_state_end.block_number}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Tick Range:</span>
                <span class="metric-value">{position.tick_lower} → {position.tick_upper}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Liquidity:</span>
                <span class="metric-value">{position.liquidity:,}</span>
            </div>
        </div>
        
        <div class="section">
            <h2>Initial Position</h2>
            <table>
                <tr>
                    <th>Asset</th>
                    <th>Amount in Position</th>
                    <th>Amount Unused</th>
                    <th>Total Available</th>
                </tr>
                <tr>
                    <td>USDC</td>
                    <td>{analysis_results['initial_usdc_in_position']:,.2f}</td>
                    <td>{analysis_results['unused_usdc']:,.2f}</td>
                    <td>50,000.00</td>
                </tr>
                <tr>
                    <td>WETH</td>
                    <td>{analysis_results['initial_weth_in_position']:,.6f}</td>
                    <td>{analysis_results['unused_weth']:,.6f}</td>
                    <td>{50000 / analysis_results['eth_price_start']:,.6f}</td>
                </tr>
            </table>
        </div>
        
        <div class="section">
            <h2>Final Position</h2>
            <table>
                <tr>
                    <th>Asset</th>
                    <th>Amount in Position</th>
                    <th>Fees Earned</th>
                    <th>Total</th>
                </tr>
                <tr>
                    <td>USDC</td>
                    <td>{analysis_results['final_usdc']:,.2f}</td>
                    <td>{analysis_results['fees_usdc']:,.2f}</td>
                    <td>{analysis_results['final_usdc'] + analysis_results['fees_usdc']:,.2f}</td>
                </tr>
                <tr>
                    <td>WETH</td>
                    <td>{analysis_results['final_weth']:,.6f}</td>
                    <td>{analysis_results['fees_weth']:,.6f}</td>
                    <td>{analysis_results['final_weth'] + analysis_results['fees_weth']:,.6f}</td>
                </tr>
            </table>
        </div>
        
        <div class="section">
            <h2>Price Information</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Start Block</th>
                    <th>End Block</th>
                    <th>Change</th>
                </tr>
                <tr>
                    <td>ETH Price (USDC)</td>
                    <td>${analysis_results['eth_price_start']:,.2f}</td>
                    <td>${analysis_results['eth_price_end']:,.2f}</td>
                    <td class="{'positive' if analysis_results['eth_price_end'] > analysis_results['eth_price_start'] else 'negative'}">
                        {((analysis_results['eth_price_end'] - analysis_results['eth_price_start']) / analysis_results['eth_price_start'] * 100):+.2f}%
                    </td>
                </tr>
                <tr>
                    <td>Pool Tick</td>
                    <td>{pool_state_start.tick}</td>
                    <td>{pool_state_end.tick}</td>
                    <td>{pool_state_end.tick - pool_state_start.tick:+d}</td>
                </tr>
            </table>
        </div>
        
        <div class="section">
            <h2>Performance Metrics</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Value (USDC)</th>
                    <th>Percentage</th>
                </tr>
                <tr>
                    <td>Impermanent Loss</td>
                    <td class="negative">${analysis_results['impermanent_loss']:,.2f}</td>
                    <td class="negative">{analysis_results['impermanent_loss_pct']:.2f}%</td>
                </tr>
                <tr>
                    <td>Total Fees Earned</td>
                    <td class="positive">${analysis_results['total_fees_usdc']:,.2f}</td>
                    <td class="positive">+{(analysis_results['total_fees_usdc'] / 100000 * 100):.2f}%</td>
                </tr>
                <tr>
                    <td><strong>Net PnL</strong></td>
                    <td class="{'positive' if analysis_results['pnl'] >= 0 else 'negative'}"><strong>${analysis_results['pnl']:,.2f}</strong></td>
                    <td class="{'positive' if analysis_results['pnl'] >= 0 else 'negative'}"><strong>{analysis_results['pnl_pct']:+.2f}%</strong></td>
                </tr>
            </table>
        </div>
        
        <div class="section">
            <h2>Portfolio Summary</h2>
            <table>
                <tr>
                    <th>Component</th>
                    <th>Value (USDC)</th>
                </tr>
                <tr>
                    <td>Initial Portfolio</td>
                    <td>$100,000.00</td>
                </tr>
                <tr>
                    <td>Position Value (end)</td>
                    <td>${analysis_results['final_value_usdc']:,.2f}</td>
                </tr>
                <tr>
                    <td>Fees Earned</td>
                    <td>${analysis_results['total_fees_usdc']:,.2f}</td>
                </tr>
                <tr>
                    <td>Unused Funds Value</td>
                    <td>${analysis_results['unused_value']:,.2f}</td>
                </tr>
                <tr>
                    <td><strong>Final Total Value</strong></td>
                    <td><strong>${analysis_results['final_total_value']:,.2f}</strong></td>
                </tr>
            </table>
        </div>
        
        <div class="section">
            <h2>Visualizations</h2>
            <p>Please refer to the generated plots:</p>
            <ul>
                <li><strong>liquidity_distribution.png</strong> - Shows the liquidity distribution across ticks</li>
                <li><strong>fee_accumulation.png</strong> - Shows fee accumulation by tick for both USDC and WETH</li>
            </ul>
        </div>
    </div>
</body>
</html>
"""
        
        with open(output_path, 'w') as f:
            f.write(html_content) 