# Fee Estimation Algorithm Guide

## Overview

The fee estimation algorithm calculates the expected fees earned by a Uniswap V3 liquidity position based on historical swap data. This guide explains how the algorithm works and how to validate its correctness.

## How the Algorithm Works

### 1. Fee Collection in Uniswap V3

- **Fee Rate**: 0.05% (500/1000000) for the USDC/WETH pool
- **Collection**: Fees are deducted from swap amounts
- **Distribution**: Fees go to liquidity providers proportionally

### 2. Algorithm Steps

```python
For each swap:
1. Calculate total fees = swap_amount × fee_rate
2. Determine tick range crossed (from previous tick to current tick)
3. Distribute fees equally across all crossed ticks
4. Calculate our share at each tick = our_liquidity / total_liquidity
5. Accumulate our fees = total_fees × our_share
```

### 3. Key Formula

```
Fee per tick = (Total swap fee / Ticks crossed) × (Our liquidity / Total liquidity)
```

### 4. Example Calculation

**Swap**: 1,000,000 USDC → 500 WETH

- Total USDC fee: 1,000,000 × 0.0005 = 500 USDC
- Total WETH fee: 500 × 0.0005 = 0.25 WETH
- If our liquidity is 10% of total: We earn 50 USDC + 0.025 WETH

## Assumptions and Limitations

### Assumptions

1. **Static Liquidity**: Liquidity distribution doesn't change during the period
2. **Linear Tick Crossing**: Swaps cross ticks uniformly
3. **Complete Swaps**: All swaps are fully executed within the pool

### Limitations

1. **Approximation**: Real fee accrual is more complex (uses fee growth tracking)
2. **No Partial Ticks**: Doesn't account for partial tick occupancy
3. **Historical Only**: Based on past data, not predictive

## Validation Methods

### 1. Unit Testing

Run the test suite:

```bash
python -m pytest tests/test_analysis.py -v
```

### 2. Manual Validation

Run the validation script:

```bash
python test_fee_estimation.py
```

### 3. Cross-Reference Methods

#### a) Compare with Uniswap Subgraph

```graphql
query {
  pool(id: "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640") {
    totalFeesUSD
    feesUSD
  }
}
```

#### b) On-Chain Verification

- Check `feeGrowthGlobal0X128` and `feeGrowthGlobal1X128` values
- Compare position's `tokensOwed0` and `tokensOwed1`

#### c) Mathematical Validation

- Total fees collected = Σ(swap_volume × fee_rate)
- Sum of all LP fees should equal total fees
- Individual LP share = (LP liquidity / Total liquidity) × Total fees

### 4. Sanity Checks

1. **Fee Rate Check**: Fees should be ~0.05% of swap volume
2. **Proportionality**: Larger positions should earn more fees
3. **Range Check**: Only ticks within position range should have fees
4. **Non-Negative**: All fees should be ≥ 0

## Common Issues and Solutions

### Issue 1: Fees Too High/Low

**Cause**: Incorrect liquidity share calculation
**Solution**: Verify liquidity distribution data

### Issue 2: Missing Fees

**Cause**: Swap events not captured or ticks not in range
**Solution**: Check block range and swap event filtering

### Issue 3: Uneven Distribution

**Cause**: Incorrect tick crossing logic
**Solution**: Verify tick range calculation for each swap

## Improving Accuracy

1. **Use Shorter Time Periods**: Reduces liquidity change impact
2. **Include More Events**: Capture mint/burn events for liquidity tracking
3. **Fee Growth Tracking**: Implement actual Uniswap V3 fee growth mechanism
4. **Real-time Updates**: Query current fee values from contracts

## Code Example

```python
# Accurate fee calculation example
def calculate_exact_fees(position, pool_contract, block_number):
    """Get exact fees using on-chain data."""
    # Get fee growth inside position
    fee_growth_inside_0 = pool_contract.functions.feeGrowthInside0X128(
        position.tick_lower,
        position.tick_upper
    ).call(block_identifier=block_number)

    # Calculate fees owed
    fees_0 = (fee_growth_inside_0 * position.liquidity) / 2**128

    return fees_0
```

## Conclusion

The fee estimation algorithm provides a reasonable approximation of fees earned. For production use, consider implementing the exact fee growth tracking mechanism used by Uniswap V3 contracts for precise calculations.
