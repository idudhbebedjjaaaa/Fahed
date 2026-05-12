"""
SAR Strategy - Fast Vectorized Backtesting on REAL Data
Optimized for speed: uses numpy arrays, minimal Python loops
"""
import pandas as pd
import numpy as np
import time
import os
from typing import Optional

os.chdir(os.path.dirname(os.path.abspath(__file__)))


# ============================================================
# DATA LOADING
# ============================================================

def load_xauusd_m15() -> pd.DataFrame:
    df = pd.read_csv("data/XAUUSD_M15.csv")
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    df.sort_index(inplace=True)
    return df

def load_xauusd_h1() -> pd.DataFrame:
    df = pd.read_csv("data/XAUUSD_H1.csv")
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    df.sort_index(inplace=True)
    return df

def load_eurusd_m1() -> pd.DataFrame:
    df = pd.read_csv("data/EURUSD_M1.csv", sep='\t')
    df.columns = ['date', 'time', 'open', 'high', 'low', 'close', 'tick_volume', 'volume', 'spread']
    df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'], format='%Y.%m.%d %H:%M:%S')
    df.set_index('datetime', inplace=True)
    df.sort_index(inplace=True)
    return df

def resample(df, freq):
    return df.resample(freq).agg({
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'tick_volume': 'sum', 'spread': 'mean'
    }).dropna()


# ============================================================
# INDICATORS (vectorized)
# ============================================================

def atr(high, low, close, period=14):
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - np.roll(close, 1)),
                               np.abs(low - np.roll(close, 1))))
    tr[0] = high[0] - low[0]
    # EMA-style ATR
    result = np.zeros(len(tr))
    result[:period] = np.nan
    result[period-1] = np.mean(tr[:period])
    mult = 2.0 / (period + 1)
    for i in range(period, len(tr)):
        result[i] = tr[i] * mult + result[i-1] * (1 - mult)
    return result

def adx(high, low, close, period=14):
    up = np.diff(high, prepend=high[0])
    dn = -np.diff(low, prepend=low[0])

    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)

    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - np.roll(close, 1)),
                               np.abs(low - np.roll(close, 1))))
    tr[0] = high[0] - low[0]

    # Smoothed
    def ema_arr(arr, n):
        out = np.zeros(len(arr))
        out[:n] = np.nan
        out[n-1] = np.mean(arr[:n])
        m = 2.0/(n+1)
        for i in range(n, len(arr)):
            out[i] = arr[i]*m + out[i-1]*(1-m)
        return out

    atr_s = ema_arr(tr, period)
    pdm_s = ema_arr(plus_dm, period)
    mdm_s = ema_arr(minus_dm, period)

    plus_di = 100 * pdm_s / (atr_s + 1e-10)
    minus_di = 100 * mdm_s / (atr_s + 1e-10)
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
    adx_val = ema_arr(dx, period)

    return adx_val, plus_di, minus_di

def ema(arr, period):
    out = np.zeros(len(arr))
    out[:period] = np.nan
    out[period-1] = np.mean(arr[:period])
    m = 2.0/(period+1)
    for i in range(period, len(arr)):
        out[i] = arr[i]*m + out[i-1]*(1-m)
    return out


# ============================================================
# FAST BACKTEST ENGINE
# ============================================================

def backtest(close, high, low, spreads, hours, atr_vals, adx_vals, plus_di, minus_di,
             ema_f, ema_s, htf_ema,
             # Parameters:
             dist_mode, dist_mult, trail_mode, trail_mult,
             filter_mode, adx_thresh, session, cooldown,
             use_htf, risk_pct, max_reversals,
             # Contract specs:
             point_value, initial_balance, spread_mult,
             commission_per_lot, slippage):
    """
    Fast SAR backtest. All inputs are numpy arrays.
    Returns: (net_profit, total_trades, win_rate, profit_factor, max_dd_pct, sharpe, trades_list)
    """
    n = len(close)
    balance = initial_balance
    peak_balance = initial_balance

    position = 0  # 0=flat, 1=long, -1=short
    entry_price = 0.0
    pending_price = 0.0
    highest = 0.0
    lowest = 1e10
    trail_level = 0.0
    consec_rev = 0
    last_rev_i = -100
    lots = 0.0
    max_dd = 0.0
    daily_loss = 0.0
    current_day = -1

    profits = []
    n_wins = 0
    gross_profit = 0.0
    gross_loss = 0.0

    start = 60  # warmup

    for i in range(start, n):
        # Daily reset
        day = i // 96  # approximate day boundary for M15
        if day != current_day:
            current_day = day
            daily_loss = 0.0

        # Skip if indicators not ready
        if np.isnan(atr_vals[i]) or atr_vals[i] <= 0:
            continue

        # Session filter
        if session == 1:  # london
            if not (8 <= hours[i] < 17):
                continue
        elif session == 2:  # newyork
            if not (13 <= hours[i] < 22):
                continue
        elif session == 3:  # london_ny overlap
            if not (13 <= hours[i] < 17):
                continue

        # Spread cost
        spread_cost = spreads[i] * spread_mult

        if position == 0:
            # Check daily loss limit
            if daily_loss >= balance * 0.03:
                continue

            # Determine direction from EMA
            if np.isnan(ema_f[i]) or np.isnan(ema_s[i]):
                continue
            direction = 1 if ema_f[i] > ema_s[i] else -1

            # Apply filter
            if not _passes_filter(i, direction, filter_mode, adx_thresh,
                                  adx_vals, plus_di, minus_di, ema_f, ema_s,
                                  htf_ema, use_htf):
                continue

            # Calculate distance
            distance = _get_distance(i, dist_mode, dist_mult, atr_vals)
            if distance <= 0:
                continue

            # Lot size
            lots = _calc_lots(balance, risk_pct, distance, point_value)

            # Open
            position = direction
            entry_price = close[i] + (spread_cost if direction > 0 else 0)
            last_rev_i = i
            consec_rev = 0
            if direction > 0:
                highest = close[i]
                lowest = 1e10
            else:
                lowest = close[i]
                highest = 0.0
            trail_level = 0.0
            pending_price = entry_price + (-distance if direction > 0 else distance)
            continue

        # Have position - check exits
        if position > 0:
            highest = max(highest, high[i])
        else:
            lowest = min(lowest, low[i])

        # Trailing stop check
        exit_price = 0.0
        exit_type = 0  # 0=none, 1=trail, 2=reversal

        if trail_mode > 0:
            tl = _get_trail(i, trail_mode, trail_mult, atr_vals, position, highest, lowest, trail_level)
            if tl > 0:
                trail_level = tl
                if position > 0 and low[i] <= trail_level:
                    exit_price = trail_level
                    exit_type = 1
                elif position < 0 and high[i] >= trail_level:
                    exit_price = trail_level
                    exit_type = 1

        # Reversal check
        if exit_type == 0:
            if position > 0 and low[i] <= pending_price:
                exit_price = pending_price
                exit_type = 2
            elif position < 0 and high[i] >= pending_price:
                exit_price = pending_price
                exit_type = 2

        if exit_type > 0:
            # Calculate profit
            if position > 0:
                pnl = (exit_price - entry_price - spread_cost - slippage) * lots * point_value
            else:
                pnl = (entry_price - exit_price - spread_cost - slippage) * lots * point_value
            pnl -= commission_per_lot * lots

            profits.append(pnl)
            balance += pnl
            if pnl > 0:
                n_wins += 1
                gross_profit += pnl
            else:
                gross_loss += abs(pnl)
                daily_loss += abs(pnl)

            # Drawdown
            if balance > peak_balance:
                peak_balance = balance
            dd = (peak_balance - balance) / peak_balance * 100
            if dd > max_dd:
                max_dd = dd

            if balance <= initial_balance * 0.5:  # Stop if lost 50%
                break

            # Reversal: open opposite
            if exit_type == 2 and consec_rev < max_reversals and (i - last_rev_i) >= cooldown:
                new_dir = -position
                if _passes_filter(i, new_dir, filter_mode, adx_thresh,
                                  adx_vals, plus_di, minus_di, ema_f, ema_s,
                                  htf_ema, use_htf):
                    position = new_dir
                    entry_price = exit_price + (spread_cost if new_dir > 0 else 0)
                    last_rev_i = i
                    consec_rev += 1
                    distance = _get_distance(i, dist_mode, dist_mult, atr_vals)
                    lots = _calc_lots(balance, risk_pct, distance, point_value)
                    pending_price = entry_price + (-distance if new_dir > 0 else distance)
                    if new_dir > 0:
                        highest = close[i]
                    else:
                        lowest = close[i]
                    trail_level = 0.0
                else:
                    position = 0
            else:
                position = 0

    # Metrics
    total_trades = len(profits)
    if total_trades == 0:
        return 0, 0, 0, 0, 0, 0, []

    net_profit = sum(profits)
    win_rate = n_wins / total_trades * 100
    pf = gross_profit / (gross_loss + 1e-10)
    avg_trade = net_profit / total_trades

    # Sharpe
    if total_trades > 1:
        ret_arr = np.array(profits) / initial_balance
        sharpe = np.mean(ret_arr) / (np.std(ret_arr) + 1e-10) * np.sqrt(min(total_trades, 252))
    else:
        sharpe = 0

    return net_profit, total_trades, win_rate, pf, max_dd, sharpe, profits


def _get_distance(i, mode, mult, atr_vals):
    if mode == 0:  # atr
        return atr_vals[i] * mult
    elif mode == 1:  # volatility adaptive
        if i >= 50:
            avg = np.mean(atr_vals[max(0,i-50):i])
            if avg > 0:
                ratio = atr_vals[i] / avg
                return atr_vals[i] * mult * max(0.8, min(ratio, 2.0))
        return atr_vals[i] * mult
    return atr_vals[i] * mult

def _get_trail(i, mode, mult, atr_vals, direction, highest, lowest, prev_level):
    if mode == 1:  # atr trail
        dist = atr_vals[i] * mult
    elif mode == 2:  # volatility trail
        if i >= 50:
            avg = np.mean(atr_vals[max(0,i-50):i])
            ratio = atr_vals[i] / (avg + 1e-10)
            dist = atr_vals[i] * mult * max(0.8, min(ratio, 2.5))
        else:
            dist = atr_vals[i] * mult
    else:
        return 0.0

    if direction > 0:
        new_level = highest - dist
        return max(new_level, prev_level) if prev_level > 0 else new_level
    else:
        new_level = lowest + dist
        return min(new_level, prev_level) if prev_level > 0 else new_level

def _passes_filter(i, direction, filter_mode, adx_thresh,
                   adx_vals, plus_di, minus_di, ema_f, ema_s, htf_ema, use_htf):
    if filter_mode == 0:  # none
        return True
    if filter_mode == 1:  # adx
        if np.isnan(adx_vals[i]) or adx_vals[i] < adx_thresh:
            return False
        if direction > 0 and plus_di[i] <= minus_di[i]:
            return False
        if direction < 0 and minus_di[i] <= plus_di[i]:
            return False
    elif filter_mode == 2:  # ema
        if np.isnan(ema_f[i]) or np.isnan(ema_s[i]):
            return False
        if direction > 0 and ema_f[i] <= ema_s[i]:
            return False
        if direction < 0 and ema_f[i] >= ema_s[i]:
            return False
    elif filter_mode == 3:  # composite (adx + ema)
        if np.isnan(adx_vals[i]) or adx_vals[i] < adx_thresh:
            return False
        if direction > 0 and plus_di[i] <= minus_di[i]:
            return False
        if direction < 0 and minus_di[i] <= plus_di[i]:
            return False
        if np.isnan(ema_f[i]) or np.isnan(ema_s[i]):
            return False
        if direction > 0 and ema_f[i] <= ema_s[i]:
            return False
        if direction < 0 and ema_f[i] >= ema_s[i]:
            return False

    # HTF filter
    if use_htf and htf_ema is not None:
        if not np.isnan(htf_ema[i]):
            if direction > 0 and close_arr_global[i] < htf_ema[i]:
                return False
            if direction < 0 and close_arr_global[i] > htf_ema[i]:
                return False
    return True

def _calc_lots(balance, risk_pct, distance, point_value):
    if distance <= 0 or balance <= 0:
        return 0.01
    risk = balance * risk_pct / 100.0
    value = distance * point_value
    if value <= 0:
        return 0.01
    lots = risk / value
    return max(0.01, min(lots, 5.0))


# Global for filter access
close_arr_global = None

# ============================================================
# OPTIMIZATION
# ============================================================

def run_optimization(symbol, df, df_htf, point_value, spread_mult, initial_balance=10000):
    global close_arr_global

    print(f"\n{'='*70}")
    print(f"  SAR OPTIMIZATION - {symbol} - REAL DATA")
    print(f"  Period: {df.index[0]} to {df.index[-1]} ({len(df)} bars)")
    print(f"{'='*70}\n")

    # Prepare arrays
    close = df['close'].values.astype(np.float64)
    high = df['high'].values.astype(np.float64)
    low = df['low'].values.astype(np.float64)
    spreads = df['spread'].values.astype(np.float64)
    hours = np.array([t.hour for t in df.index])

    close_arr_global = close

    # Indicators
    atr_vals = atr(high, low, close, 14)
    adx_vals, plus_di_vals, minus_di_vals = adx(high, low, close, 14)
    ema_f = ema(close, 20)
    ema_s = ema(close, 50)

    # HTF EMA
    htf_ema_aligned = None
    if df_htf is not None and len(df_htf) > 60:
        htf_ema_raw = ema(df_htf['close'].values, 50)
        htf_ema_series = pd.Series(htf_ema_raw, index=df_htf.index)
        htf_ema_aligned = htf_ema_series.reindex(df.index, method='ffill').values

    # Parameter grid (focused)
    dist_modes = [0, 1]          # 0=atr, 1=volatility
    dist_mults = [1.5, 2.0, 2.5, 3.0, 3.5]
    trail_modes = [1, 2]         # 1=atr, 2=volatility
    trail_mults = [1.5, 2.0, 2.5, 3.0]
    filter_modes = [1, 2, 3]     # 1=adx, 2=ema, 3=composite
    adx_thresholds = [20, 25, 30]
    sessions = [0, 3]            # 0=all, 3=london_ny
    cooldowns = [2, 3]

    total = (len(dist_modes) * len(dist_mults) * len(trail_modes) * len(trail_mults) *
             len(filter_modes) * len(adx_thresholds) * len(sessions) * len(cooldowns))
    print(f"  Grid: {total} combinations")

    results = []
    t0 = time.time()
    count = 0

    for dm in dist_modes:
        for dmult in dist_mults:
            for tm in trail_modes:
                for tmult in trail_mults:
                    for fm in filter_modes:
                        for at in adx_thresholds:
                            for sess in sessions:
                                for cool in cooldowns:
                                    np_, nt, wr, pf, dd, sh, trades = backtest(
                                        close, high, low, spreads, hours,
                                        atr_vals, adx_vals, plus_di_vals, minus_di_vals,
                                        ema_f, ema_s, htf_ema_aligned,
                                        dm, dmult, tm, tmult, fm, at, sess, cool,
                                        True, 1.0, 5,
                                        point_value, initial_balance, spread_mult,
                                        7.0, 0.0  # commission, slippage in price
                                    )
                                    # Score
                                    score = 0
                                    if np_ > 0 and dd < 40 and nt >= 20:
                                        score = (sh * 0.35 + pf * 0.2 +
                                                 min(np_/initial_balance, 3) * 0.2 +
                                                 (wr/100) * 0.15 +
                                                 max(0, (30-dd)/30) * 0.1)
                                    results.append({
                                        'profit': np_, 'trades': nt, 'wr': wr,
                                        'pf': pf, 'dd': dd, 'sharpe': sh, 'score': score,
                                        'dm': dm, 'dmult': dmult, 'tm': tm, 'tmult': tmult,
                                        'fm': fm, 'adx_th': at, 'sess': sess, 'cool': cool,
                                        'profits_list': trades
                                    })
                                    count += 1
                                    if count % 200 == 0:
                                        elapsed = time.time() - t0
                                        eta = (elapsed / count) * (total - count)
                                        print(f"    {count}/{total} ({count/total*100:.0f}%) - "
                                              f"ETA: {eta:.0f}s")

    elapsed = time.time() - t0
    print(f"\n  Completed in {elapsed:.1f}s")

    # Sort
    results.sort(key=lambda x: x['score'], reverse=True)

    # Print top 10
    dm_names = {0: 'ATR', 1: 'VOL'}
    tm_names = {1: 'ATR', 2: 'VOL'}
    fm_names = {0: 'None', 1: 'ADX', 2: 'EMA', 3: 'COMP'}
    sess_names = {0: 'ALL', 1: 'LON', 2: 'NY', 3: 'LN_NY'}

    print(f"\n  {'#':<3} {'Score':<7} {'Profit':<11} {'Sharpe':<7} {'PF':<6} {'DD%':<6} {'WR%':<6} {'Trd':<5} {'Dist':<8} {'Trail':<8} {'Filter':<6} {'Sess':<6} {'Cool':<4}")
    print("  " + "-"*90)

    for idx, r in enumerate(results[:15]):
        print(f"  {idx+1:<3} {r['score']:<7.3f} ${r['profit']:<10.0f} {r['sharpe']:<7.2f} "
              f"{r['pf']:<6.2f} {r['dd']:<6.1f} {r['wr']:<6.1f} {r['trades']:<5} "
              f"{dm_names[r['dm']]}x{r['dmult']:<4} {tm_names[r['tm']]}x{r['tmult']:<4} "
              f"{fm_names[r['fm']]:<6} {sess_names[r['sess']]:<6} {r['cool']}")

    return results


def walk_forward(symbol, df, df_htf, best_params, point_value, spread_mult, initial_balance=10000, n_folds=5):
    global close_arr_global

    print(f"\n  Walk-Forward Analysis ({n_folds} folds):")
    n = len(df)
    fold_size = n // n_folds
    fold_results = []

    for fold in range(n_folds):
        start = fold * fold_size
        end = min((fold + 1) * fold_size, n)
        df_fold = df.iloc[start:end]

        close = df_fold['close'].values.astype(np.float64)
        high = df_fold['high'].values.astype(np.float64)
        low = df_fold['low'].values.astype(np.float64)
        spreads = df_fold['spread'].values.astype(np.float64)
        hours = np.array([t.hour for t in df_fold.index])
        close_arr_global = close

        atr_vals = atr(high, low, close, 14)
        adx_vals, plus_di_vals, minus_di_vals = adx(high, low, close, 14)
        ema_f = ema(close, 20)
        ema_s = ema(close, 50)

        htf_ema_aligned = None
        if df_htf is not None and len(df_htf) > 60:
            mask = (df_htf.index >= df_fold.index[0]) & (df_htf.index <= df_fold.index[-1])
            df_htf_fold = df_htf[mask]
            if len(df_htf_fold) > 60:
                htf_e = ema(df_htf_fold['close'].values, 50)
                htf_s = pd.Series(htf_e, index=df_htf_fold.index)
                htf_ema_aligned = htf_s.reindex(df_fold.index, method='ffill').values

        p = best_params
        np_, nt, wr, pf, dd, sh, _ = backtest(
            close, high, low, spreads, hours,
            atr_vals, adx_vals, plus_di_vals, minus_di_vals,
            ema_f, ema_s, htf_ema_aligned,
            p['dm'], p['dmult'], p['tm'], p['tmult'],
            p['fm'], p['adx_th'], p['sess'], p['cool'],
            True, 1.0, 5,
            point_value, initial_balance, spread_mult, 7.0, 0.0
        )
        fold_results.append({'profit': np_, 'trades': nt, 'sharpe': sh, 'pf': pf, 'dd': dd})
        print(f"    Fold {fold+1}: Profit=${np_:>8.0f} | Sharpe={sh:>5.2f} | PF={pf:>5.2f} | DD={dd:>5.1f}% | Trades={nt}")

    profitable = sum(1 for r in fold_results if r['profit'] > 0)
    avg_profit = np.mean([r['profit'] for r in fold_results])
    avg_sharpe = np.mean([r['sharpe'] for r in fold_results])
    robust = profitable >= 3

    print(f"\n    Avg Profit: ${avg_profit:.0f} | Avg Sharpe: {avg_sharpe:.2f}")
    print(f"    Profitable Folds: {profitable}/{n_folds} → {'ROBUST' if robust else 'NOT ROBUST'}")
    return robust, fold_results


def monte_carlo_sim(profits_list, initial_balance, n_sims=1000):
    if not profits_list:
        return {}
    profits = np.array(profits_list)
    final_balances = []
    max_dds = []

    for _ in range(n_sims):
        shuffled = np.random.permutation(profits)
        equity = initial_balance + np.cumsum(shuffled)
        peak = np.maximum.accumulate(np.insert(equity, 0, initial_balance))
        dd = (peak[1:] - equity) / peak[1:] * 100
        final_balances.append(equity[-1])
        max_dds.append(dd.max())

    return {
        'median_profit': np.median(np.array(final_balances) - initial_balance),
        'p5': np.percentile(np.array(final_balances) - initial_balance, 5),
        'p95': np.percentile(np.array(final_balances) - initial_balance, 95),
        'worst_dd_95': np.percentile(max_dds, 95)
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("  SAR STOP-AND-REVERSE - REAL DATA ANALYSIS")
    print("  Backtesting on actual market data from MT5")
    print("=" * 70)

    initial_balance = 10000.0

    # ===== XAUUSD =====
    print("\n>>> Loading XAUUSD M15 + H1...")
    xau_m15 = load_xauusd_m15()
    xau_h1 = load_xauusd_h1()
    xau_h1 = xau_h1[xau_h1.index >= xau_m15.index[0]]
    print(f"    M15: {len(xau_m15)} bars | {xau_m15.index[0]} → {xau_m15.index[-1]}")
    print(f"    H1:  {len(xau_h1)} bars")
    print(f"    Price range: ${xau_m15['close'].min():.0f} - ${xau_m15['close'].max():.0f}")

    # XAUUSD: 1 lot = 100 oz. If price moves $1, profit = $100 per lot.
    # Spread in data is in points (e.g., 10 = 10 points = $0.10)
    # spread_mult converts spread column to price units
    xau_point_value = 100.0  # $100 per $1 move per lot
    xau_spread_mult = 0.01   # spread=10 means $0.10

    xau_results = run_optimization("XAUUSD", xau_m15, xau_h1, xau_point_value,
                                   xau_spread_mult, initial_balance)

    xau_best = xau_results[0]
    print(f"\n  Best XAUUSD Config:")
    dm_n = {0:'ATR', 1:'VOL'}
    tm_n = {1:'ATR', 2:'VOL'}
    fm_n = {0:'None', 1:'ADX', 2:'EMA', 3:'COMPOSITE'}
    ss_n = {0:'ALL', 1:'LONDON', 2:'NY', 3:'LONDON_NY'}
    print(f"    Distance: {dm_n[xau_best['dm']]} x {xau_best['dmult']}")
    print(f"    Trailing: {tm_n[xau_best['tm']]} x {xau_best['tmult']}")
    print(f"    Filter:   {fm_n[xau_best['fm']]} (ADX>{xau_best['adx_th']})")
    print(f"    Session:  {ss_n[xau_best['sess']]}")
    print(f"    Cooldown: {xau_best['cool']} bars")

    # Walk Forward
    xau_robust, xau_wf = walk_forward("XAUUSD", xau_m15, xau_h1, xau_best,
                                       xau_point_value, xau_spread_mult, initial_balance)

    # Monte Carlo
    if xau_best['profits_list']:
        xau_mc = monte_carlo_sim(xau_best['profits_list'], initial_balance)
        print(f"\n  Monte Carlo (1000 sims):")
        print(f"    Median Profit: ${xau_mc['median_profit']:.0f}")
        print(f"    5th %ile: ${xau_mc['p5']:.0f}")
        print(f"    95th %ile: ${xau_mc['p95']:.0f}")
        print(f"    Worst DD (95%): {xau_mc['worst_dd_95']:.1f}%")

    # ===== EURUSD =====
    print("\n\n>>> Loading EURUSD M1 → resampling to M15 + H1...")
    eur_m1 = load_eurusd_m1()
    eur_m15 = resample(eur_m1, '15min')
    eur_h1 = resample(eur_m1, '1h')
    print(f"    M1:  {len(eur_m1)} bars | {eur_m1.index[0]} → {eur_m1.index[-1]}")
    print(f"    M15: {len(eur_m15)} bars")
    print(f"    H1:  {len(eur_h1)} bars")
    print(f"    Price range: {eur_m15['close'].min():.5f} - {eur_m15['close'].max():.5f}")

    # EURUSD: 1 lot = 100,000 units. If price moves 0.0001 (1 pip), profit = $10 per lot.
    # So per 1.0 price move per lot = $100,000
    # Spread in data: e.g., 5 = 5 points = 0.00005
    eur_point_value = 100000.0  # $100,000 per 1.0 move per lot
    eur_spread_mult = 0.00001   # spread=5 means 0.00005

    eur_results = run_optimization("EURUSD", eur_m15, eur_h1, eur_point_value,
                                   eur_spread_mult, initial_balance)

    eur_best = eur_results[0]
    print(f"\n  Best EURUSD Config:")
    print(f"    Distance: {dm_n[eur_best['dm']]} x {eur_best['dmult']}")
    print(f"    Trailing: {tm_n[eur_best['tm']]} x {eur_best['tmult']}")
    print(f"    Filter:   {fm_n[eur_best['fm']]} (ADX>{eur_best['adx_th']})")
    print(f"    Session:  {ss_n[eur_best['sess']]}")
    print(f"    Cooldown: {eur_best['cool']} bars")

    # Walk Forward
    eur_robust, eur_wf = walk_forward("EURUSD", eur_m15, eur_h1, eur_best,
                                       eur_point_value, eur_spread_mult, initial_balance)

    # Monte Carlo
    if eur_best['profits_list']:
        eur_mc = monte_carlo_sim(eur_best['profits_list'], initial_balance)
        print(f"\n  Monte Carlo (1000 sims):")
        print(f"    Median Profit: ${eur_mc['median_profit']:.0f}")
        print(f"    5th %ile: ${eur_mc['p5']:.0f}")
        print(f"    95th %ile: ${eur_mc['p95']:.0f}")
        print(f"    Worst DD (95%): {eur_mc['worst_dd_95']:.1f}%")

    # ===== FINAL REPORT =====
    print("\n\n" + "=" * 70)
    print("  FINAL RESULTS - REAL DATA")
    print("=" * 70)
    print(f"\n  {'Metric':<25} {'XAUUSD':<20} {'EURUSD':<20}")
    print("  " + "-" * 60)
    print(f"  {'Net Profit':<25} ${xau_best['profit']:<19.0f} ${eur_best['profit']:<19.0f}")
    print(f"  {'Total Trades':<25} {xau_best['trades']:<20} {eur_best['trades']:<20}")
    print(f"  {'Win Rate':<25} {xau_best['wr']:<19.1f}% {eur_best['wr']:<19.1f}%")
    print(f"  {'Profit Factor':<25} {xau_best['pf']:<20.2f} {eur_best['pf']:<20.2f}")
    print(f"  {'Sharpe Ratio':<25} {xau_best['sharpe']:<20.2f} {eur_best['sharpe']:<20.2f}")
    print(f"  {'Max Drawdown':<25} {xau_best['dd']:<19.1f}% {eur_best['dd']:<19.1f}%")
    print(f"  {'Walk Forward':<25} {'ROBUST' if xau_robust else 'NOT ROBUST':<20} {'ROBUST' if eur_robust else 'NOT ROBUST':<20}")
    print(f"  {'Score':<25} {xau_best['score']:<20.3f} {eur_best['score']:<20.3f}")

    print(f"\n  XAUUSD Best: dist={dm_n[xau_best['dm']]}x{xau_best['dmult']}, "
          f"trail={tm_n[xau_best['tm']]}x{xau_best['tmult']}, "
          f"filter={fm_n[xau_best['fm']]}, session={ss_n[xau_best['sess']]}")
    print(f"  EURUSD Best: dist={dm_n[eur_best['dm']]}x{eur_best['dmult']}, "
          f"trail={tm_n[eur_best['tm']]}x{eur_best['tmult']}, "
          f"filter={fm_n[eur_best['fm']]}, session={ss_n[eur_best['sess']]}")

    # Save
    with open('results/RESULTS.txt', 'w') as f:
        f.write("SAR REAL DATA RESULTS\n" + "="*60 + "\n\n")
        f.write(f"XAUUSD:\n")
        f.write(f"  Profit: ${xau_best['profit']:.0f} | Trades: {xau_best['trades']} | "
                f"WR: {xau_best['wr']:.1f}% | PF: {xau_best['pf']:.2f} | "
                f"Sharpe: {xau_best['sharpe']:.2f} | DD: {xau_best['dd']:.1f}%\n")
        f.write(f"  Walk Forward: {'ROBUST' if xau_robust else 'NOT ROBUST'}\n")
        f.write(f"  Config: dist={dm_n[xau_best['dm']]}x{xau_best['dmult']}, "
                f"trail={tm_n[xau_best['tm']]}x{xau_best['tmult']}, "
                f"filter={fm_n[xau_best['fm']]}(>{xau_best['adx_th']}), "
                f"session={ss_n[xau_best['sess']]}, cool={xau_best['cool']}\n\n")
        f.write(f"EURUSD:\n")
        f.write(f"  Profit: ${eur_best['profit']:.0f} | Trades: {eur_best['trades']} | "
                f"WR: {eur_best['wr']:.1f}% | PF: {eur_best['pf']:.2f} | "
                f"Sharpe: {eur_best['sharpe']:.2f} | DD: {eur_best['dd']:.1f}%\n")
        f.write(f"  Walk Forward: {'ROBUST' if eur_robust else 'NOT ROBUST'}\n")
        f.write(f"  Config: dist={dm_n[eur_best['dm']]}x{eur_best['dmult']}, "
                f"trail={tm_n[eur_best['tm']]}x{eur_best['tmult']}, "
                f"filter={fm_n[eur_best['fm']]}(>{eur_best['adx_th']}), "
                f"session={ss_n[eur_best['sess']]}, cool={eur_best['cool']}\n")

    print("\n  Results saved to results/RESULTS.txt")
    print("=" * 70)
