# Uniswap V3 Liquidity Analysis Tool

A comprehensive Python framework for analyzing Uniswap V3 liquidity positions, calculating impermanent loss, and estimating fee earnings.

## Features

- **Uniswap V3 Analysis**: Calculate liquidity positions, impermanent loss, and fee earnings
- **CLI Interface**: Easy-to-use command-line interface for various analysis scenarios
- **Modular Architecture**: Clean separation of concerns with extensible interfaces
- **Caching Support**: Improved performance with file-based caching
- **Rich Visualizations**: Generate charts and HTML reports

## Requirements

- Python 3.8+
- Ethereum RPC endpoint (Infura, Alchemy, or local node)
- Dependencies listed in `requirements.txt`

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd defi-analysis
```

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
# For Python 3.13+ compatibility
export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
pip install -r requirements.txt
```

4. Set up environment variables:

```bash
cp env.example .env
# Edit .env and add your Ethereum RPC URL
```

## Quick Start

### Default Analysis

Run the analysis with hardcoded parameters:

```bash
python main.py
```

### CLI Usage

Run analysis with configuration:

```bash
python cli.py analyze
```

## CLI Commands

- **`analyze`**: Run analysis using configuration profiles

  ```bash
  python cli.py analyze --pool usdc_weth --analysis default
  ```

- **`analyze-custom`**: Run analysis with custom parameters

  ```bash
  python cli.py analyze-custom \
    --start-block 17618642 \
    --end-block 17618742 \
    --pool-address 0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640 \
    --tick-lower 200540 \
    --tick-upper 200560
  ```

- **`pool-info`**: Display pool information

  ```bash
  python cli.py pool-info --pool usdc_weth
  ```

- **`clear-cache`**: Clear cached data
  ```bash
  python cli.py clear-cache
  ```

## Configuration

The `config.yaml` file controls the analysis parameters:

```yaml
# Ethereum RPC Configuration
ethereum:
  rpc_url: ${ETH_RPC_URL} # From environment
  retry_attempts: 3
  timeout: 30

# Pool Configuration
pools:
  usdc_weth:
    address: "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"
    name: "USDC/WETH 0.05%"
    fee_tier: 500 # 0.05%
    token0:
      address: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
      symbol: "USDC"
      decimals: 6
    token1:
      address: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
      symbol: "WETH"
      decimals: 18

# Analysis Configuration
analysis:
  default:
    start_block: 17618642
    end_block: 17618742
    initial_portfolio_value: 100000
    portfolio_split: 0.5
    position:
      tick_lower: 200540
      tick_upper: 200560
```

### Configuration Examples

**Conservative Strategy** (wider tick range):

```yaml
analysis:
  conservative:
    start_block: 17618642
    end_block: 17618742
    initial_portfolio_value: 100000
    portfolio_split: 0.5
    position:
      tick_lower: 200000 # Wider range
      tick_upper: 201000
```

**Aggressive Strategy** (narrower tick range):

```yaml
analysis:
  aggressive:
    start_block: 17618642
    end_block: 17618742
    initial_portfolio_value: 100000
    portfolio_split: 0.5
    position:
      tick_lower: 200580 # Narrower range
      tick_upper: 200600
```

## Testing

Run the test suite:

```bash
# Run all tests
python run_tests.py

# Or using pytest directly
python -m pytest tests/ -v
```

## Output

The analysis generates:

- **liquidity_distribution.png**: Visualization of liquidity across tick ranges
- **fee_accumulation.png**: Fee earnings by tick
- **analysis_report.html**: Comprehensive HTML report with all metrics

Results are saved in the `output/` directory.

## Extending the Framework

### Add Support for Another Pool

Add to `config.yaml`:

```yaml
pools:
  wbtc_weth:
    address: "0xCBCdF9626bC03E24f779434178A73a0B4bad62eD"
    name: "WBTC/WETH 0.3%"
    fee_tier: 3000 # 0.3%
    token0:
      address: "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599"
      symbol: "WBTC"
      decimals: 8
    token1:
      address: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
      symbol: "WETH"
      decimals: 18
```

### Custom Analysis Implementation

```python
from src.core.interfaces import IAnalysisStrategy

class CustomStrategy(IAnalysisStrategy):
    async def analyze(self, position, start_state, end_state, events, **kwargs):
        # Your custom analysis logic
        return AnalysisResult(...)
```

## License

MIT License
