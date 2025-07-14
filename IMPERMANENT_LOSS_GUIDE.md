# Impermanent Loss Guide

This guide explains the impermanent loss calculations used in the DeFi Analysis tool.

## Overview

Impermanent loss (IL) is the difference in value between holding tokens in a liquidity pool versus holding them in your wallet. It occurs due to the automatic rebalancing that happens in AMMs when prices change.

## Two Approaches to IL Calculation

### 1. Position-Based Calculation (Used in Main Analysis)

This method calculates the actual dollar loss based on the specific position:

```python
IL_amount = HODL_value - LP_final_value
IL_percentage = (IL_amount / initial_value) * 100
```

**Advantages:**

- Works for both full-range and concentrated liquidity positions
- Accounts for actual token rebalancing within position ranges
- Provides real dollar impact

**Use Case:** Analyzing actual Uniswap V3 positions with specific ranges

### 2. Academic Formula (For Full-Range Positions)

The standard formula for constant product AMMs (x\*y=k):

```python
IL = sqrt(R) - 0.5 * (R + 1)
# where R = final_price / initial_price
```

**Properties:**

- Only applies to full-range positions (0 to ∞)
- Symmetric for reciprocal price ratios
- Independent of position size

**Use Case:** Theoretical analysis and Uniswap V2-style positions

## Examples

### Price Doubles (2x)

- Academic Formula: IL = -8.58%
- Meaning: You lose 8.58% compared to just holding

### Price Halves (0.5x)

- Academic Formula: IL = -4.29%
- Meaning: You lose 4.29% compared to just holding

### Price Triples (3x)

- Academic Formula: IL = -26.8%
- Meaning: You lose 26.8% compared to just holding

## Key Insights

1. **IL is always negative** - You always "lose" compared to holding when prices move
2. **IL is temporary** - If price returns to original, IL disappears
3. **Fees can offset IL** - Trading fees earned may compensate for IL
4. **Concentrated positions** - Have different IL profiles than full-range

## Using the Code

### For actual position analysis:

```python
analyzer = PositionAnalyzer(calculator)
il_amount, il_pct = analyzer.calculate_impermanent_loss(
    initial_usdc, initial_weth,
    final_usdc, final_weth,
    initial_eth_price, final_eth_price
)
```

### For theoretical full-range IL:

```python
il_pct = PositionAnalyzer.calculate_impermanent_loss_full_range(
    initial_price=2000,
    final_price=3000
)
# Returns: -2.526%
```

## Further Reading

- [Uniswap V3 Whitepaper](https://uniswap.org/whitepaper-v3.pdf)
- [Understanding Uniswap Returns](https://docs.uniswap.org/concepts/introduction/liquidity-user-guide)
