# Uniswap V3 Liquidity Analysis Tool

A high-performance Python framework for analyzing Uniswap V3 liquidity positions, calculating impermanent loss, and estimating fee earnings with advanced caching and optimization features.

## 🚀 Key Features

- **Comprehensive Analysis**: Calculate liquidity positions, impermanent loss, and fee earnings
- **Performance Optimized**: 4-10x faster with caching, parallel processing, and connection pooling
- **Flexible CLI**: Easy-to-use command-line interface with multiple analysis modes
- **Rich Visualizations**: Generate interactive charts and HTML reports
- **Modular Architecture**: Clean, extensible codebase with well-defined interfaces
- **Smart Caching**: Intelligent caching system that preserves real-time data accuracy

## 📊 Performance Metrics

Based on benchmark results:

- **Pool State Fetching**: 4.3x faster with optimizations
- **Event Processing**: 100+ events/second
- **Cache Hit Rate**: Up to 100% for historical data
- **Overall Speedup**: 10-100x for repeated queries

## 🛠️ Requirements

- Python 3.8+ (tested on 3.12)
- Ethereum RPC endpoint (Infura, Alchemy, or local node)
- 100MB+ disk space for caching

## 📦 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd defi-analysis
```

### 2. Set Up Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp env.example .env
# Edit .env and add your Ethereum RPC URL
```

Example `.env` file:

```
ETH_RPC_URL=https://mainnet.infura.io/v3/YOUR_PROJECT_ID
```

## 🏗️ Project Structure

```
defi-analysis/
├── src/                      # Core library modules
│   ├── analysis/            # Position analysis & fee calculations
│   ├── blockchain/          # Web3/Ethereum interaction
│   ├── uniswap/            # Uniswap V3 mathematics
│   ├── visualization/       # Charts and reports
│   ├── config/             # Configuration management
│   └── data/               # Caching layer
├── scripts/                 # Executable scripts
│   ├── main.py             # Quick analysis script
│   ├── cli.py              # Full CLI interface
│   └── benchmark_optimizations.py  # Performance tests
├── tests/                   # Test suite
├── config.yaml             # Configuration file
└── output/                 # Generated reports (gitignored)
```

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed documentation.

## 🚀 Quick Start

### Basic Analysis

Run a quick analysis with default parameters:

```bash
python scripts/main.py
```

This analyzes:

- Pool: USDC/WETH 0.05%
- Period: 100 blocks (17618642-17618742)
- Initial capital: $100,000
- Position range: Ticks 200540-200560

### CLI Analysis

Use the full CLI for more control:

```bash
python scripts/cli.py analyze --pool usdc_weth --analysis default
```

## 📋 CLI Commands

### `analyze` - Run Configured Analysis

```bash
python scripts/cli.py analyze --pool <pool_name> --analysis <profile>
```

Options:

- `--pool`: Pool identifier from config.yaml
- `--analysis`: Analysis profile from config.yaml
- `--cache/--no-cache`: Enable/disable caching
- `--output-dir`: Custom output directory

### `analyze-custom` - Custom Parameters

```bash
python scripts/cli.py analyze-custom \
  --start-block 17618642 \
  --end-block 17618742 \
  --pool-address 0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640 \
  --tick-lower 200540 \
  --tick-upper 200560 \
  --initial-value 100000
```

### `pool-info` - Display Pool Information

```bash
python scripts/cli.py pool-info --pool usdc_weth
```

Shows current pool state including:

- Current tick and price
- Total liquidity
- Fee tier
- Token addresses

### `clear-cache` - Clear Cached Data

```bash
python scripts/cli.py clear-cache
```

### `validate-config` - Validate Configuration

```bash
python scripts/cli.py validate-config
```

## ⚙️ Configuration

Edit `config.yaml` to customize:

```yaml
# Ethereum Connection
ethereum:
  rpc_url: ${ETH_RPC_URL} # From environment
  retry_attempts: 3
  timeout: 30

# Performance Settings
performance:
  max_workers: 20 # Thread pool size
  max_concurrent_requests: 10 # RPC rate limiting
  chunk_size: 2000 # Event fetch chunk size

# Pool Configuration
pools:
  usdc_weth:
    address: "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"
    name: "USDC/WETH 0.05%"
    fee_tier: 500 # 0.05%

# Analysis Profiles
analysis_profiles:
  default:
    start_block: 17618642
    end_block: 17618742
    initial_portfolio_value: 100000
    portfolio_split: 0.5
    position:
      tick_lower: 200540
      tick_upper: 200560
```

## 🚄 Performance Optimizations

### 1. RPC Call Optimizations

- **Connection Pooling**: Reuses HTTP connections
- **Rate Limiting**: Prevents endpoint overload
- **Batch Processing**: Groups multiple calls
- **Retry Logic**: Handles transient failures

### 2. Intelligent Caching

- **Block-Specific Cache Keys**: Historical data cached permanently
- **Real-Time Data**: Always fetches fresh latest blocks
- **Fee Calculations**: Caches complex computations
- **24-Hour TTL**: Configurable cache expiration

### 3. Parallel Processing

- **Concurrent RPC Calls**: Up to 20 parallel requests
- **Event Chunk Processing**: Parallel event fetching
- **Async/Await**: Non-blocking I/O operations

### 4. Computational Optimizations

- **NumPy Vectorization**: Fast array operations
- **Efficient Data Structures**: Optimized memory usage
- **Lazy Loading**: Loads data only when needed

## 📈 Output & Visualizations

The tool generates:

### 1. Console Output

- Position details and liquidity minted
- Impermanent loss calculations
- Fee earnings estimation
- Portfolio P&L summary
- Performance metrics

### 2. Charts (PNG)

- **Liquidity Distribution**: Pool liquidity vs your position
- **Fee Accumulation**: Fees earned by tick range

### 3. HTML Report

- Comprehensive analysis summary
- Interactive tables
- All metrics in one document

### 4. Performance Metrics

- Operation timings
- Cache hit rates
- RPC call statistics

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
python run_tests.py

# Run specific test file
python -m pytest tests/test_uniswap_v3.py -v

# Run benchmarks
python scripts/benchmark_optimizations.py
```

## 🔍 Example Analysis Output

```
================================================================================
ANALYSIS RESULTS
================================================================================

Position at End Block:
  USDC balance: 84,847.42
  WETH balance: 6.374503
  Total value in USDC: $97,304.87

Impermanent Loss:
  IL amount: $14.50
  IL percentage: 0.01%

Estimated Fees Earned:
  USDC fees: 8,281.16
  WETH fees: 4.237243
  Total fees in USDC: $16,561.84

Portfolio PnL:
  Initial value: $100,000.00
  Final value: $116,585.95
  PnL: $16,585.95
  PnL percentage: +16.59%

================================================================================
PERFORMANCE METRICS
================================================================================
Pool State (Start Block)                     0.00s (CACHED)
Swap Events (54 events)                      0.01s (CACHED)
Position Analysis                            0.00s
Total Execution Time:                        2.59s
Cache Hit Rate:                            100.0%
================================================================================
```

## 🐛 Troubleshooting

### Common Issues

1. **Rate Limiting (429 errors)**

   - Reduce `max_concurrent_requests` in config.yaml
   - Use a different RPC endpoint
   - Enable caching to reduce requests

2. **Connection Errors**

   - Check your RPC URL in .env
   - Verify internet connection
   - Try a different RPC provider

3. **Cache Issues**

   - Run `python scripts/cli.py clear-cache`
   - Delete the `cache/` directory
   - Check disk space

4. **Import Errors**
   - Ensure virtual environment is activated
   - Run `pip install -r requirements.txt`
   - Check Python version (3.8+)

## 📚 Additional Documentation

- [FEE_ESTIMATION_GUIDE.md](FEE_ESTIMATION_GUIDE.md) - Fee calculation methodology
- [RPC_OPTIMIZATION_RESULTS.md](RPC_OPTIMIZATION_RESULTS.md) - Performance test results
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Detailed code organization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- Uniswap V3 for the innovative AMM design
- Web3.py for Ethereum interaction
- The DeFi community for inspiration
