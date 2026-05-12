# SAR Expert Advisor - Professional Quant Fund Grade System

## Overview

A professional **Stop-And-Reverse (SAR)** Expert Advisor for MetaTrader 5, accompanied by a comprehensive Python backtesting, optimization, and statistical analysis framework. This system implements a dynamic SAR strategy that is always in the market, automatically reversing direction when price hits defined reversal levels.

## Architecture

```
Fahed/
├── MQL5/
│   ├── Experts/
│   │   └── SAR_Expert.mq5          # Main EA (MetaTrader 5)
│   └── Include/
│       ├── SARTypes.mqh             # Type definitions & enums
│       ├── SARFilters.mqh           # Trend/session/volume filters
│       ├── SARTrailing.mqh          # 6 trailing stop modes
│       └── SARRiskManager.mqh       # Professional risk management
├── python/
│   ├── backtesting/
│   │   ├── engine.py                # Core backtesting engine
│   │   └── indicators.py            # Technical indicators
│   ├── optimization/
│   │   └── optimizer.py             # Grid, Genetic, Bayesian optimization
│   ├── analysis/
│   │   └── statistical.py           # Monte Carlo, Walk Forward, Edge analysis
│   ├── data/
│   │   └── data_loader.py           # Data loading & synthetic generation
│   └── run_analysis.py              # Main analysis runner
├── docs/
│   ├── analysis_output.txt          # Full analysis output
│   └── ANALYSIS_REPORT.md           # Comprehensive analysis report
└── requirements.txt
```

## Core Strategy Logic

1. System opens an initial Market order (Buy or Sell)
2. Places a **Pending Stop order** in opposite direction at defined distance
3. When the pending order is triggered:
   - Current position is closed
   - The pending order becomes the new active trade
   - A new pending order is placed in the opposite direction
4. Process repeats continuously

## Features

### Distance Modes (5 types)
- **Fixed**: Constant distance in points (50-300)
- **ATR-Based**: Dynamic distance using ATR multiplier
- **Volatility Adaptive**: ATR adjusted by volatility ratio
- **Session-Based**: Distance adjusted by trading session
- **Spread-Adjusted**: ATR + spread compensation

### Trailing Stop Modes (6 types)
- **Fixed Trailing**: Constant trail distance
- **ATR Trailing**: Trail based on ATR
- **Chandelier Exit**: Highest high/lowest low - ATR × multiplier
- **Step Trailing**: Lock profit in discrete steps
- **Volatility Trailing**: Dynamic multiplier based on vol regime
- **Hybrid Trailing**: Best of ATR + Step trailing

### Trend Filters
- ADX with directional movement
- EMA Crossover (fast/slow)
- Market Structure (HH/HL/LH/LL)
- ATR Expansion
- Composite (multiple combined)

### Protection System
- Max consecutive reversals limit
- Max daily loss percentage
- Spread filter (max spread threshold)
- Cooldown between reversals (bars)
- Volatility shutdown (extreme ATR)
- Equity protection (% from peak)
- Slippage protection

### Multi-Timeframe Support
- Higher timeframe trend filter (H1 trend, M15 execution)
- HTF EMA direction confirmation

### Session Filters
- London (08:00-17:00)
- New York (13:00-22:00)
- Asian (00:00-09:00)
- London+NY Overlap (13:00-17:00)

## Python Analysis Framework

### Backtesting Engine
- Realistic simulation with spread, commission, and slippage
- All 5 distance modes
- All 6 trailing stop modes
- All filter modes
- Session-aware execution
- Regime detection and labeling

### Optimization Methods
- **Grid Search**: Exhaustive parameter combination testing
- **Genetic Algorithm**: Evolutionary optimization with crossover/mutation
- **Bayesian Optimization**: Optuna-based TPE sampler

### Statistical Analysis
- **Edge Analysis**: T-test, bootstrap CI, Cohen's d effect size
- **Monte Carlo Simulation**: 1000 trial shuffle testing
- **Walk Forward Analysis**: K-fold in-sample/out-of-sample testing
- **Whipsaw Analysis**: Deep choppy market impact assessment
- **Regime Analysis**: Performance by market condition
- **Long-Term Viability**: Composite scoring system

## Installation

### Python Dependencies
```bash
pip install numpy pandas scipy scikit-learn matplotlib seaborn optuna joblib
```

### MQL5
Copy the `MQL5/Experts/` and `MQL5/Include/` folders to your MetaTrader 5 data directory.

## Running the Analysis

```bash
cd Fahed
python python/run_analysis.py
```

This runs the complete analysis pipeline including:
- Baseline tests across multiple configurations
- All distance mode comparisons
- All trailing stop comparisons
- Session filter tests
- Start direction tests
- Exit mode comparison
- Multi-method optimization
- Statistical analysis (Monte Carlo, Walk Forward, Edge)
- Viability assessment

## License

Proprietary - Quant SAR Project
