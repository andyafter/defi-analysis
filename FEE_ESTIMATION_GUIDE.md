# Fee Estimation Guide

## How It Works

The algorithm estimates fees earned by a Uniswap V3 position based on historical swaps.

### Core Formula

```
Your Fees = Swap Volume × Fee Rate × (Your Liquidity / Total Liquidity)
```

### Algorithm Steps

1. **For each swap**: Calculate total fees (swap amount × 0.05%)
2. **Find tick range**: Track which ticks the swap crossed
3. **Distribute fees**: Split fees equally across crossed ticks
4. **Calculate share**: Your liquidity ÷ total liquidity at each tick
5. **Sum earnings**: Accumulate your portion of fees

### Example

```
Swap: 1,000,000 USDC → 500 WETH
Pool fee: 0.05%
Your share: 10% of pool liquidity

Total fees: 500 USDC + 0.25 WETH
Your earnings: 50 USDC + 0.025 WETH
```

## Accuracy

### What We Assume

- Static liquidity distribution during analysis period
- Linear fee distribution across ticks
- Complete swap execution within pool

### What We Approximate

- Real Uniswap uses complex fee growth tracking
- We simplify to tick-based distribution
- Historical analysis only, not predictive

## Validation

### Quick Checks

```bash
# Run tests
pytest tests/test_analysis.py::test_fee_calculation_accuracy -v

# Sanity checks
- Fees ≈ 0.05% of volume
- Larger positions earn more
- Only in-range ticks earn fees
```

### Cross-Reference

1. **Subgraph**: Compare with Uniswap analytics
2. **On-chain**: Check `feeGrowthGlobal` values
3. **Math**: Total fees = Σ(volume × 0.05%)

## Common Issues

| Issue        | Cause                 | Fix                |
| ------------ | --------------------- | ------------------ |
| Wrong fees   | Bad liquidity data    | Verify pool state  |
| Missing fees | Incomplete events     | Check block range  |
| Zero fees    | Position out of range | Verify tick bounds |

## Advanced: Exact Calculation

For production use, implement Uniswap's fee growth tracking:

```python
def get_exact_fees(position, pool_contract, block):
    """Get precise fees from contract."""
    fee_growth = pool_contract.functions.feeGrowthInside0X128(
        position.tick_lower,
        position.tick_upper
    ).call(block_identifier=block)

    return (fee_growth * position.liquidity) // 2**128
```

## Summary

Our estimation provides good approximations for analysis. For exact values, use on-chain fee growth data.
