"""
Data loader module for historical OHLCV data.
Supports CSV files and generates synthetic data for testing.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional


def load_csv_data(filepath: str, symbol: str = "UNKNOWN") -> pd.DataFrame:
    """Load OHLCV data from CSV file."""
    df = pd.read_csv(filepath, parse_dates=True)
    
    # Normalize column names
    col_map = {}
    for col in df.columns:
        lower = col.lower().strip()
        if lower in ('date', 'time', 'datetime', 'timestamp'):
            col_map[col] = 'datetime'
        elif lower == 'open':
            col_map[col] = 'open'
        elif lower == 'high':
            col_map[col] = 'high'
        elif lower == 'low':
            col_map[col] = 'low'
        elif lower == 'close':
            col_map[col] = 'close'
        elif lower in ('volume', 'tick_volume', 'tickvol'):
            col_map[col] = 'volume'
        elif lower == 'spread':
            col_map[col] = 'spread'
    
    df = df.rename(columns=col_map)
    
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.set_index('datetime')
    
    df['symbol'] = symbol
    
    if 'spread' not in df.columns:
        df['spread'] = 0
    
    if 'volume' not in df.columns:
        df['volume'] = 1000
    
    return df.sort_index()


def generate_synthetic_data(
    symbol: str = "EURUSD",
    periods: int = 50000,
    timeframe_minutes: int = 15,
    start_price: float = 1.1000,
    volatility: float = 0.0001,
    trend_strength: float = 0.0,
    spread_pips: float = 1.0,
    seed: Optional[int] = 42
) -> pd.DataFrame:
    """
    Generate synthetic OHLCV data with configurable characteristics.
    
    Generates realistic price data with:
    - Trending and ranging regimes
    - Session-based volatility patterns
    - Realistic spreads
    - Volume patterns
    """
    if seed is not None:
        np.random.seed(seed)
    
    # Point size
    if "JPY" in symbol or "XAU" in symbol:
        point = 0.01 if "XAU" in symbol else 0.001
    else:
        point = 0.00001
    
    # Generate regime switching (trending vs ranging)
    regime_length = np.random.geometric(p=0.002, size=periods)
    regimes = []
    current_regime = np.random.choice(['trend_up', 'trend_down', 'range'])
    idx = 0
    while idx < periods:
        length = min(regime_length[idx % len(regime_length)], periods - idx)
        regimes.extend([current_regime] * length)
        idx += length
        current_regime = np.random.choice(['trend_up', 'trend_down', 'range'])
    regimes = regimes[:periods]
    
    # Generate returns based on regime
    returns = np.zeros(periods)
    for i in range(periods):
        hour = (i * timeframe_minutes // 60) % 24
        
        # Session-based volatility
        if 8 <= hour < 17:    # London
            vol_mult = 1.3
        elif 13 <= hour < 22:  # NY
            vol_mult = 1.2
        elif 0 <= hour < 9:    # Asian
            vol_mult = 0.7
        else:
            vol_mult = 0.8
        
        base_vol = volatility * vol_mult
        
        if regimes[i] == 'trend_up':
            returns[i] = np.random.normal(trend_strength * point, base_vol)
        elif regimes[i] == 'trend_down':
            returns[i] = np.random.normal(-trend_strength * point, base_vol)
        else:  # range
            returns[i] = np.random.normal(0, base_vol * 0.6)
    
    # Build price series
    close = np.zeros(periods)
    close[0] = start_price
    for i in range(1, periods):
        close[i] = close[i-1] * (1 + returns[i])
    
    # Generate OHLC from close
    high = np.zeros(periods)
    low = np.zeros(periods)
    open_price = np.zeros(periods)
    
    open_price[0] = close[0]
    for i in range(1, periods):
        open_price[i] = close[i-1] + np.random.normal(0, volatility * 0.1)
        bar_range = abs(returns[i]) * close[i] + np.random.exponential(volatility * 0.3) * close[i]
        
        if close[i] > open_price[i]:
            low[i] = min(open_price[i], close[i]) - np.random.uniform(0, bar_range * 0.3)
            high[i] = max(open_price[i], close[i]) + np.random.uniform(0, bar_range * 0.3)
        else:
            high[i] = max(open_price[i], close[i]) + np.random.uniform(0, bar_range * 0.3)
            low[i] = min(open_price[i], close[i]) - np.random.uniform(0, bar_range * 0.3)
    
    high[0] = close[0] + abs(np.random.normal(0, volatility)) * close[0]
    low[0] = close[0] - abs(np.random.normal(0, volatility)) * close[0]
    
    # Generate volume with session patterns
    volume = np.zeros(periods)
    for i in range(periods):
        hour = (i * timeframe_minutes // 60) % 24
        if 8 <= hour < 17:
            vol_base = 5000
        elif 13 <= hour < 22:
            vol_base = 6000
        else:
            vol_base = 2000
        volume[i] = max(100, np.random.poisson(vol_base))
    
    # Generate spread
    spread = np.full(periods, spread_pips)
    for i in range(periods):
        hour = (i * timeframe_minutes // 60) % 24
        if 0 <= hour < 8:
            spread[i] *= 1.5
        # Higher spread during high volatility
        if abs(returns[i]) > 2 * volatility:
            spread[i] *= 2.0
    
    # Create datetime index
    start_date = pd.Timestamp('2020-01-02 00:00:00')
    dates = pd.date_range(start=start_date, periods=periods, freq=f'{timeframe_minutes}min')
    
    # Filter out weekends
    mask = dates.weekday < 5
    dates = dates[mask][:periods]
    if len(dates) < periods:
        extra_dates = pd.date_range(start=dates[-1] + pd.Timedelta(minutes=timeframe_minutes),
                                     periods=periods - len(dates), freq=f'{timeframe_minutes}min')
        extra_mask = extra_dates.weekday < 5
        dates = dates.append(extra_dates[extra_mask])[:periods]
    
    df = pd.DataFrame({
        'open': open_price[:len(dates)],
        'high': high[:len(dates)],
        'low': low[:len(dates)],
        'close': close[:len(dates)],
        'volume': volume[:len(dates)],
        'spread': spread[:len(dates)],
        'symbol': symbol,
        'regime': regimes[:len(dates)]
    }, index=dates[:len(open_price)])
    
    df.index.name = 'datetime'
    
    return df


def generate_xauusd_data(periods: int = 50000, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic XAUUSD data with gold-specific characteristics."""
    return generate_synthetic_data(
        symbol="XAUUSD",
        periods=periods,
        timeframe_minutes=15,
        start_price=1900.0,
        volatility=0.0015,
        trend_strength=0.1,
        spread_pips=30.0,
        seed=seed
    )


def generate_eurusd_data(periods: int = 50000, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic EURUSD data with forex-specific characteristics."""
    return generate_synthetic_data(
        symbol="EURUSD",
        periods=periods,
        timeframe_minutes=15,
        start_price=1.1000,
        volatility=0.0004,
        trend_strength=0.05,
        spread_pips=1.0,
        seed=seed
    )
