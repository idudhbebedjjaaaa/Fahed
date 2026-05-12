#!/usr/bin/env python3
"""
Main analysis runner for SAR Expert Advisor.
Runs comprehensive backtesting, optimization, and statistical analysis.
"""

import sys
import os
import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python.data.data_loader import generate_eurusd_data, generate_xauusd_data
from python.backtesting.engine import (
    SARConfig, SARBacktester, BacktestResult,
    DistanceMode, TrailingMode, ExitMode, FilterMode,
    StartDirection, SessionFilter
)
from python.backtesting.indicators import regime_detector
from python.optimization.optimizer import (
    GridSearchOptimizer, GeneticOptimizer, BayesianOptimizer,
    ParameterSpace, score_result
)
from python.analysis.statistical import (
    monte_carlo_simulation, walk_forward_analysis,
    analyze_whipsaw, analyze_edge, compare_market_conditions,
    long_term_viability_assessment
)

warnings.filterwarnings('ignore')


def print_header(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_subheader(title: str):
    print(f"\n--- {title} ---")


def format_currency(val: float) -> str:
    return f"${val:,.2f}"


def format_pct(val: float) -> str:
    return f"{val:.2f}%"


def run_baseline_tests(data: pd.DataFrame, symbol: str, config_base: SARConfig) -> dict:
    """Run baseline tests with different configurations."""
    print_header(f"BASELINE TESTS - {symbol}")
    results = {}
    
    # Test 1: Pure SAR (no filters, no trailing)
    print_subheader("Test 1: Pure SAR (No Filters, No Trailing)")
    config = SARConfig(
        distance_mode=DistanceMode.ATR,
        atr_distance_mult=2.0,
        trailing_mode=TrailingMode.NONE,
        filter_mode=FilterMode.NONE,
        exit_mode=ExitMode.REVERSE_ONLY,
        session_filter=SessionFilter.ALL,
        start_direction=StartDirection.TREND,
        initial_capital=config_base.initial_capital,
        point_value=config_base.point_value,
        pip_value=config_base.pip_value,
        contract_size=config_base.contract_size,
        commission_per_lot=config_base.commission_per_lot,
        slippage_points=config_base.slippage_points,
        max_consec_reversals=0,
        max_daily_loss_pct=0,
        cooldown_bars=0,
    )
    bt = SARBacktester(config)
    result = bt.run(data)
    results['pure_sar'] = result
    print_result_summary(result, "Pure SAR")
    
    # Test 2: SAR + ADX Filter
    print_subheader("Test 2: SAR + ADX Filter")
    config.filter_mode = FilterMode.ADX
    config.adx_threshold = 20.0
    bt = SARBacktester(config)
    result = bt.run(data)
    results['sar_adx'] = result
    print_result_summary(result, "SAR + ADX")
    
    # Test 3: SAR + EMA Filter
    print_subheader("Test 3: SAR + EMA Cross Filter")
    config.filter_mode = FilterMode.EMA_CROSS
    bt = SARBacktester(config)
    result = bt.run(data)
    results['sar_ema'] = result
    print_result_summary(result, "SAR + EMA")
    
    # Test 4: SAR + Composite Filter
    print_subheader("Test 4: SAR + Composite Filter")
    config.filter_mode = FilterMode.COMPOSITE
    bt = SARBacktester(config)
    result = bt.run(data)
    results['sar_composite'] = result
    print_result_summary(result, "SAR + Composite")
    
    # Test 5: SAR + ATR Trailing
    print_subheader("Test 5: SAR + ATR Trailing")
    config.filter_mode = FilterMode.ADX
    config.trailing_mode = TrailingMode.ATR
    config.exit_mode = ExitMode.REVERSE_ONLY
    bt = SARBacktester(config)
    result = bt.run(data)
    results['sar_atr_trail'] = result
    print_result_summary(result, "SAR + ATR Trail")
    
    # Test 6: SAR + Chandelier Exit
    print_subheader("Test 6: SAR + Chandelier Exit")
    config.trailing_mode = TrailingMode.CHANDELIER
    bt = SARBacktester(config)
    result = bt.run(data)
    results['sar_chandelier'] = result
    print_result_summary(result, "SAR + Chandelier")
    
    # Test 7: SAR with TP + Trailing
    print_subheader("Test 7: SAR with TP + Trailing")
    config.exit_mode = ExitMode.TP_AND_TRAIL
    config.trailing_mode = TrailingMode.ATR
    config.take_profit = 300
    bt = SARBacktester(config)
    result = bt.run(data)
    results['sar_tp_trail'] = result
    print_result_summary(result, "SAR + TP + Trail")
    
    # Test 8: SAR with Wait Reentry
    print_subheader("Test 8: SAR with Wait & Re-entry")
    config.exit_mode = ExitMode.WAIT_REENTRY
    config.wait_bars = 5
    bt = SARBacktester(config)
    result = bt.run(data)
    results['sar_wait'] = result
    print_result_summary(result, "SAR + Wait")
    
    # Test 9: SAR with Protection System
    print_subheader("Test 9: SAR with Full Protection")
    config.exit_mode = ExitMode.REVERSE_ONLY
    config.trailing_mode = TrailingMode.ATR
    config.max_consec_reversals = 5
    config.max_daily_loss_pct = 3.0
    config.cooldown_bars = 3
    bt = SARBacktester(config)
    result = bt.run(data)
    results['sar_protected'] = result
    print_result_summary(result, "SAR + Protection")
    
    return results


def test_distance_modes(data: pd.DataFrame, symbol: str, config_base: SARConfig) -> dict:
    """Test all distance modes."""
    print_header(f"DISTANCE MODE TESTS - {symbol}")
    results = {}
    
    for mode in DistanceMode:
        for dist_val in [1.0, 1.5, 2.0, 2.5, 3.0]:
            config = SARConfig(
                distance_mode=mode,
                fixed_distance=dist_val * 50,
                atr_distance_mult=dist_val,
                filter_mode=FilterMode.ADX,
                trailing_mode=TrailingMode.ATR,
                exit_mode=ExitMode.REVERSE_ONLY,
                initial_capital=config_base.initial_capital,
                point_value=config_base.point_value,
                pip_value=config_base.pip_value,
                contract_size=config_base.contract_size,
                commission_per_lot=config_base.commission_per_lot,
                slippage_points=config_base.slippage_points,
            )
            
            bt = SARBacktester(config)
            result = bt.run(data)
            key = f"{mode.value}_x{dist_val}"
            results[key] = result
    
    # Print comparison table
    print(f"\n{'Mode':<25} {'Net Profit':>12} {'PF':>8} {'Sharpe':>8} {'DD%':>8} {'WR%':>8} {'Trades':>8}")
    print("-" * 85)
    for key, result in sorted(results.items(), key=lambda x: x[1].net_profit, reverse=True):
        pf = result.profit_factor if result.profit_factor != float('inf') else 99.0
        print(f"{key:<25} {format_currency(result.net_profit):>12} {pf:>8.2f} "
              f"{result.sharpe_ratio:>8.2f} {format_pct(result.max_drawdown_pct):>8} "
              f"{format_pct(result.win_rate):>8} {result.total_trades:>8}")
    
    return results


def test_trailing_modes(data: pd.DataFrame, symbol: str, config_base: SARConfig) -> dict:
    """Test all trailing stop modes."""
    print_header(f"TRAILING STOP TESTS - {symbol}")
    results = {}
    
    for mode in TrailingMode:
        config = SARConfig(
            distance_mode=DistanceMode.ATR,
            atr_distance_mult=2.0,
            trailing_mode=mode,
            trail_atr_mult=1.5,
            chandelier_mult=3.0,
            vol_trail_mult=2.0,
            filter_mode=FilterMode.ADX,
            exit_mode=ExitMode.REVERSE_ONLY,
            initial_capital=config_base.initial_capital,
            point_value=config_base.point_value,
            pip_value=config_base.pip_value,
            contract_size=config_base.contract_size,
            commission_per_lot=config_base.commission_per_lot,
            slippage_points=config_base.slippage_points,
        )
        
        bt = SARBacktester(config)
        result = bt.run(data)
        results[mode.value] = result
    
    print(f"\n{'Trailing Mode':<20} {'Net Profit':>12} {'PF':>8} {'Sharpe':>8} {'DD%':>8} {'WR%':>8}")
    print("-" * 75)
    for key, result in sorted(results.items(), key=lambda x: x[1].net_profit, reverse=True):
        pf = result.profit_factor if result.profit_factor != float('inf') else 99.0
        print(f"{key:<20} {format_currency(result.net_profit):>12} {pf:>8.2f} "
              f"{result.sharpe_ratio:>8.2f} {format_pct(result.max_drawdown_pct):>8} "
              f"{format_pct(result.win_rate):>8}")
    
    return results


def test_sessions(data: pd.DataFrame, symbol: str, config_base: SARConfig) -> dict:
    """Test session filters."""
    print_header(f"SESSION FILTER TESTS - {symbol}")
    results = {}
    
    for session in SessionFilter:
        config = SARConfig(
            distance_mode=DistanceMode.ATR,
            atr_distance_mult=2.0,
            trailing_mode=TrailingMode.ATR,
            filter_mode=FilterMode.ADX,
            session_filter=session,
            exit_mode=ExitMode.REVERSE_ONLY,
            initial_capital=config_base.initial_capital,
            point_value=config_base.point_value,
            pip_value=config_base.pip_value,
            contract_size=config_base.contract_size,
            commission_per_lot=config_base.commission_per_lot,
            slippage_points=config_base.slippage_points,
        )
        
        bt = SARBacktester(config)
        result = bt.run(data)
        results[session.value] = result
    
    print(f"\n{'Session':<20} {'Net Profit':>12} {'PF':>8} {'Sharpe':>8} {'DD%':>8} {'Trades':>8}")
    print("-" * 70)
    for key, result in sorted(results.items(), key=lambda x: x[1].net_profit, reverse=True):
        pf = result.profit_factor if result.profit_factor != float('inf') else 99.0
        print(f"{key:<20} {format_currency(result.net_profit):>12} {pf:>8.2f} "
              f"{result.sharpe_ratio:>8.2f} {format_pct(result.max_drawdown_pct):>8} "
              f"{result.total_trades:>8}")
    
    return results


def test_start_directions(data: pd.DataFrame, symbol: str, config_base: SARConfig) -> dict:
    """Test different start directions."""
    print_header(f"START DIRECTION TESTS - {symbol}")
    results = {}
    
    for sd in StartDirection:
        config = SARConfig(
            distance_mode=DistanceMode.ATR,
            atr_distance_mult=2.0,
            trailing_mode=TrailingMode.ATR,
            filter_mode=FilterMode.ADX,
            start_direction=sd,
            exit_mode=ExitMode.REVERSE_ONLY,
            initial_capital=config_base.initial_capital,
            point_value=config_base.point_value,
            pip_value=config_base.pip_value,
            contract_size=config_base.contract_size,
            commission_per_lot=config_base.commission_per_lot,
            slippage_points=config_base.slippage_points,
        )
        
        bt = SARBacktester(config)
        result = bt.run(data)
        results[sd.value] = result
    
    print(f"\n{'Start Dir':<15} {'Net Profit':>12} {'PF':>8} {'Sharpe':>8} {'DD%':>8}")
    print("-" * 55)
    for key, result in sorted(results.items(), key=lambda x: x[1].net_profit, reverse=True):
        pf = result.profit_factor if result.profit_factor != float('inf') else 99.0
        print(f"{key:<15} {format_currency(result.net_profit):>12} {pf:>8.2f} "
              f"{result.sharpe_ratio:>8.2f} {format_pct(result.max_drawdown_pct):>8}")
    
    return results


def test_exit_modes(data: pd.DataFrame, symbol: str, config_base: SARConfig) -> dict:
    """Test exit mode comparison: TP+Trail vs Trail only vs Reverse only."""
    print_header(f"EXIT MODE COMPARISON - {symbol}")
    results = {}
    
    for em in ExitMode:
        config = SARConfig(
            distance_mode=DistanceMode.ATR,
            atr_distance_mult=2.0,
            trailing_mode=TrailingMode.ATR,
            filter_mode=FilterMode.ADX,
            exit_mode=em,
            take_profit=300,
            wait_bars=5,
            initial_capital=config_base.initial_capital,
            point_value=config_base.point_value,
            pip_value=config_base.pip_value,
            contract_size=config_base.contract_size,
            commission_per_lot=config_base.commission_per_lot,
            slippage_points=config_base.slippage_points,
        )
        
        bt = SARBacktester(config)
        result = bt.run(data)
        results[em.value] = result
    
    print(f"\n{'Exit Mode':<20} {'Net Profit':>12} {'PF':>8} {'Sharpe':>8} {'DD%':>8} {'Trades':>8}")
    print("-" * 70)
    for key, result in sorted(results.items(), key=lambda x: x[1].net_profit, reverse=True):
        pf = result.profit_factor if result.profit_factor != float('inf') else 99.0
        print(f"{key:<20} {format_currency(result.net_profit):>12} {pf:>8.2f} "
              f"{result.sharpe_ratio:>8.2f} {format_pct(result.max_drawdown_pct):>8} "
              f"{result.total_trades:>8}")
    
    return results


def run_optimization(data: pd.DataFrame, symbol: str, config_base: SARConfig) -> dict:
    """Run multi-method optimization."""
    print_header(f"OPTIMIZATION - {symbol}")
    
    param_space = ParameterSpace.get_reduced_space()
    
    # Grid Search
    print_subheader("Grid Search Optimization")
    gs = GridSearchOptimizer(param_space, config_base)
    gs_results = gs.optimize(data, max_combinations=200)
    
    if gs_results:
        print(f"\nTop 5 Grid Search Results:")
        for i, r in enumerate(gs_results[:5]):
            print(f"  #{i+1}: Score={r.score:.4f}, Profit={format_currency(r.net_profit)}, "
                  f"Sharpe={r.sharpe_ratio:.2f}, DD={format_pct(r.max_drawdown_pct)}")
    
    # Genetic Algorithm
    print_subheader("Genetic Algorithm Optimization")
    ga = GeneticOptimizer(param_space, config_base,
                          population_size=30, generations=15)
    ga_results = ga.optimize(data)
    
    if ga_results:
        print(f"\nTop 5 Genetic Results:")
        for i, r in enumerate(ga_results[:5]):
            print(f"  #{i+1}: Score={r.score:.4f}, Profit={format_currency(r.net_profit)}, "
                  f"Sharpe={r.sharpe_ratio:.2f}, DD={format_pct(r.max_drawdown_pct)}")
    
    # Bayesian Optimization
    print_subheader("Bayesian Optimization")
    bo = BayesianOptimizer(param_space, config_base, n_trials=50)
    bo_results = bo.optimize(data)
    
    if bo_results:
        print(f"\nTop 5 Bayesian Results:")
        for i, r in enumerate(bo_results[:5]):
            print(f"  #{i+1}: Score={r.score:.4f}, Profit={format_currency(r.net_profit)}, "
                  f"Sharpe={r.sharpe_ratio:.2f}, DD={format_pct(r.max_drawdown_pct)}")
    
    # Find best overall
    all_results = gs_results + ga_results + bo_results
    all_results.sort(key=lambda x: x.score, reverse=True)
    
    best = all_results[0] if all_results else None
    
    return {
        'grid_search': gs_results,
        'genetic': ga_results,
        'bayesian': bo_results,
        'best': best,
    }


def run_deep_analysis(data: pd.DataFrame, result: BacktestResult, 
                       config: SARConfig, symbol: str) -> dict:
    """Run deep statistical analysis."""
    print_header(f"DEEP STATISTICAL ANALYSIS - {symbol}")
    
    # Edge analysis
    print_subheader("Edge Analysis")
    edge = analyze_edge(result)
    print(f"  Has Statistical Edge: {edge['has_edge']}")
    print(f"  Mean Trade: {format_currency(edge['mean_trade'])}")
    print(f"  T-statistic: {edge['t_statistic']:.4f}")
    print(f"  P-value: {edge['p_value']:.6f}")
    print(f"  Win Rate: {format_pct(edge['win_rate'])}")
    print(f"  Bootstrap CI: ({format_currency(edge['bootstrap_ci'][0])}, "
          f"{format_currency(edge['bootstrap_ci'][1])})")
    print(f"  Cohen's d (Effect Size): {edge['cohens_d']:.4f} ({edge['effect_size']})")
    
    # Whipsaw analysis
    print_subheader("Whipsaw Analysis")
    whipsaw = analyze_whipsaw(result.trades, config)
    print(f"  Total Reversals: {whipsaw.get('total_reversals', 0)}")
    print(f"  Profitable Reversals: {whipsaw.get('profitable_reversals', 0)}")
    print(f"  Losing Reversals: {whipsaw.get('losing_reversals', 0)}")
    print(f"  Whipsaw Rate: {format_pct(whipsaw.get('whipsaw_rate', 0))}")
    print(f"  Total Whipsaw Loss: {format_currency(whipsaw.get('total_whipsaw_loss', 0))}")
    print(f"  Whipsaw Sequences: {whipsaw.get('whipsaw_sequences', 0)}")
    print(f"  Avg Sequence Length: {whipsaw.get('avg_sequence_length', 0):.1f}")
    print(f"  Max Sequence Length: {whipsaw.get('max_sequence_length', 0)}")
    
    if whipsaw.get('whipsaw_by_regime'):
        print(f"\n  Whipsaw by Regime:")
        for regime, data_r in whipsaw['whipsaw_by_regime'].items():
            print(f"    {regime}: {data_r['count']} trades, Loss: {format_currency(data_r['loss'])}")
    
    # Monte Carlo
    print_subheader("Monte Carlo Simulation (1000 trials)")
    mc = monte_carlo_simulation(result.trades, config.initial_capital, n_simulations=1000)
    print(f"  Median Profit: {format_currency(mc.median_profit)}")
    print(f"  Mean Profit: {format_currency(mc.mean_profit)}")
    print(f"  5th Percentile: {format_currency(mc.percentile_5)}")
    print(f"  25th Percentile: {format_currency(mc.percentile_25)}")
    print(f"  75th Percentile: {format_currency(mc.percentile_75)}")
    print(f"  95th Percentile: {format_currency(mc.percentile_95)}")
    print(f"  Probability of Profit: {format_pct(mc.prob_profit)}")
    print(f"  Median Max Drawdown: {format_currency(mc.median_max_dd)}")
    print(f"  Worst Max Drawdown: {format_currency(mc.worst_max_dd)}")
    
    # Walk Forward
    print_subheader("Walk Forward Analysis (5 folds)")
    wf = walk_forward_analysis(data, config, n_folds=5)
    print(f"  In-Sample Profit: {format_currency(wf.is_profit)}")
    print(f"  Out-of-Sample Profit: {format_currency(wf.oos_profit)}")
    print(f"  Efficiency Ratio: {wf.efficiency_ratio:.4f}")
    print(f"  OOS Sharpe: {wf.oos_sharpe:.4f}")
    print(f"  Is Robust: {wf.is_robust}")
    
    if wf.fold_results:
        print(f"\n  Fold Details:")
        for fold in wf.fold_results:
            print(f"    Fold {fold['fold']}: IS={format_currency(fold['is_profit'])}, "
                  f"OOS={format_currency(fold['oos_profit'])}, "
                  f"IS WR={format_pct(fold['is_win_rate'])}, "
                  f"OOS WR={format_pct(fold['oos_win_rate'])}")
    
    # Market conditions comparison
    print_subheader("Performance by Market Condition")
    conditions = compare_market_conditions(data, config)
    
    if conditions.get('by_regime'):
        print(f"\n  {'Regime':<20} {'Trades':>8} {'Profit':>12} {'WR%':>8} {'PF':>8} {'Whipsaw%':>10}")
        print("  " + "-" * 70)
        for regime, stats in conditions['by_regime'].items():
            pf = stats['profit_factor'] if stats['profit_factor'] != float('inf') else 99.0
            print(f"  {regime:<20} {stats['trades']:>8} {format_currency(stats['net_profit']):>12} "
                  f"{format_pct(stats['win_rate']):>8} {pf:>8.2f} {format_pct(stats['whipsaw_rate']):>10}")
    
    print(f"\n  Best Regime: {conditions.get('best_regime', 'N/A')}")
    print(f"  Worst Regime: {conditions.get('worst_regime', 'N/A')}")
    
    # Long-term viability
    print_subheader("Long-Term Viability Assessment")
    viability = long_term_viability_assessment(result, mc, wf)
    print(f"\n  OVERALL SCORE: {viability['overall_score']:.4f}")
    print(f"  VERDICT: {viability['verdict']}")
    print(f"\n  Component Scores:")
    for comp, score in viability['component_scores'].items():
        print(f"    {comp}: {score:.2f}")
    
    print(f"\n  Recommendations:")
    for rec in viability['recommendations']:
        print(f"    - {rec}")
    
    return {
        'edge': edge,
        'whipsaw': whipsaw,
        'monte_carlo': mc,
        'walk_forward': wf,
        'conditions': conditions,
        'viability': viability,
    }


def print_result_summary(result: BacktestResult, label: str):
    """Print a concise result summary."""
    pf = result.profit_factor if result.profit_factor != float('inf') else 99.0
    rf = result.recovery_factor if result.recovery_factor != float('inf') else 99.0
    
    print(f"\n  [{label}]")
    print(f"  Net Profit:     {format_currency(result.net_profit)}")
    print(f"  Profit Factor:  {pf:.2f}")
    print(f"  Sharpe Ratio:   {result.sharpe_ratio:.2f}")
    print(f"  Max Drawdown:   {format_currency(result.max_drawdown)} ({format_pct(result.max_drawdown_pct)})")
    print(f"  Recovery Factor:{rf:.2f}")
    print(f"  Win Rate:       {format_pct(result.win_rate)}")
    print(f"  Total Trades:   {result.total_trades}")
    print(f"  Avg Trade:      {format_currency(result.avg_trade)}")
    print(f"  Expectancy:     {format_currency(result.expectancy)}")
    print(f"  Reversals:      {result.total_reversals}")
    print(f"  Whipsaw Losses: {format_currency(result.whipsaw_losses)}")
    print(f"  Avg Bars Held:  {result.avg_bars_held:.1f}")


def main():
    print_header("SAR EXPERT ADVISOR - COMPREHENSIVE ANALYSIS")
    print("Quant Fund Grade Analysis")
    print(f"Timestamp: {pd.Timestamp.now()}")
    
    # Generate data
    print_subheader("Generating Synthetic Market Data")
    eurusd_data = generate_eurusd_data(periods=15000, seed=42)
    xauusd_data = generate_xauusd_data(periods=15000, seed=42)
    
    print(f"EURUSD: {len(eurusd_data)} bars, {eurusd_data.index[0]} to {eurusd_data.index[-1]}")
    print(f"XAUUSD: {len(xauusd_data)} bars, {xauusd_data.index[0]} to {xauusd_data.index[-1]}")
    
    # Base configs
    eurusd_config = SARConfig(
        initial_capital=10000.0,
        point_value=0.00001,
        pip_value=10.0,
        contract_size=100000.0,
        commission_per_lot=7.0,
        slippage_points=2.0,
    )
    
    xauusd_config = SARConfig(
        initial_capital=10000.0,
        point_value=0.01,
        pip_value=1.0,
        contract_size=100.0,
        commission_per_lot=7.0,
        slippage_points=5.0,
    )
    
    all_results = {}
    
    # ===== EURUSD =====
    print("\n" + "#" * 80)
    print("#" + " " * 30 + "EURUSD" + " " * 30 + "#")
    print("#" * 80)
    
    # Baseline tests
    eu_baseline = run_baseline_tests(eurusd_data, "EURUSD", eurusd_config)
    all_results['eurusd_baseline'] = eu_baseline
    
    # Distance tests
    eu_distances = test_distance_modes(eurusd_data, "EURUSD", eurusd_config)
    all_results['eurusd_distances'] = eu_distances
    
    # Trailing tests
    eu_trailing = test_trailing_modes(eurusd_data, "EURUSD", eurusd_config)
    all_results['eurusd_trailing'] = eu_trailing
    
    # Session tests
    eu_sessions = test_sessions(eurusd_data, "EURUSD", eurusd_config)
    all_results['eurusd_sessions'] = eu_sessions
    
    # Start direction tests
    eu_starts = test_start_directions(eurusd_data, "EURUSD", eurusd_config)
    all_results['eurusd_starts'] = eu_starts
    
    # Exit mode tests
    eu_exits = test_exit_modes(eurusd_data, "EURUSD", eurusd_config)
    all_results['eurusd_exits'] = eu_exits
    
    # Optimization
    eu_opt = run_optimization(eurusd_data, "EURUSD", eurusd_config)
    all_results['eurusd_optimization'] = eu_opt
    
    # Deep analysis on best configuration
    best_eu_params = eu_opt['best'].params if eu_opt.get('best') else {}
    from python.optimization.optimizer import params_to_config
    best_eu_config = params_to_config(best_eu_params, eurusd_config)
    
    bt_best_eu = SARBacktester(best_eu_config)
    best_eu_result = bt_best_eu.run(eurusd_data)
    
    eu_analysis = run_deep_analysis(eurusd_data, best_eu_result, best_eu_config, "EURUSD")
    all_results['eurusd_analysis'] = eu_analysis
    
    # ===== XAUUSD =====
    print("\n" + "#" * 80)
    print("#" + " " * 30 + "XAUUSD" + " " * 30 + "#")
    print("#" * 80)
    
    # Baseline tests
    xau_baseline = run_baseline_tests(xauusd_data, "XAUUSD", xauusd_config)
    all_results['xauusd_baseline'] = xau_baseline
    
    # Distance tests
    xau_distances = test_distance_modes(xauusd_data, "XAUUSD", xauusd_config)
    all_results['xauusd_distances'] = xau_distances
    
    # Trailing tests
    xau_trailing = test_trailing_modes(xauusd_data, "XAUUSD", xauusd_config)
    all_results['xauusd_trailing'] = xau_trailing
    
    # Session tests
    xau_sessions = test_sessions(xauusd_data, "XAUUSD", xauusd_config)
    all_results['xauusd_sessions'] = xau_sessions
    
    # Exit mode tests
    xau_exits = test_exit_modes(xauusd_data, "XAUUSD", xauusd_config)
    all_results['xauusd_exits'] = xau_exits
    
    # Optimization
    xau_opt = run_optimization(xauusd_data, "XAUUSD", xauusd_config)
    all_results['xauusd_optimization'] = xau_opt
    
    # Deep analysis
    best_xau_params = xau_opt['best'].params if xau_opt.get('best') else {}
    best_xau_config = params_to_config(best_xau_params, xauusd_config)
    
    bt_best_xau = SARBacktester(best_xau_config)
    best_xau_result = bt_best_xau.run(xauusd_data)
    
    xau_analysis = run_deep_analysis(xauusd_data, best_xau_result, best_xau_config, "XAUUSD")
    all_results['xauusd_analysis'] = xau_analysis
    
    # ===== FINAL COMPARISON =====
    print_header("FINAL COMPARISON & RECOMMENDATIONS")
    
    print_subheader("Best Configurations")
    if eu_opt.get('best'):
        print(f"\nEURUSD Best Parameters:")
        for k, v in eu_opt['best'].params.items():
            print(f"  {k}: {v}")
        print(f"  Score: {eu_opt['best'].score:.4f}")
        print(f"  Net Profit: {format_currency(eu_opt['best'].net_profit)}")
        print(f"  Sharpe: {eu_opt['best'].sharpe_ratio:.2f}")
    
    if xau_opt.get('best'):
        print(f"\nXAUUSD Best Parameters:")
        for k, v in xau_opt['best'].params.items():
            print(f"  {k}: {v}")
        print(f"  Score: {xau_opt['best'].score:.4f}")
        print(f"  Net Profit: {format_currency(xau_opt['best'].net_profit)}")
        print(f"  Sharpe: {xau_opt['best'].sharpe_ratio:.2f}")
    
    print_subheader("Viability Summary")
    if eu_analysis.get('viability'):
        print(f"\nEURUSD: {eu_analysis['viability']['verdict']}")
        print(f"  Score: {eu_analysis['viability']['overall_score']:.4f}")
    if xau_analysis.get('viability'):
        print(f"\nXAUUSD: {xau_analysis['viability']['verdict']}")
        print(f"  Score: {xau_analysis['viability']['overall_score']:.4f}")
    
    print_header("ANALYSIS COMPLETE")
    
    return all_results


if __name__ == '__main__':
    results = main()
