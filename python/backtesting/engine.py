"""
Core SAR Backtesting Engine.
Simulates the Stop-And-Reverse strategy with realistic execution.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from enum import Enum

from .indicators import (
    ema, atr, adx, market_structure, volatility_ratio, session_label
)


class DistanceMode(Enum):
    FIXED = 'fixed'
    ATR = 'atr'
    VOLATILITY = 'volatility'
    SESSION = 'session'
    SPREAD_ADJUSTED = 'spread_adjusted'


class TrailingMode(Enum):
    NONE = 'none'
    FIXED = 'fixed'
    ATR = 'atr'
    CHANDELIER = 'chandelier'
    STEP = 'step'
    VOLATILITY = 'volatility'
    HYBRID = 'hybrid'


class ExitMode(Enum):
    REVERSE_ONLY = 'reverse_only'
    TP_AND_TRAIL = 'tp_and_trail'
    TRAIL_ONLY = 'trail_only'
    WAIT_REENTRY = 'wait_reentry'


class FilterMode(Enum):
    NONE = 'none'
    ADX = 'adx'
    EMA_CROSS = 'ema_cross'
    MARKET_STRUCTURE = 'market_structure'
    ATR_EXPANSION = 'atr_expansion'
    COMPOSITE = 'composite'


class StartDirection(Enum):
    BUY = 'buy'
    SELL = 'sell'
    RANDOM = 'random'
    TREND = 'trend'


class SessionFilter(Enum):
    ALL = 'all'
    LONDON = 'london'
    NEWYORK = 'newyork'
    ASIAN = 'asian'
    LONDON_NY = 'london_ny'


@dataclass
class SARConfig:
    """Configuration for the SAR backtesting engine."""
    # Distance settings
    distance_mode: DistanceMode = DistanceMode.ATR
    fixed_distance: float = 100.0        # points
    atr_distance_mult: float = 2.0
    atr_period: int = 14
    
    # Exit mode
    exit_mode: ExitMode = ExitMode.REVERSE_ONLY
    take_profit: float = 200.0           # points
    wait_bars: int = 5
    
    # Trailing stop
    trailing_mode: TrailingMode = TrailingMode.ATR
    trail_fixed: float = 150.0           # points
    trail_atr_mult: float = 1.5
    chandelier_mult: float = 3.0
    chandelier_period: int = 22
    step_size: float = 20.0              # points
    step_distance: float = 50.0          # points
    vol_trail_mult: float = 2.0
    
    # Filters
    filter_mode: FilterMode = FilterMode.ADX
    adx_period: int = 14
    adx_threshold: float = 20.0
    ema_fast: int = 20
    ema_slow: int = 50
    atr_expansion_mult: float = 1.2
    volume_threshold: float = 1.5
    
    # Multi-timeframe
    use_htf: bool = True
    htf_ema_period: int = 50
    
    # Session filter
    session_filter: SessionFilter = SessionFilter.ALL
    
    # Start direction
    start_direction: StartDirection = StartDirection.TREND
    
    # Risk management
    risk_percent: float = 1.0
    fixed_lots: float = 0.1
    initial_capital: float = 10000.0
    
    # Protection
    max_consec_reversals: int = 5
    max_daily_loss_pct: float = 3.0
    max_spread: float = 30.0
    cooldown_bars: int = 3
    vol_shutdown_mult: float = 3.0
    equity_protection_pct: float = 10.0
    
    # Execution costs
    commission_per_lot: float = 7.0      # USD per round trip
    slippage_points: float = 2.0         # average slippage
    
    # Symbol info
    point_value: float = 0.00001         # EURUSD
    pip_value: float = 10.0              # USD per pip per standard lot
    contract_size: float = 100000.0


@dataclass
class Trade:
    """Represents a single trade."""
    entry_time: pd.Timestamp
    exit_time: Optional[pd.Timestamp] = None
    direction: int = 0                   # 1=buy, -1=sell
    entry_price: float = 0.0
    exit_price: float = 0.0
    lots: float = 0.0
    profit: float = 0.0
    commission: float = 0.0
    slippage_cost: float = 0.0
    net_profit: float = 0.0
    exit_reason: str = ''
    bars_held: int = 0
    max_favorable: float = 0.0          # max favorable excursion
    max_adverse: float = 0.0            # max adverse excursion
    regime: str = ''


@dataclass 
class BacktestResult:
    """Complete backtest results."""
    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    config: Optional[SARConfig] = None
    
    # Summary metrics
    net_profit: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    win_rate: float = 0.0
    avg_trade: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    recovery_factor: float = 0.0
    expectancy: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_consec_wins: int = 0
    max_consec_losses: int = 0
    total_reversals: int = 0
    whipsaw_losses: float = 0.0
    avg_bars_held: float = 0.0
    
    # Regime analysis
    regime_results: Dict = field(default_factory=dict)


class SARBacktester:
    """
    Stop-And-Reverse Backtesting Engine.
    
    Simulates the SAR strategy tick-by-tick on OHLC data
    with realistic execution costs.
    """
    
    def __init__(self, config: SARConfig):
        self.config = config
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.current_trade: Optional[Trade] = None
        self.direction: int = 0
        self.equity: float = config.initial_capital
        self.peak_equity: float = config.initial_capital
        self.daily_start_equity: float = config.initial_capital
        self.consec_reversals: int = 0
        self.last_reversal_bar: int = -999
        self.waiting_reentry: bool = False
        self.wait_bar_count: int = 0
        self.total_reversals: int = 0
        self.highest_since_entry: float = 0
        self.lowest_since_entry: float = 999999
        self.current_trail_level: float = 0
        self.initialized: bool = False
        
        # Precomputed indicators (set during run)
        self._atr: Optional[pd.Series] = None
        self._adx_data: Optional[pd.DataFrame] = None
        self._ema_fast: Optional[pd.Series] = None
        self._ema_slow: Optional[pd.Series] = None
        self._mkt_struct: Optional[pd.Series] = None
        self._vol_ratio: Optional[pd.Series] = None
        self._sessions: Optional[pd.Series] = None
        self._regimes: Optional[pd.Series] = None
    
    def run(self, data: pd.DataFrame) -> BacktestResult:
        """Run the backtest on provided OHLCV data."""
        self._precompute_indicators(data)
        self._reset()
        
        current_day = None
        
        for i in range(max(100, self.config.atr_period * 3), len(data)):
            row = data.iloc[i]
            dt = data.index[i]
            
            # Track equity curve
            unrealized = self._unrealized_pnl(row)
            self.equity_curve.append(self.equity + unrealized)
            
            # New day check
            day = dt.date()
            if day != current_day:
                current_day = day
                self.daily_start_equity = self.equity
                self.consec_reversals = 0
            
            # Peak equity tracking
            total_eq = self.equity + unrealized
            if total_eq > self.peak_equity:
                self.peak_equity = total_eq
            
            # Waiting for re-entry
            if self.waiting_reentry:
                self.wait_bar_count += 1
                if self.wait_bar_count < self.config.wait_bars:
                    continue
                self.waiting_reentry = False
                self.wait_bar_count = 0
            
            # Initialize first trade
            if not self.initialized:
                if self._can_trade(i, data, row):
                    direction = self._get_start_direction(i, data)
                    if direction != 0:
                        if self._check_filters(i, data, direction):
                            self._open_trade(i, data, row, direction)
                            self.initialized = True
                        elif self._check_filters(i, data, -direction):
                            # Try opposite direction
                            self._open_trade(i, data, row, -direction)
                            self.initialized = True
                continue
            
            # Check trailing stop
            if self.direction != 0 and self.config.trailing_mode != TrailingMode.NONE:
                if self._check_trailing(i, data, row):
                    self._close_trade(i, data, row, 'trailing_stop')
                    
                    if self.config.exit_mode in (ExitMode.TRAIL_ONLY, ExitMode.TP_AND_TRAIL):
                        self.waiting_reentry = True
                        self.wait_bar_count = 0
                    
                    # In all exit modes, re-initialize to find next entry
                    self.initialized = False
                    continue
            
            # Check take profit
            if self.direction != 0 and self.config.exit_mode == ExitMode.TP_AND_TRAIL:
                if self._check_take_profit(row):
                    self._close_trade(i, data, row, 'take_profit')
                    self.waiting_reentry = True
                    self.wait_bar_count = 0
                    self.initialized = False
                    continue
            
            # Check reversal level
            if self.direction != 0:
                reversal_distance = self._get_reversal_distance(i, data, row)
                
                if self.direction == 1:
                    reversal_price = self.current_trade.entry_price - reversal_distance
                    if row['low'] <= reversal_price:
                        self._execute_reversal(i, data, row, reversal_price)
                elif self.direction == -1:
                    reversal_price = self.current_trade.entry_price + reversal_distance
                    if row['high'] >= reversal_price:
                        self._execute_reversal(i, data, row, reversal_price)
            
            # Update tracking
            if self.direction != 0:
                if row['high'] > self.highest_since_entry:
                    self.highest_since_entry = row['high']
                if row['low'] < self.lowest_since_entry:
                    self.lowest_since_entry = row['low']
        
        # Close any open trade at end
        if self.current_trade is not None and self.direction != 0:
            self._close_trade(len(data) - 1, data, data.iloc[-1], 'end_of_data')
        
        return self._compile_results(data)
    
    def _precompute_indicators(self, data: pd.DataFrame):
        """Precompute all indicators for efficiency."""
        self._atr = atr(data, self.config.atr_period)
        self._adx_data = adx(data, self.config.adx_period)
        self._ema_fast = ema(data['close'], self.config.ema_fast)
        self._ema_slow = ema(data['close'], self.config.ema_slow)
        self._mkt_struct = market_structure(data)
        self._vol_ratio = volatility_ratio(data)
        self._sessions = session_label(data)
        
        if 'regime' in data.columns:
            self._regimes = data['regime']
        else:
            from .indicators import regime_detector
            self._regimes = regime_detector(data)
    
    def _reset(self):
        """Reset state for new backtest run."""
        self.trades = []
        self.equity_curve = []
        self.current_trade = None
        self.direction = 0
        self.equity = self.config.initial_capital
        self.peak_equity = self.config.initial_capital
        self.daily_start_equity = self.config.initial_capital
        self.consec_reversals = 0
        self.last_reversal_bar = -999
        self.waiting_reentry = False
        self.wait_bar_count = 0
        self.total_reversals = 0
        self.highest_since_entry = 0
        self.lowest_since_entry = 999999
        self.current_trail_level = 0
        self.initialized = False
    
    def _can_trade(self, i: int, data: pd.DataFrame, row) -> bool:
        """Check all protection rules."""
        # Spread filter
        if self.config.max_spread > 0:
            spread = row.get('spread', 0)
            if spread > self.config.max_spread:
                return False
        
        # Cooldown
        if self.config.cooldown_bars > 0:
            if i - self.last_reversal_bar < self.config.cooldown_bars:
                return False
        
        # Consecutive reversals
        if self.config.max_consec_reversals > 0:
            if self.consec_reversals >= self.config.max_consec_reversals:
                return False
        
        # Daily loss
        if self.config.max_daily_loss_pct > 0:
            loss_pct = (self.daily_start_equity - self.equity) / self.daily_start_equity * 100
            if loss_pct >= self.config.max_daily_loss_pct:
                return False
        
        # Volatility shutdown
        if self.config.vol_shutdown_mult > 0 and self._atr is not None:
            current_atr = self._atr.iloc[i]
            avg_atr = self._atr.iloc[max(0, i-50):i].mean()
            if avg_atr > 0 and current_atr > avg_atr * self.config.vol_shutdown_mult:
                return False
        
        # Equity protection
        if self.config.equity_protection_pct > 0:
            dd = (self.peak_equity - self.equity) / self.peak_equity * 100
            if dd >= self.config.equity_protection_pct:
                return False
        
        # Session filter
        if not self._check_session(i, data):
            return False
        
        return True
    
    def _check_session(self, i: int, data: pd.DataFrame) -> bool:
        """Check session filter."""
        if self.config.session_filter == SessionFilter.ALL:
            return True
        
        session = self._sessions.iloc[i]
        sf = self.config.session_filter
        
        if sf == SessionFilter.LONDON:
            return session in ('london', 'london_ny')
        elif sf == SessionFilter.NEWYORK:
            return session in ('newyork', 'london_ny')
        elif sf == SessionFilter.ASIAN:
            return session == 'asian'
        elif sf == SessionFilter.LONDON_NY:
            return session == 'london_ny'
        
        return True
    
    def _check_filters(self, i: int, data: pd.DataFrame, direction: int) -> bool:
        """Check trend filters."""
        fm = self.config.filter_mode
        
        if fm == FilterMode.NONE:
            return True
        
        if fm == FilterMode.ADX or fm == FilterMode.COMPOSITE:
            adx_val = self._adx_data['ADX'].iloc[i]
            plus_di = self._adx_data['+DI'].iloc[i]
            minus_di = self._adx_data['-DI'].iloc[i]
            
            if adx_val < self.config.adx_threshold:
                return False
            if direction > 0 and plus_di <= minus_di:
                return False
            if direction < 0 and minus_di <= plus_di:
                return False
        
        if fm == FilterMode.EMA_CROSS or fm == FilterMode.COMPOSITE:
            ema_f = self._ema_fast.iloc[i]
            ema_s = self._ema_slow.iloc[i]
            if direction > 0 and ema_f <= ema_s:
                return False
            if direction < 0 and ema_f >= ema_s:
                return False
        
        if fm == FilterMode.MARKET_STRUCTURE:
            ms = self._mkt_struct.iloc[i]
            if direction > 0 and ms <= 0:
                return False
            if direction < 0 and ms >= 0:
                return False
        
        if fm == FilterMode.ATR_EXPANSION or fm == FilterMode.COMPOSITE:
            vr = self._vol_ratio.iloc[i]
            if vr < self.config.atr_expansion_mult:
                return False
        
        # HTF filter (use slower EMA as proxy)
        if self.config.use_htf:
            htf_ema = ema(data['close'], self.config.htf_ema_period).iloc[i]
            price = data['close'].iloc[i]
            if direction > 0 and price < htf_ema:
                return False
            if direction < 0 and price > htf_ema:
                return False
        
        return True
    
    def _get_start_direction(self, i: int, data: pd.DataFrame) -> int:
        """Determine initial trade direction."""
        sd = self.config.start_direction
        
        if sd == StartDirection.BUY:
            return 1
        elif sd == StartDirection.SELL:
            return -1
        elif sd == StartDirection.RANDOM:
            return 1 if np.random.random() > 0.5 else -1
        elif sd == StartDirection.TREND:
            ema_f = self._ema_fast.iloc[i]
            ema_s = self._ema_slow.iloc[i]
            return 1 if ema_f > ema_s else -1
        
        return 1
    
    def _get_reversal_distance(self, i: int, data: pd.DataFrame, row) -> float:
        """Calculate reversal distance based on mode."""
        dm = self.config.distance_mode
        point = self.config.point_value
        
        if dm == DistanceMode.FIXED:
            return self.config.fixed_distance * point
        
        elif dm == DistanceMode.ATR:
            atr_val = self._atr.iloc[i]
            return max(atr_val * self.config.atr_distance_mult, 
                      self.config.fixed_distance * point * 0.5)
        
        elif dm == DistanceMode.VOLATILITY:
            atr_val = self._atr.iloc[i]
            vr = self._vol_ratio.iloc[i]
            return max(atr_val * self.config.atr_distance_mult * (1 + vr * 0.5),
                      self.config.fixed_distance * point * 0.5)
        
        elif dm == DistanceMode.SESSION:
            atr_val = self._atr.iloc[i]
            session = self._sessions.iloc[i]
            
            session_mult = {
                'london': 1.2,
                'london_ny': 1.3,
                'newyork': 1.0,
                'asian': 0.8,
                'other': 0.9
            }.get(session, 1.0)
            
            return max(atr_val * self.config.atr_distance_mult * session_mult,
                      self.config.fixed_distance * point * 0.5)
        
        elif dm == DistanceMode.SPREAD_ADJUSTED:
            atr_val = self._atr.iloc[i]
            spread = row.get('spread', 1.0) * point
            return max(atr_val * self.config.atr_distance_mult + spread * 2,
                      self.config.fixed_distance * point * 0.5)
        
        return self.config.fixed_distance * point
    
    def _calculate_trailing_level(self, i: int, data: pd.DataFrame, row) -> float:
        """Calculate trailing stop level."""
        tm = self.config.trailing_mode
        point = self.config.point_value
        price = row['close']
        
        if tm == TrailingMode.NONE:
            return 0
        
        if tm == TrailingMode.FIXED:
            dist = self.config.trail_fixed * point
            if self.direction > 0:
                return self.highest_since_entry - dist
            else:
                return self.lowest_since_entry + dist
        
        elif tm == TrailingMode.ATR:
            atr_val = self._atr.iloc[i]
            dist = atr_val * self.config.trail_atr_mult
            if self.direction > 0:
                return self.highest_since_entry - dist
            else:
                return self.lowest_since_entry + dist
        
        elif tm == TrailingMode.CHANDELIER:
            atr_val = self._atr.iloc[i]
            period = min(self.config.chandelier_period, i)
            if self.direction > 0:
                hh = data['high'].iloc[max(0, i-period):i+1].max()
                return hh - atr_val * self.config.chandelier_mult
            else:
                ll = data['low'].iloc[max(0, i-period):i+1].min()
                return ll + atr_val * self.config.chandelier_mult
        
        elif tm == TrailingMode.STEP:
            dist = self.config.step_distance * point
            step = self.config.step_size * point
            if self.direction > 0:
                gain = self.highest_since_entry - self.current_trade.entry_price
                steps = int(gain / step)
                return self.current_trade.entry_price + steps * step - dist
            else:
                gain = self.current_trade.entry_price - self.lowest_since_entry
                steps = int(gain / step)
                return self.current_trade.entry_price - steps * step + dist
        
        elif tm == TrailingMode.VOLATILITY:
            atr_val = self._atr.iloc[i]
            avg_atr = self._atr.iloc[max(0, i-50):i].mean()
            vol_ratio_val = atr_val / (avg_atr + 1e-10)
            dynamic_mult = self.config.vol_trail_mult * vol_ratio_val
            dynamic_mult = max(1.0, min(5.0, dynamic_mult))
            dist = atr_val * dynamic_mult
            if self.direction > 0:
                return self.highest_since_entry - dist
            else:
                return self.lowest_since_entry + dist
        
        elif tm == TrailingMode.HYBRID:
            # Best of ATR and Step
            atr_level = self._calculate_trailing_level_specific(
                TrailingMode.ATR, i, data, row)
            step_level = self._calculate_trailing_level_specific(
                TrailingMode.STEP, i, data, row)
            
            if self.direction > 0:
                return max(atr_level, step_level)
            else:
                if atr_level > 0 and step_level > 0:
                    return min(atr_level, step_level)
                return max(atr_level, step_level)
        
        return 0
    
    def _calculate_trailing_level_specific(self, mode: TrailingMode, 
                                            i: int, data: pd.DataFrame, row) -> float:
        """Calculate specific trailing mode level (for hybrid)."""
        point = self.config.point_value
        
        if mode == TrailingMode.ATR:
            atr_val = self._atr.iloc[i]
            dist = atr_val * self.config.trail_atr_mult
            if self.direction > 0:
                return self.highest_since_entry - dist
            else:
                return self.lowest_since_entry + dist
        
        elif mode == TrailingMode.STEP:
            dist = self.config.step_distance * point
            step = self.config.step_size * point
            if self.direction > 0:
                gain = self.highest_since_entry - self.current_trade.entry_price
                steps = int(gain / step) if step > 0 else 0
                return self.current_trade.entry_price + steps * step - dist
            else:
                gain = self.current_trade.entry_price - self.lowest_since_entry
                steps = int(gain / step) if step > 0 else 0
                return self.current_trade.entry_price - steps * step + dist
        
        return 0
    
    def _check_trailing(self, i: int, data: pd.DataFrame, row) -> bool:
        """Check if trailing stop is hit."""
        if self.config.trailing_mode == TrailingMode.NONE:
            return False
        
        new_level = self._calculate_trailing_level(i, data, row)
        
        # Only move trail in favorable direction
        if self.direction > 0:
            if new_level > self.current_trail_level or self.current_trail_level == 0:
                self.current_trail_level = new_level
            if self.current_trail_level > 0 and row['low'] <= self.current_trail_level:
                return True
        else:
            if new_level < self.current_trail_level or self.current_trail_level == 0:
                self.current_trail_level = new_level
            if self.current_trail_level > 0 and row['high'] >= self.current_trail_level:
                return True
        
        return False
    
    def _check_take_profit(self, row) -> bool:
        """Check if take profit is hit."""
        if self.config.take_profit <= 0:
            return False
        
        tp_dist = self.config.take_profit * self.config.point_value
        
        if self.direction > 0:
            tp_price = self.current_trade.entry_price + tp_dist
            return row['high'] >= tp_price
        else:
            tp_price = self.current_trade.entry_price - tp_dist
            return row['low'] <= tp_price
        
        return False
    
    def _open_trade(self, i: int, data: pd.DataFrame, row, direction: int):
        """Open a new trade."""
        entry_price = row['close']
        slippage = self.config.slippage_points * self.config.point_value
        
        if direction > 0:
            entry_price += slippage  # buy at slightly higher price
        else:
            entry_price -= slippage  # sell at slightly lower price
        
        # Calculate lot size
        rev_dist = self._get_reversal_distance(i, data, row)
        lots = self._calculate_lots(rev_dist)
        
        self.current_trade = Trade(
            entry_time=data.index[i],
            direction=direction,
            entry_price=entry_price,
            lots=lots,
            regime=self._regimes.iloc[i] if self._regimes is not None else ''
        )
        
        self.direction = direction
        self.highest_since_entry = entry_price
        self.lowest_since_entry = entry_price
        self.current_trail_level = 0
    
    def _close_trade(self, i: int, data: pd.DataFrame, row, reason: str):
        """Close current trade."""
        if self.current_trade is None:
            return
        
        exit_price = row['close']
        slippage = self.config.slippage_points * self.config.point_value
        
        if self.direction > 0:
            exit_price -= slippage
        else:
            exit_price += slippage
        
        self.current_trade.exit_time = data.index[i]
        self.current_trade.exit_price = exit_price
        self.current_trade.exit_reason = reason
        
        # Calculate P&L
        if self.direction > 0:
            price_diff = exit_price - self.current_trade.entry_price
        else:
            price_diff = self.current_trade.entry_price - exit_price
        
        gross_profit = price_diff * self.current_trade.lots * self.config.contract_size
        commission = self.config.commission_per_lot * self.current_trade.lots
        slippage_cost = slippage * 2 * self.current_trade.lots * self.config.contract_size
        
        self.current_trade.profit = gross_profit
        self.current_trade.commission = commission
        self.current_trade.slippage_cost = slippage_cost
        self.current_trade.net_profit = gross_profit - commission
        
        # MFE/MAE
        if self.direction > 0:
            self.current_trade.max_favorable = (self.highest_since_entry - self.current_trade.entry_price) * self.current_trade.lots * self.config.contract_size
            self.current_trade.max_adverse = (self.current_trade.entry_price - self.lowest_since_entry) * self.current_trade.lots * self.config.contract_size
        else:
            self.current_trade.max_favorable = (self.current_trade.entry_price - self.lowest_since_entry) * self.current_trade.lots * self.config.contract_size
            self.current_trade.max_adverse = (self.highest_since_entry - self.current_trade.entry_price) * self.current_trade.lots * self.config.contract_size
        
        # Bars held
        entry_idx = data.index.get_loc(self.current_trade.entry_time)
        self.current_trade.bars_held = i - entry_idx
        
        self.equity += self.current_trade.net_profit
        self.trades.append(self.current_trade)
        
        self.current_trade = None
        self.direction = 0
    
    def _execute_reversal(self, i: int, data: pd.DataFrame, row, reversal_price: float):
        """Execute a stop-and-reverse."""
        # Check if can trade
        if not self._can_trade(i, data, row):
            self._close_trade(i, data, row, 'protection_shutdown')
            self.initialized = False
            return
        
        old_direction = self.direction
        new_direction = -old_direction
        
        # Check filter for new direction
        if not self._check_filters(i, data, new_direction):
            if self.config.exit_mode == ExitMode.WAIT_REENTRY:
                self._close_trade(i, data, row, 'filter_rejected')
                self.waiting_reentry = True
                self.wait_bar_count = 0
                self.initialized = False
                return
            elif self.config.exit_mode == ExitMode.REVERSE_ONLY:
                # In reverse-only mode, close and re-init
                self._close_trade(i, data, row, 'filter_rejected')
                self.initialized = False
                return
        
        # Close current trade at reversal price
        self._close_trade(i, data, row, 'reversal')
        
        self.total_reversals += 1
        self.consec_reversals += 1
        self.last_reversal_bar = i
        
        # Reset consecutive reversals on profitable trade
        if len(self.trades) > 0 and self.trades[-1].net_profit > 0:
            self.consec_reversals = 0
        
        # Open new trade in opposite direction
        self._open_trade(i, data, row, new_direction)
    
    def _calculate_lots(self, stop_distance: float) -> float:
        """Calculate position size based on risk."""
        if self.config.risk_percent <= 0:
            return self.config.fixed_lots
        
        risk_amount = self.equity * self.config.risk_percent / 100.0
        
        if stop_distance <= 0:
            return self.config.fixed_lots
        
        point_value = self.config.pip_value * self.config.point_value / 0.0001
        lots = risk_amount / (stop_distance / self.config.point_value * point_value)
        
        lots = max(0.01, min(lots, 10.0))
        lots = round(lots, 2)
        
        return lots
    
    def _unrealized_pnl(self, row) -> float:
        """Calculate unrealized P&L for current trade."""
        if self.current_trade is None or self.direction == 0:
            return 0
        
        if self.direction > 0:
            diff = row['close'] - self.current_trade.entry_price
        else:
            diff = self.current_trade.entry_price - row['close']
        
        return diff * self.current_trade.lots * self.config.contract_size
    
    def _compile_results(self, data: pd.DataFrame) -> BacktestResult:
        """Compile all results into BacktestResult."""
        result = BacktestResult()
        result.trades = self.trades
        result.config = self.config
        result.total_reversals = self.total_reversals
        
        if not self.trades:
            result.equity_curve = pd.Series(self.equity_curve, 
                                            index=data.index[-len(self.equity_curve):])
            return result
        
        # Build equity curve
        result.equity_curve = pd.Series(self.equity_curve,
                                         index=data.index[-len(self.equity_curve):])
        
        # Basic metrics
        profits = [t.net_profit for t in self.trades]
        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p <= 0]
        
        result.total_trades = len(self.trades)
        result.net_profit = sum(profits)
        result.gross_profit = sum(wins) if wins else 0
        result.gross_loss = sum(losses) if losses else 0
        result.profit_factor = (result.gross_profit / abs(result.gross_loss)) if result.gross_loss != 0 else float('inf')
        result.win_rate = len(wins) / len(profits) * 100 if profits else 0
        result.avg_trade = np.mean(profits) if profits else 0
        result.avg_win = np.mean(wins) if wins else 0
        result.avg_loss = np.mean(losses) if losses else 0
        
        # Drawdown
        eq = pd.Series(self.equity_curve)
        peak = eq.cummax()
        dd = eq - peak
        result.max_drawdown = abs(dd.min())
        result.max_drawdown_pct = (result.max_drawdown / peak[dd.idxmin()]) * 100 if dd.min() < 0 else 0
        
        # Sharpe ratio (annualized)
        if len(profits) > 1:
            daily_returns = pd.Series(profits)
            result.sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() > 0 else 0
        
        # Recovery factor
        result.recovery_factor = result.net_profit / result.max_drawdown if result.max_drawdown > 0 else float('inf')
        
        # Expectancy
        if result.total_trades > 0:
            win_pct = len(wins) / result.total_trades
            loss_pct = len(losses) / result.total_trades
            avg_w = np.mean(wins) if wins else 0
            avg_l = abs(np.mean(losses)) if losses else 0
            result.expectancy = win_pct * avg_w - loss_pct * avg_l
        
        # Consecutive wins/losses
        streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        for p in profits:
            if p > 0:
                if streak > 0:
                    streak += 1
                else:
                    streak = 1
                max_win_streak = max(max_win_streak, streak)
            else:
                if streak < 0:
                    streak -= 1
                else:
                    streak = -1
                max_loss_streak = max(max_loss_streak, abs(streak))
        
        result.max_consec_wins = max_win_streak
        result.max_consec_losses = max_loss_streak
        
        # Whipsaw analysis
        reversal_trades = [t for t in self.trades if t.exit_reason == 'reversal']
        whipsaw_trades = [t for t in reversal_trades if t.net_profit < 0]
        result.whipsaw_losses = sum(t.net_profit for t in whipsaw_trades)
        
        # Average bars held
        result.avg_bars_held = np.mean([t.bars_held for t in self.trades])
        
        # Regime analysis
        result.regime_results = self._analyze_regimes()
        
        return result
    
    def _analyze_regimes(self) -> Dict:
        """Analyze performance by market regime."""
        regimes = {}
        for trade in self.trades:
            regime = trade.regime if trade.regime else 'unknown'
            if regime not in regimes:
                regimes[regime] = {
                    'trades': 0,
                    'wins': 0,
                    'net_profit': 0,
                    'gross_profit': 0,
                    'gross_loss': 0,
                    'avg_trade': 0
                }
            
            regimes[regime]['trades'] += 1
            regimes[regime]['net_profit'] += trade.net_profit
            if trade.net_profit > 0:
                regimes[regime]['wins'] += 1
                regimes[regime]['gross_profit'] += trade.net_profit
            else:
                regimes[regime]['gross_loss'] += trade.net_profit
        
        for regime in regimes:
            r = regimes[regime]
            r['win_rate'] = r['wins'] / r['trades'] * 100 if r['trades'] > 0 else 0
            r['avg_trade'] = r['net_profit'] / r['trades'] if r['trades'] > 0 else 0
            r['profit_factor'] = (r['gross_profit'] / abs(r['gross_loss'])) if r['gross_loss'] != 0 else float('inf')
        
        return regimes
