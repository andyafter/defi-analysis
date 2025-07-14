# Uniswap V3 Liquidity Analysis Tool

High-performance Python framework for analyzing Uniswap V3 liquidity positions with advanced optimization features.

## 🚀 Features

- **Position Analysis**: Calculate impermanent loss, fee earnings, and P&L
- **10x Performance**: Intelligent caching, parallel processing, connection pooling
- **Rich Output**: Interactive charts, HTML reports, performance metrics
- **Easy CLI**: Simple commands for complex analysis

## 📊 Performance

- Pool state fetching: **4.3x faster**
- Event processing: **100+ events/second**
- Cache hit rate: **Up to 100%**
- Overall speedup: **10-100x** for repeated queries

## 🛠️ Quick Start

### 1. Install

```bash
git clone <repository-url>
cd defi-analysis
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp env.example .env
# Add your Ethereum RPC URL to .env
```

### 3. Run

```bash
# Quick analysis with defaults
python scripts/main.py

# Or use CLI
python scripts/cli.py analyze --pool usdc_weth
```

## 📋 CLI Commands

| Command          | Description         | Example                                                                            |
| ---------------- | ------------------- | ---------------------------------------------------------------------------------- |
| `analyze`        | Run preset analysis | `python scripts/cli.py analyze --pool usdc_weth`                                   |
| `analyze-custom` | Custom parameters   | `python scripts/cli.py analyze-custom --start-block 17618642 --end-block 17618742` |
| `pool-info`      | Show pool state     | `python scripts/cli.py pool-info --pool usdc_weth`                                 |
| `clear-cache`    | Clear cached data   | `python scripts/cli.py clear-cache`                                                |

### Custom Analysis Example

```bash
python scripts/cli.py analyze-custom \
  --start-block 17618642 \
  --end-block 17618742 \
  --pool-address 0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640 \
  --tick-lower 200540 \
  --tick-upper 200560 \
  --initial-value 100000
```

## ⚙️ Configuration

Edit `config.yaml`:

```yaml
# Connection
ethereum:
  rpc_url: ${ETH_RPC_URL} # From .env

# Performance
performance:
  max_workers: 20
  max_concurrent_requests: 10

# Pools
pools:
  usdc_weth:
    address: "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640"
    fee_tier: 500 # 0.05%
```

## 📈 Output

### Console

- Position details & liquidity
- Impermanent loss & fees
- Portfolio P&L summary
- Performance metrics

### Files Generated

- **PNG Charts**: Liquidity distribution, fee accumulation
- **HTML Report**: Complete analysis summary
- **analysis.log**: Detailed execution logs

### Example Output

```
Position Summary:
  Final USDC: 84,847.42
  Final WETH: 6.374503
  Total Value: $97,304.87

Impermanent Loss: 0.01% ($14.50)
Fees Earned: $16,561.84
Total P&L: +16.59% ($16,585.95)

Performance: 2.59s (100% cache hits)
```

## 🧪 Testing

```bash
# All tests
python run_tests.py

# Specific tests
pytest tests/test_uniswap_v3.py -v

# Benchmarks
python scripts/benchmark_optimizations.py
```

## 🐛 Troubleshooting

| Issue            | Solution                                  |
| ---------------- | ----------------------------------------- |
| 429 Rate Limit   | Lower `max_concurrent_requests` in config |
| Connection Error | Check RPC URL in .env                     |
| Import Error     | Activate venv, reinstall requirements     |
| Cache Issues     | Run `clear-cache` command                 |

## 📚 Documentation

- [Fee Calculation Guide](FEE_ESTIMATION_GUIDE.md)
- [Performance Benchmarks](RPC_OPTIMIZATION_RESULTS.md)
- [Impermanent Loss Guide](IMPERMANENT_LOSS_GUIDE.md)

## 📄 License

MIT License - see LICENSE file for details.
