# Uniswap V3 Liquidity Analysis

This project analyzes a Uniswap V3 liquidity position on the USDC/WETH pool for the Tokka Labs take-home assignment.

## Overview

The analysis involves:

- Creating a Uniswap V3 position with 100,000 USDC worth of assets (50% USDC, 50% WETH)
- Tick range: 200540 to 200560
- Analysis period: Block 17618642 to 17618742
- Pool: USDC/WETH (0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640)

## Requirements

- Python 3.9+
- Ethereum node access (Infura, Alchemy, or other RPC provider)
- Required Python packages (see requirements.txt)

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your Ethereum RPC URL:

```bash
cp env.example .env
# Edit .env and add your API key
```

3. Run the analysis:

```bash
python main.py
```

## Testing

Run the unit tests:

```bash
python run_tests.py
```

Note: Tests that don't require blockchain interaction will run without an RPC URL.

## Project Structure

- `main.py` - Main entry point for the analysis
- `uniswap_v3.py` - Uniswap V3 specific calculations and interactions
- `data_fetcher.py` - Blockchain data fetching utilities
- `analysis.py` - Analysis and calculation functions
- `visualization.py` - Plotting and visualization functions
- `tests/` - Unit tests for all modules

## Output

The analysis generates:

1. Impermanent loss calculation
2. Liquidity distribution plots
3. Swap fee accumulation plots
4. Portfolio PnL report

Results are saved in the `output/` directory.
