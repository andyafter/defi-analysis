"""
Visualization module for generating plots and reports.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import seaborn as sns
import pandas as pd
from typing import Dict, Any, Tuple, List
import numpy as np
from datetime import datetime
import base64
from io import BytesIO

from src.uniswap import Position
from src.blockchain import PoolState


class Visualizer:
    """Handles visualization of Uniswap V3 analysis results."""
    
    def __init__(self):
        # Set professional style
        plt.style.use('seaborn-v0_8-whitegrid')
        
        # Define color palette
        self.colors = {
            'primary': '#1f77b4',      # Blue
            'secondary': '#ff7f0e',    # Orange
            'success': '#2ca02c',      # Green
            'danger': '#d62728',       # Red
            'warning': '#ff9800',      # Amber
            'info': '#17a2b8',         # Cyan
            'dark': '#2c3e50',         # Dark blue
            'light': '#ecf0f1',        # Light gray
            'position': '#9467bd',     # Purple
            'pool': '#8c564b',        # Brown
        }
        
        # Set font properties
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
        plt.rcParams['font.size'] = 10
    
    def plot_liquidity_distribution(
        self,
        liquidity_distribution: Dict[int, int],
        position: Position,
        tick_lower: int,
        tick_upper: int,
        current_tick: int,
        output_path: str
    ):
        """Plot enhanced liquidity distribution with position overlay."""
        # Prepare data
        ticks = np.arange(tick_lower - 20, tick_upper + 21)
        total_liquidity = np.array([liquidity_distribution.get(tick, 0) for tick in ticks])
        position_liquidity = np.where(
            (ticks >= position.tick_lower) & (ticks <= position.tick_upper),
            position.liquidity,
            0
        )
        
        # Create figure with custom layout
        fig = plt.figure(figsize=(14, 8))
        gs = GridSpec(3, 1, height_ratios=[2.5, 0.5, 0.5], hspace=0.3)
        
        # Main liquidity plot
        ax_main = fig.add_subplot(gs[0])
        
        # Create gradient effect for pool liquidity
        bars_pool = ax_main.bar(ticks, total_liquidity, alpha=0.6, 
                                label='Pool Liquidity', color=self.colors['pool'],
                                edgecolor='none')
        
        # Highlight our position
        bars_position = ax_main.bar(ticks, position_liquidity, alpha=0.8, 
                                   label='Our Position', color=self.colors['position'],
                                   edgecolor='none')
        
        # Mark position boundaries
        ax_main.axvline(x=position.tick_lower, color=self.colors['danger'], 
                       linestyle='--', linewidth=2, alpha=0.8)
        ax_main.axvline(x=position.tick_upper, color=self.colors['danger'], 
                       linestyle='--', linewidth=2, alpha=0.8)
        
        # Mark current tick
        ax_main.axvline(x=current_tick, color=self.colors['success'], 
                       linestyle='-', linewidth=3, alpha=0.9, label='Current Price')
        
        # Add shaded region for position range
        ax_main.axvspan(position.tick_lower, position.tick_upper, 
                       alpha=0.1, color=self.colors['position'])
        
        # Styling
        ax_main.set_xlabel('Tick', fontsize=12, fontweight='bold')
        ax_main.set_ylabel('Liquidity', fontsize=12, fontweight='bold')
        ax_main.set_title('Liquidity Distribution and Position Analysis', 
                         fontsize=16, fontweight='bold', pad=20)
        ax_main.ticklabel_format(axis='y', style='scientific', scilimits=(0,0))
        ax_main.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax_main.set_xlim(tick_lower - 25, tick_upper + 25)
        
        # Add legend with custom styling
        legend = ax_main.legend(loc='upper right', frameon=True, fancybox=True, 
                               shadow=True, fontsize=11)
        legend.get_frame().set_facecolor('white')
        legend.get_frame().set_alpha(0.9)
        
        # Add liquidity share info
        ax_info = fig.add_subplot(gs[1])
        ax_info.axis('off')
        
        if current_tick >= position.tick_lower and current_tick <= position.tick_upper:
            current_liquidity = liquidity_distribution.get(current_tick, 1)
            share_pct = (position.liquidity / current_liquidity * 100) if current_liquidity > 0 else 0
            info_text = f"Position Active | Our Share at Current Tick: {share_pct:.2f}%"
            info_color = self.colors['success']
        else:
            info_text = "Position Inactive | Current price outside position range"
            info_color = self.colors['warning']
        
        ax_info.text(0.5, 0.5, info_text, ha='center', va='center', 
                    fontsize=12, fontweight='bold', color=info_color,
                    bbox=dict(boxstyle="round,pad=0.5", facecolor=self.colors['light'], 
                             edgecolor=info_color, linewidth=2))
        
        # Add metrics bar
        ax_metrics = fig.add_subplot(gs[2])
        ax_metrics.axis('off')
        
        total_position_liquidity = position.liquidity * (position.tick_upper - position.tick_lower + 1)
        total_pool_liquidity = sum(total_liquidity)
        overall_share = (total_position_liquidity / total_pool_liquidity * 100) if total_pool_liquidity > 0 else 0
        
        metrics_text = (f"Position Range: {position.tick_upper - position.tick_lower + 1} ticks | "
                       f"Position Liquidity: {position.liquidity:,.0f} | "
                       f"Average Pool Share: {overall_share:.3f}%")
        
        ax_metrics.text(0.5, 0.5, metrics_text, ha='center', va='center', 
                       fontsize=10, color=self.colors['dark'])
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
    
    def plot_fee_accumulation(
        self,
        fee_by_tick: Dict[int, Tuple[float, float]],
        tick_lower: int,
        tick_upper: int,
        eth_price: float,
        output_path: str
    ):
        """Plot enhanced fee accumulation with multiple views."""
        # Prepare data
        ticks = np.array(sorted(fee_by_tick.keys()))
        fees_array = np.array([fee_by_tick[tick] for tick in ticks])
        usdc_fees = fees_array[:, 0]
        weth_fees = fees_array[:, 1]
        
        # Convert WETH fees to USDC for total view
        weth_fees_in_usdc = weth_fees * eth_price
        total_fees_usdc = usdc_fees + weth_fees_in_usdc
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle('Fee Analysis Dashboard', fontsize=18, fontweight='bold', y=0.98)
        
        # 1. Total fees by tick (top left)
        ax1 = axes[0, 0]
        bars = ax1.bar(ticks, total_fees_usdc, color=self.colors['success'], 
                       alpha=0.8, edgecolor='none')
        
        # Highlight highest earning ticks
        max_fee_idx = np.argmax(total_fees_usdc)
        bars[max_fee_idx].set_color(self.colors['warning'])
        bars[max_fee_idx].set_edgecolor(self.colors['dark'])
        bars[max_fee_idx].set_linewidth(2)
        
        ax1.set_title('Total Fee Distribution (USDC)', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Tick')
        ax1.set_ylabel('Total Fees (USDC)')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(tick_lower - 1, tick_upper + 1)
        
        # Add annotation for highest earning tick
        ax1.annotate(f'Peak: ${total_fees_usdc[max_fee_idx]:,.2f}',
                    xy=(ticks[max_fee_idx], total_fees_usdc[max_fee_idx]),
                    xytext=(10, 10), textcoords='offset points',
                    ha='left', fontsize=10,
                    bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        
        # 2. Cumulative fees (top right)
        ax2 = axes[0, 1]
        cumulative_fees = np.cumsum(total_fees_usdc)
        ax2.fill_between(ticks, cumulative_fees, alpha=0.3, color=self.colors['info'])
        ax2.plot(ticks, cumulative_fees, color=self.colors['info'], linewidth=3)
        ax2.set_title('Cumulative Fee Earnings', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Tick')
        ax2.set_ylabel('Cumulative Fees (USDC)')
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(tick_lower - 1, tick_upper + 1)
        
        # Add total annotation
        ax2.text(0.95, 0.95, f'Total: ${cumulative_fees[-1]:,.2f}',
                transform=ax2.transAxes, ha='right', va='top',
                fontsize=12, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8))
        
        # 3. USDC vs WETH fees (bottom left)
        ax3 = axes[1, 0]
        x = np.arange(len(ticks))
        width = 0.35
        
        bars1 = ax3.bar(x - width/2, usdc_fees, width, label='USDC Fees',
                       color=self.colors['primary'], alpha=0.8)
        bars2 = ax3.bar(x + width/2, weth_fees_in_usdc, width, label='WETH Fees (in USDC)',
                       color=self.colors['secondary'], alpha=0.8)
        
        ax3.set_title('Fee Breakdown by Asset', fontsize=14, fontweight='bold')
        ax3.set_xlabel('Tick Index')
        ax3.set_ylabel('Fees (USDC)')
        ax3.set_xticks(x[::max(1, len(x)//10)])  # Show every 10th tick
        ax3.set_xticklabels(ticks[::max(1, len(x)//10)])
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. Fee composition pie chart (bottom right)
        ax4 = axes[1, 1]
        total_usdc = np.sum(usdc_fees)
        total_weth_usdc = np.sum(weth_fees_in_usdc)
        
        sizes = [total_usdc, total_weth_usdc]
        labels = [f'USDC\n${total_usdc:,.2f}', f'WETH\n${total_weth_usdc:,.2f}']
        colors = [self.colors['primary'], self.colors['secondary']]
        
        wedges, texts, autotexts = ax4.pie(sizes, labels=labels, colors=colors,
                                           autopct='%1.1f%%', startangle=90,
                                           explode=(0.05, 0.05))
        
        for text in texts:
            text.set_fontsize(12)
            text.set_fontweight('bold')
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(11)
            autotext.set_fontweight('bold')
        
        ax4.set_title('Fee Composition', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
    
    def plot_position_value_chart(
        self,
        analysis_results: Dict[str, Any],
        output_path: str
    ):
        """Create a comprehensive position value chart."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # Left chart: Value breakdown
        categories = ['Initial\nPortfolio', 'Final\nPosition', 'Fees\nEarned', 'Unused\nFunds', 'Final\nTotal']
        values = [
            100000,
            analysis_results['final_value_usdc'],
            analysis_results['total_fees_usdc'],
            analysis_results['unused_value'],
            analysis_results['final_total_value']
        ]
        
        colors_list = [self.colors['dark'], self.colors['primary'], 
                      self.colors['success'], self.colors['info'], self.colors['warning']]
        
        bars = ax1.bar(categories, values, color=colors_list, alpha=0.8, edgecolor='white', linewidth=2)
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1000,
                    f'${value:,.0f}', ha='center', va='bottom', fontweight='bold')
        
        ax1.set_title('Portfolio Value Breakdown', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Value (USDC)', fontsize=12)
        ax1.grid(True, alpha=0.3, axis='y')
        ax1.set_ylim(0, max(values) * 1.15)
        
        # Add reference line for initial value
        ax1.axhline(y=100000, color=self.colors['danger'], linestyle='--', 
                   linewidth=2, alpha=0.7, label='Initial Value')
        ax1.legend()
        
        # Right chart: Performance metrics
        metrics = ['Impermanent\nLoss', 'Fees\nEarned', 'Net\nP&L']
        metric_values = [
            -abs(analysis_results['impermanent_loss']),
            analysis_results['total_fees_usdc'],
            analysis_results['pnl']
        ]
        
        # Color based on positive/negative
        metric_colors = [self.colors['danger'], self.colors['success'], 
                        self.colors['success'] if analysis_results['pnl'] >= 0 else self.colors['danger']]
        
        bars2 = ax2.bar(metrics, metric_values, color=metric_colors, alpha=0.8, 
                       edgecolor='white', linewidth=2)
        
        # Add value and percentage labels
        for bar, value, metric in zip(bars2, metric_values, metrics):
            height = bar.get_height()
            pct = (value / 100000) * 100
            label_y = height + 500 if height > 0 else height - 1500
            
            ax2.text(bar.get_x() + bar.get_width()/2., label_y,
                    f'${abs(value):,.0f}\n({pct:+.2f}%)', 
                    ha='center', va='bottom' if height > 0 else 'top', 
                    fontweight='bold', fontsize=10)
        
        ax2.set_title('Performance Metrics', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Value (USDC)', fontsize=12)
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.axhline(y=0, color='black', linewidth=1)
        
        # Set y-axis to show both positive and negative
        y_max = max(abs(min(metric_values)), max(metric_values)) * 1.3
        ax2.set_ylim(-y_max, y_max)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
    
    def _fig_to_base64(self, fig):
        """Convert matplotlib figure to base64 string."""
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        return img_base64
    
    def generate_summary_report(
        self,
        analysis_results: Dict[str, Any],
        position: Position,
        pool_state_start: PoolState,
        pool_state_end: PoolState,
        output_path: str
    ):
        """Generate enhanced HTML summary report with embedded visualizations."""
        
        # Create mini charts for the report
        fig_summary = self._create_summary_chart(analysis_results)
        summary_chart_b64 = self._fig_to_base64(fig_summary)
        plt.close(fig_summary)
        
        # Determine performance class
        pnl_class = 'positive' if analysis_results['pnl'] >= 0 else 'negative'
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Uniswap V3 Position Analysis Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        
        .header .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .timestamp {{
            margin-top: 15px;
            font-size: 0.9em;
            opacity: 0.8;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .section {{
            margin-bottom: 40px;
        }}
        
        .section h2 {{
            color: #2c3e50;
            font-size: 1.8em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #3498db;
            display: inline-block;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            border: 1px solid #e9ecef;
        }}
        
        .metric-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        
        .metric-label {{
            font-size: 0.9em;
            color: #6c757d;
            margin-bottom: 5px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .metric-value {{
            font-size: 1.8em;
            font-weight: 700;
            color: #2c3e50;
        }}
        
        .positive {{
            color: #27ae60 !important;
        }}
        
        .negative {{
            color: #e74c3c !important;
        }}
        
        .warning {{
            color: #f39c12 !important;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 5px 20px rgba(0,0,0,0.05);
        }}
        
        th {{
            background: #3498db;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.9em;
            letter-spacing: 0.5px;
        }}
        
        td {{
            padding: 15px;
            border-bottom: 1px solid #ecf0f1;
        }}
        
        tr:hover {{
            background: #f8f9fa;
        }}
        
        tr:last-child td {{
            border-bottom: none;
        }}
        
        .chart-container {{
            margin: 30px 0;
            text-align: center;
        }}
        
        .chart-container img {{
            max-width: 100%;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        
        .alert {{
            padding: 15px 20px;
            border-radius: 10px;
            margin: 20px 0;
            display: flex;
            align-items: center;
        }}
        
        .alert-info {{
            background: #e3f2fd;
            border-left: 5px solid #2196f3;
            color: #1976d2;
        }}
        
        .alert-success {{
            background: #e8f5e9;
            border-left: 5px solid #4caf50;
            color: #388e3c;
        }}
        
        .alert-warning {{
            background: #fff3e0;
            border-left: 5px solid #ff9800;
            color: #f57c00;
        }}
        
        .footer {{
            background: #2c3e50;
            color: white;
            padding: 30px;
            text-align: center;
            font-size: 0.9em;
        }}
        
        .footer a {{
            color: #3498db;
            text-decoration: none;
        }}
        
        .summary-stats {{
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: 20px;
            margin: 30px 0;
        }}
        
        .stat-box {{
            flex: 1;
            min-width: 200px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
        }}
        
        .stat-box .value {{
            font-size: 2.5em;
            font-weight: 700;
            margin: 10px 0;
        }}
        
        .stat-box .label {{
            font-size: 1em;
            opacity: 0.9;
        }}
        
        @media (max-width: 768px) {{
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
            
            .header h1 {{
                font-size: 2em;
            }}
            
            .content {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🦄 Uniswap V3 Position Analysis</h1>
            <div class="subtitle">Comprehensive Performance Report</div>
            <div class="timestamp">Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</div>
        </div>
        
        <div class="content">
            <!-- Summary Stats -->
            <div class="summary-stats">
                <div class="stat-box">
                    <div class="label">Total Return</div>
                    <div class="value">{analysis_results['pnl_pct']:+.2f}%</div>
                    <div class="label">${analysis_results['pnl']:,.2f}</div>
                </div>
                <div class="stat-box">
                    <div class="label">Fees Earned</div>
                    <div class="value">${analysis_results['total_fees_usdc']:,.2f}</div>
                    <div class="label">{(analysis_results['total_fees_usdc'] / 100000 * 100):.2f}% of initial</div>
                </div>
                <div class="stat-box">
                    <div class="label">Final Value</div>
                    <div class="value">${analysis_results['final_total_value']:,.2f}</div>
                    <div class="label">from $100,000</div>
                </div>
            </div>
            
            <!-- Position Overview -->
            <div class="section">
                <h2>📊 Position Overview</h2>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-label">Pool</div>
                        <div class="metric-value">USDC/WETH</div>
                        <div class="metric-label">0.05% Fee Tier</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Block Range</div>
                        <div class="metric-value">{pool_state_end.block_number - pool_state_start.block_number:,}</div>
                        <div class="metric-label">{pool_state_start.block_number} → {pool_state_end.block_number}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Tick Range</div>
                        <div class="metric-value">{position.tick_upper - position.tick_lower + 1}</div>
                        <div class="metric-label">{position.tick_lower} → {position.tick_upper}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Liquidity</div>
                        <div class="metric-value">{position.liquidity/1e9:.2f}B</div>
                        <div class="metric-label">Position Liquidity</div>
                    </div>
                </div>
            </div>
            
            <!-- Price Movement -->
            <div class="section">
                <h2>💹 Price Movement</h2>
                <table>
                    <tr>
                        <th>Metric</th>
                        <th>Start</th>
                        <th>End</th>
                        <th>Change</th>
                    </tr>
                    <tr>
                        <td><strong>ETH Price</strong></td>
                        <td>${analysis_results['eth_price_start']:,.2f}</td>
                        <td>${analysis_results['eth_price_end']:,.2f}</td>
                        <td class="{'positive' if analysis_results['eth_price_end'] > analysis_results['eth_price_start'] else 'negative'}">
                            {((analysis_results['eth_price_end'] - analysis_results['eth_price_start']) / analysis_results['eth_price_start'] * 100):+.2f}%
                        </td>
                    </tr>
                    <tr>
                        <td><strong>Pool Tick</strong></td>
                        <td>{pool_state_start.tick:,}</td>
                        <td>{pool_state_end.tick:,}</td>
                        <td>{pool_state_end.tick - pool_state_start.tick:+,}</td>
                    </tr>
                    <tr>
                        <td><strong>Position Status</strong></td>
                        <td>{'In Range' if pool_state_start.tick >= position.tick_lower and pool_state_start.tick <= position.tick_upper else 'Out of Range'}</td>
                        <td>{'In Range' if pool_state_end.tick >= position.tick_lower and pool_state_end.tick <= position.tick_upper else 'Out of Range'}</td>
                        <td>-</td>
                    </tr>
                </table>
            </div>
            
            <!-- Position Details -->
            <div class="section">
                <h2>💰 Position Details</h2>
                <table>
                    <tr>
                        <th>Asset</th>
                        <th>Initial Amount</th>
                        <th>Final Amount</th>
                        <th>Fees Earned</th>
                        <th>Total Change</th>
                    </tr>
                    <tr>
                        <td><strong>USDC</strong></td>
                        <td>{analysis_results['initial_usdc_in_position']:,.2f}</td>
                        <td>{analysis_results['final_usdc']:,.2f}</td>
                        <td class="positive">+{analysis_results['fees_usdc']:,.2f}</td>
                        <td class="{'positive' if (analysis_results['final_usdc'] + analysis_results['fees_usdc'] - analysis_results['initial_usdc_in_position']) >= 0 else 'negative'}">
                            {(analysis_results['final_usdc'] + analysis_results['fees_usdc'] - analysis_results['initial_usdc_in_position']):+,.2f}
                        </td>
                    </tr>
                    <tr>
                        <td><strong>WETH</strong></td>
                        <td>{analysis_results['initial_weth_in_position']:.6f}</td>
                        <td>{analysis_results['final_weth']:.6f}</td>
                        <td class="positive">+{analysis_results['fees_weth']:.6f}</td>
                        <td class="{'positive' if (analysis_results['final_weth'] + analysis_results['fees_weth'] - analysis_results['initial_weth_in_position']) >= 0 else 'negative'}">
                            {(analysis_results['final_weth'] + analysis_results['fees_weth'] - analysis_results['initial_weth_in_position']):+.6f}
                        </td>
                    </tr>
                </table>
            </div>
            
            <!-- Performance Analysis -->
            <div class="section">
                <h2>📈 Performance Analysis</h2>
                <div class="chart-container">
                    <img src="data:image/png;base64,{summary_chart_b64}" alt="Performance Summary">
                </div>
                
                <table>
                    <tr>
                        <th>Component</th>
                        <th>Value (USDC)</th>
                        <th>% of Initial</th>
                        <th>Impact on P&L</th>
                    </tr>
                    <tr>
                        <td><strong>Impermanent Loss</strong></td>
                        <td class="negative">${analysis_results['impermanent_loss']:,.2f}</td>
                        <td class="negative">{analysis_results['impermanent_loss_pct']:.2f}%</td>
                        <td class="negative">-{abs(analysis_results['impermanent_loss'] / 100000 * 100):.2f}%</td>
                    </tr>
                    <tr>
                        <td><strong>Trading Fees</strong></td>
                        <td class="positive">${analysis_results['total_fees_usdc']:,.2f}</td>
                        <td class="positive">+{(analysis_results['total_fees_usdc'] / 100000 * 100):.2f}%</td>
                        <td class="positive">+{(analysis_results['total_fees_usdc'] / 100000 * 100):.2f}%</td>
                    </tr>
                    <tr>
                        <td><strong>Net Result</strong></td>
                        <td class="{pnl_class}">${analysis_results['pnl']:,.2f}</td>
                        <td class="{pnl_class}">{analysis_results['pnl_pct']:+.2f}%</td>
                        <td class="{pnl_class}">{analysis_results['pnl_pct']:+.2f}%</td>
                    </tr>
                </table>
            </div>
            
            <!-- Key Insights -->
            <div class="section">
                <h2>💡 Key Insights</h2>
                
                {self._generate_insights(analysis_results, position, pool_state_start, pool_state_end)}
            </div>
            
            <!-- Generated Visualizations -->
            <div class="section">
                <h2>📊 Additional Visualizations</h2>
                <div class="alert alert-info">
                    <strong>Generated Files:</strong> Check the output directory for detailed charts:
                    <ul style="margin-top: 10px; margin-left: 20px;">
                        <li><strong>liquidity_distribution.png</strong> - Liquidity distribution across ticks</li>
                        <li><strong>fee_accumulation.png</strong> - Detailed fee analysis dashboard</li>
                        <li><strong>position_value.png</strong> - Portfolio value breakdown</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated by Uniswap V3 Analysis Tool | <a href="https://github.com/your-repo">View on GitHub</a></p>
            <p style="margin-top: 10px; opacity: 0.8;">Disclaimer: This analysis is for informational purposes only and should not be considered financial advice.</p>
        </div>
    </div>
</body>
</html>
"""
        
        with open(output_path, 'w') as f:
            f.write(html_content)
    
    def _create_summary_chart(self, analysis_results: Dict[str, Any]):
        """Create a summary chart for the HTML report."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Left: Portfolio composition
        sizes = [
            abs(analysis_results['final_value_usdc']),
            abs(analysis_results['total_fees_usdc']),
            abs(analysis_results['unused_value'])
        ]
        labels = ['Position\nValue', 'Fees\nEarned', 'Unused\nFunds']
        colors = [self.colors['primary'], self.colors['success'], self.colors['info']]
        
        wedges, texts, autotexts = ax1.pie(sizes, labels=labels, colors=colors,
                                           autopct='%1.1f%%', startangle=45)
        
        for text in texts:
            text.set_fontsize(10)
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        ax1.set_title('Final Portfolio Composition', fontsize=12, fontweight='bold', pad=20)
        
        # Right: P&L waterfall
        categories = ['Initial', 'IL', 'Fees', 'Final']
        values = [100000, -abs(analysis_results['impermanent_loss']), 
                 analysis_results['total_fees_usdc'], analysis_results['pnl']]
        
        # Calculate cumulative values for waterfall
        cumulative = [100000]
        cumulative.append(cumulative[0] + values[1])
        cumulative.append(cumulative[1] + values[2])
        cumulative.append(100000 + analysis_results['pnl'])
        
        # Create waterfall effect
        for i in range(len(categories)):
            if i == 0:
                ax2.bar(categories[i], values[i], bottom=0, 
                       color=self.colors['dark'], alpha=0.8)
            elif i == len(categories) - 1:
                ax2.bar(categories[i], cumulative[i], bottom=0,
                       color=self.colors['warning'] if cumulative[i] >= 100000 else self.colors['danger'], 
                       alpha=0.8)
            else:
                if values[i] >= 0:
                    ax2.bar(categories[i], values[i], bottom=cumulative[i-1],
                           color=self.colors['success'], alpha=0.8)
                else:
                    ax2.bar(categories[i], abs(values[i]), bottom=cumulative[i],
                           color=self.colors['danger'], alpha=0.8)
        
        # Add connectors
        for i in range(len(categories) - 1):
            ax2.plot([i, i+1], [cumulative[i+1], cumulative[i+1]], 
                    'k--', alpha=0.5, linewidth=1)
        
        ax2.set_title('P&L Waterfall Analysis', fontsize=12, fontweight='bold', pad=20)
        ax2.set_ylabel('Portfolio Value (USDC)')
        ax2.axhline(y=100000, color='black', linestyle=':', alpha=0.5)
        ax2.set_ylim(min(cumulative) * 0.98, max(cumulative) * 1.02)
        
        plt.tight_layout()
        return fig
    
    def _generate_insights(self, analysis_results: Dict[str, Any], position: Position, 
                          pool_state_start: PoolState, pool_state_end: PoolState) -> str:
        """Generate intelligent insights based on analysis results."""
        insights = []
        
        # Performance insight
        if analysis_results['pnl'] > 0:
            insights.append(f"""
                <div class="alert alert-success">
                    <strong>✅ Profitable Position:</strong> Your position generated a 
                    {analysis_results['pnl_pct']:.2f}% return, outperforming a simple hold strategy
                    despite {analysis_results['impermanent_loss_pct']:.2f}% impermanent loss.
                </div>
            """)
        else:
            insights.append(f"""
                <div class="alert alert-warning">
                    <strong>⚠️ Negative Returns:</strong> The position resulted in a 
                    {abs(analysis_results['pnl_pct']):.2f}% loss. Impermanent loss 
                    ({analysis_results['impermanent_loss_pct']:.2f}%) exceeded fee earnings.
                </div>
            """)
        
        # Fee efficiency
        fee_roi = (analysis_results['total_fees_usdc'] / 
                  (analysis_results['initial_usdc_in_position'] + 
                   analysis_results['initial_weth_in_position'] * analysis_results['eth_price_start'])) * 100
        
        if fee_roi > 0.5:
            insights.append(f"""
                <div class="alert alert-info">
                    <strong>💰 Strong Fee Generation:</strong> Your position earned {fee_roi:.2f}% 
                    in fees relative to deployed capital, indicating good liquidity utilization.
                </div>
            """)
        
        # Range efficiency
        ticks_in_range = sum(1 for tick in range(position.tick_lower, position.tick_upper + 1)
                           if tick >= min(pool_state_start.tick, pool_state_end.tick) and 
                           tick <= max(pool_state_start.tick, pool_state_end.tick))
        range_efficiency = (ticks_in_range / (position.tick_upper - position.tick_lower + 1)) * 100
        
        insights.append(f"""
            <div class="alert alert-info">
                <strong>📊 Range Efficiency:</strong> The price spent approximately {range_efficiency:.0f}% 
                of the time within your position range, affecting fee generation potential.
            </div>
        """)
        
        return '\n'.join(insights) 