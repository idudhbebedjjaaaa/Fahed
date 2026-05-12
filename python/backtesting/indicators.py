"""
Technical indicators used by the SAR backtesting engine.
All indicators operate on pandas DataFrames with OHLCV columns.
"""

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period).mean()


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range."""
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Average Directional Index.
    Returns DataFrame with columns: ADX, +DI, -DI
    """
    high = df['high']
    low = df['low']
    close = df['close']
    
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    tr = atr_raw(df, period=1)
    
    atr_val = tr.ewm(span=period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr_val)
    minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr_val)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
    adx_val = dx.ewm(span=period, adjust=False).mean()
    
    return pd.DataFrame({
        'ADX': adx_val,
        '+DI': plus_di,
        '-DI': minus_di
    }, index=df.index)


def atr_raw(df: pd.DataFrame, period: int = 1) -> pd.Series:
    """Raw True Range (unsmoothed)."""
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def market_structure(df: pd.DataFrame, lookback: int = 10) -> pd.Series:
    """
    Detect market structure: Higher Highs/Higher Lows vs Lower Highs/Lower Lows.
    Returns: 1 for uptrend, -1 for downtrend, 0 for range
    """
    result = pd.Series(0, index=df.index)
    
    recent_high = df['high'].rolling(lookback).max()
    prev_high = df['high'].shift(lookback).rolling(lookback).max()
    recent_low = df['low'].rolling(lookback).min()
    prev_low = df['low'].shift(lookback).rolling(lookback).min()
    
    uptrend = (recent_high > prev_high) & (recent_low > prev_low)
    downtrend = (recent_high < prev_high) & (recent_low < prev_low)
    
    result[uptrend] = 1
    result[downtrend] = -1
    
    return result


def volatility_ratio(df: pd.DataFrame, fast_period: int = 5, slow_period: int = 50) -> pd.Series:
    """Ratio of short-term to long-term volatility."""
    atr_fast = atr(df, fast_period)
    atr_slow = atr(df, slow_period)
    return atr_fast / (atr_slow + 1e-10)


def session_label(df: pd.DataFrame) -> pd.Series:
    """Label each bar with its trading session."""
    hours = df.index.hour
    labels = pd.Series('other', index=df.index)
    
    labels[(hours >= 0) & (hours < 8)] = 'asian'
    labels[(hours >= 8) & (hours < 13)] = 'london'
    labels[(hours >= 13) & (hours < 17)] = 'london_ny'
    labels[(hours >= 17) & (hours < 22)] = 'newyork'
    
    return labels


def regime_detector(df: pd.DataFrame, atr_period: int = 14, lookback: int = 50) -> pd.Series:
    """
    Detect market regime: trending, ranging, high_vol, low_vol.
    Uses ATR ratio and directional movement.
    """
    atr_val = atr(df, atr_period)
    atr_avg = atr_val.rolling(lookback).mean()
    vol_ratio = atr_val / (atr_avg + 1e-10)
    
    adx_data = adx(df, atr_period)
    
    regime = pd.Series('range', index=df.index)
    
    trending = adx_data['ADX'] > 25
    high_vol = vol_ratio > 1.5
    low_vol = vol_ratio < 0.7
    
    regime[trending & ~high_vol] = 'trending'
    regime[~trending & ~high_vol & ~low_vol] = 'range'
    regime[high_vol] = 'high_volatility'
    regime[low_vol] = 'low_volatility'
    
    return regime
