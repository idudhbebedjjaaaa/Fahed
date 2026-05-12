"""
Statistical analysis module for SAR strategy.
Includes Monte Carlo simulation, Walk Forward analysis, and regime analysis.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from ..backtesting.engine import (
    SARConfig, SARBacktester, BacktestResult, Trade
)


@dataclass
class MonteCarloResult:
    """Results from Monte Carlo simulation."""
    median_profit: float = 0.0
    mean_profit: float = 0.0
    percentile_5: float = 0.0
    percentile_25: float = 0.0
    percentile_75: float = 0.0
    percentile_95: float = 0.0
    prob_profit: float = 0.0
    median_max_dd: float = 0.0
    worst_max_dd: float = 0.0
    best_profit: float = 0.0
    worst_profit: float = 0.0
    profit_distribution: np.ndarray = None
    drawdown_distribution: np.ndarray = None


@dataclass
class WalkForwardResult:
    """Results from Walk Forward analysis."""
    in_sample_results: List[BacktestResult]
    out_sample_results: List[BacktestResult]
    is_profit: float = 0.0
    oos_profit: float = 0.0
    efficiency_ratio: float = 0.0
    oos_sharpe: float = 0.0
    oos_profit_factor: float = 0.0
    is_robust: bool = False
    fold_results: List[Dict] = None


def monte_carlo_simulation(
    trades: List[Trade],
    initial_capital: float = 10000.0,
    n_simulations: int = 1000,
    seed: int = 42
) -> MonteCarloResult:
    """
    Run Monte Carlo simulation by reshuffling trade outcomes.
    
    This tests the robustness of the strategy by simulating
    different orderings of the same trades.
    """
    np.random.seed(seed)
    
    if not trades:
        return MonteCarloResult()
    
    profits = np.array([t.net_profit for t in trades])
    n_trades = len(profits)
    
    final_profits = np.zeros(n_simulations)
    max_drawdowns = np.zeros(n_simulations)
    
    for sim in range(n_simulations):
        # Shuffle trade order
        shuffled = np.random.permutation(profits)
        
        # Build equity curve
        equity = initial_capital + np.cumsum(shuffled)
        equity = np.insert(equity, 0, initial_capital)
        
        # Final profit
        final_profits[sim] = equity[-1] - initial_capital
        
        # Max drawdown
        peak = np.maximum.accumulate(equity)
        dd = equity - peak
        max_drawdowns[sim] = abs(dd.min())
    
    result = MonteCarloResult(
        median_profit=np.median(final_profits),
        mean_profit=np.mean(final_profits),
        percentile_5=np.percentile(final_profits, 5),
        percentile_25=np.percentile(final_profits, 25),
        percentile_75=np.percentile(final_profits, 75),
        percentile_95=np.percentile(final_profits, 95),
        prob_profit=np.mean(final_profits > 0) * 100,
        median_max_dd=np.median(max_drawdowns),
        worst_max_dd=np.max(max_drawdowns),
        best_profit=np.max(final_profits),
        worst_profit=np.min(final_profits),
        profit_distribution=final_profits,
        drawdown_distribution=max_drawdowns
    )
    
    return result


def walk_forward_analysis(
    data: pd.DataFrame,
    config: SARConfig,
    n_folds: int = 5,
    is_ratio: float = 0.7
) -> WalkForwardResult:
    """
    Walk Forward Analysis.
    
    Splits data into in-sample (training) and out-of-sample (testing) windows.
    Tests if in-sample performance generalizes to out-of-sample.
    """
    total_bars = len(data)
    fold_size = total_bars // n_folds
    
    is_results = []
    oos_results = []
    fold_details = []
    
    for fold in range(n_folds - 1):
        is_start = fold * fold_size
        is_end = is_start + int(fold_size * (1 + is_ratio * (n_folds - 1) / n_folds))
        is_end = min(is_end, is_start + int(fold_size * 1.5))
        oos_start = is_end
        oos_end = min(oos_start + fold_size, total_bars)
        
        if oos_end <= oos_start + 100:
            continue
        
        is_data = data.iloc[is_start:is_end]
        oos_data = data.iloc[oos_start:oos_end]
        
        # Run in-sample
        bt_is = SARBacktester(config)
        result_is = bt_is.run(is_data)
        is_results.append(result_is)
        
        # Run out-of-sample
        bt_oos = SARBacktester(config)
        result_oos = bt_oos.run(oos_data)
        oos_results.append(result_oos)
        
        fold_details.append({
            'fold': fold + 1,
            'is_period': f"{is_data.index[0]} to {is_data.index[-1]}",
            'oos_period': f"{oos_data.index[0]} to {oos_data.index[-1]}",
            'is_profit': result_is.net_profit,
            'oos_profit': result_oos.net_profit,
            'is_sharpe': result_is.sharpe_ratio,
            'oos_sharpe': result_oos.sharpe_ratio,
            'is_trades': result_is.total_trades,
            'oos_trades': result_oos.total_trades,
            'is_win_rate': result_is.win_rate,
            'oos_win_rate': result_oos.win_rate,
        })
    
    # Aggregate results
    total_is_profit = sum(r.net_profit for r in is_results)
    total_oos_profit = sum(r.net_profit for r in oos_results)
    
    avg_oos_sharpe = np.mean([r.sharpe_ratio for r in oos_results]) if oos_results else 0
    avg_oos_pf = np.mean([r.profit_factor for r in oos_results 
                          if r.profit_factor != float('inf')]) if oos_results else 0
    
    # Efficiency ratio: OOS profit / IS profit
    efficiency = total_oos_profit / total_is_profit if total_is_profit != 0 else 0
    
    # Robustness check: at least 60% of OOS folds are profitable
    profitable_folds = sum(1 for r in oos_results if r.net_profit > 0)
    is_robust = (profitable_folds / len(oos_results)) >= 0.6 if oos_results else False
    
    return WalkForwardResult(
        in_sample_results=is_results,
        out_sample_results=oos_results,
        is_profit=total_is_profit,
        oos_profit=total_oos_profit,
        efficiency_ratio=efficiency,
        oos_sharpe=avg_oos_sharpe,
        oos_profit_factor=avg_oos_pf,
        is_robust=is_robust,
        fold_results=fold_details
    )


def analyze_whipsaw(trades: List[Trade], config: SARConfig) -> Dict:
    """
    Deep whipsaw analysis.
    
    Identifies whipsaw patterns and quantifies their impact.
    """
    if not trades:
        return {}
    
    reversal_trades = [t for t in trades if t.exit_reason == 'reversal']
    profitable_reversals = [t for t in reversal_trades if t.net_profit > 0]
    losing_reversals = [t for t in reversal_trades if t.net_profit <= 0]
    
    # Whipsaw sequences: consecutive losing reversals
    whipsaw_sequences = []
    current_sequence = []
    
    for t in trades:
        if t.exit_reason == 'reversal' and t.net_profit <= 0:
            current_sequence.append(t)
        else:
            if len(current_sequence) >= 2:
                whipsaw_sequences.append(current_sequence.copy())
            current_sequence = []
    
    if len(current_sequence) >= 2:
        whipsaw_sequences.append(current_sequence)
    
    # Cost analysis
    total_whipsaw_loss = sum(t.net_profit for seq in whipsaw_sequences for t in seq)
    avg_whipsaw_length = np.mean([len(seq) for seq in whipsaw_sequences]) if whipsaw_sequences else 0
    max_whipsaw_length = max([len(seq) for seq in whipsaw_sequences]) if whipsaw_sequences else 0
    
    # Whipsaw by regime
    whipsaw_by_regime = {}
    for t in losing_reversals:
        regime = t.regime if t.regime else 'unknown'
        if regime not in whipsaw_by_regime:
            whipsaw_by_regime[regime] = {'count': 0, 'loss': 0}
        whipsaw_by_regime[regime]['count'] += 1
        whipsaw_by_regime[regime]['loss'] += t.net_profit
    
    # Bars held analysis for whipsaws
    whipsaw_bars = [t.bars_held for t in losing_reversals] if losing_reversals else [0]
    
    return {
        'total_reversals': len(reversal_trades),
        'profitable_reversals': len(profitable_reversals),
        'losing_reversals': len(losing_reversals),
        'whipsaw_rate': len(losing_reversals) / len(reversal_trades) * 100 if reversal_trades else 0,
        'total_whipsaw_loss': total_whipsaw_loss,
        'whipsaw_sequences': len(whipsaw_sequences),
        'avg_sequence_length': avg_whipsaw_length,
        'max_sequence_length': max_whipsaw_length,
        'whipsaw_by_regime': whipsaw_by_regime,
        'avg_whipsaw_bars': np.mean(whipsaw_bars),
        'whipsaw_cost_per_trade': total_whipsaw_loss / len(reversal_trades) if reversal_trades else 0,
    }


def analyze_edge(result: BacktestResult) -> Dict:
    """
    Analyze whether the strategy has a statistical edge.
    
    Tests:
    1. Is the mean trade significantly different from zero?
    2. Is the win rate significantly different from 50%?
    3. Is the profit factor significantly > 1?
    """
    from scipy import stats
    
    if not result.trades or len(result.trades) < 30:
        return {'has_edge': False, 'reason': 'Insufficient trades'}
    
    profits = [t.net_profit for t in result.trades]
    
    # T-test: is mean trade profit significantly > 0?
    t_stat, p_value = stats.ttest_1samp(profits, 0)
    mean_significant = p_value < 0.05 and t_stat > 0
    
    # Binomial test: is win rate significantly > 50%?
    wins = sum(1 for p in profits if p > 0)
    binom_result = stats.binomtest(wins, len(profits), 0.5, alternative='greater')
    binom_p = binom_result.pvalue
    winrate_significant = binom_p < 0.05
    
    # Bootstrap confidence interval for mean trade
    n_bootstrap = 10000
    bootstrap_means = np.zeros(n_bootstrap)
    for i in range(n_bootstrap):
        sample = np.random.choice(profits, size=len(profits), replace=True)
        bootstrap_means[i] = np.mean(sample)
    
    ci_lower = np.percentile(bootstrap_means, 2.5)
    ci_upper = np.percentile(bootstrap_means, 97.5)
    
    # Effect size (Cohen's d)
    cohens_d = np.mean(profits) / np.std(profits) if np.std(profits) > 0 else 0
    
    has_edge = mean_significant and ci_lower > 0
    
    return {
        'has_edge': has_edge,
        'mean_trade': np.mean(profits),
        't_statistic': t_stat,
        'p_value': p_value,
        'mean_significant': mean_significant,
        'win_rate': wins / len(profits) * 100,
        'winrate_p_value': binom_p,
        'winrate_significant': winrate_significant,
        'bootstrap_ci': (ci_lower, ci_upper),
        'cohens_d': cohens_d,
        'effect_size': 'large' if abs(cohens_d) > 0.8 else 'medium' if abs(cohens_d) > 0.5 else 'small',
        'n_trades': len(profits),
        'profit_factor': result.profit_factor,
        'sharpe_ratio': result.sharpe_ratio,
    }


def compare_market_conditions(
    data: pd.DataFrame,
    config: SARConfig,
    regime_column: str = 'regime'
) -> Dict:
    """
    Compare strategy performance across different market conditions.
    """
    from ..backtesting.indicators import regime_detector
    
    if regime_column not in data.columns:
        data = data.copy()
        data['regime'] = regime_detector(data)
    
    # Run full backtest
    bt = SARBacktester(config)
    result = bt.run(data)
    
    # Analyze by regime
    regime_analysis = {}
    regimes = data[regime_column].unique()
    
    for regime in regimes:
        regime_trades = [t for t in result.trades if t.regime == regime]
        if not regime_trades:
            continue
        
        profits = [t.net_profit for t in regime_trades]
        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p <= 0]
        
        regime_analysis[regime] = {
            'trades': len(regime_trades),
            'net_profit': sum(profits),
            'win_rate': len(wins) / len(profits) * 100,
            'avg_trade': np.mean(profits),
            'profit_factor': sum(wins) / abs(sum(losses)) if losses else float('inf'),
            'avg_bars_held': np.mean([t.bars_held for t in regime_trades]),
            'whipsaw_rate': sum(1 for t in regime_trades 
                              if t.exit_reason == 'reversal' and t.net_profit < 0) / len(regime_trades) * 100,
        }
    
    return {
        'overall': {
            'net_profit': result.net_profit,
            'sharpe_ratio': result.sharpe_ratio,
            'profit_factor': result.profit_factor,
            'win_rate': result.win_rate,
            'total_trades': result.total_trades,
        },
        'by_regime': regime_analysis,
        'best_regime': max(regime_analysis.items(), 
                          key=lambda x: x[1]['net_profit'])[0] if regime_analysis else None,
        'worst_regime': min(regime_analysis.items(),
                           key=lambda x: x[1]['net_profit'])[0] if regime_analysis else None,
    }


def long_term_viability_assessment(result: BacktestResult, mc_result: MonteCarloResult,
                                     wf_result: WalkForwardResult) -> Dict:
    """
    Comprehensive assessment of long-term strategy viability.
    """
    scores = {}
    
    # 1. Statistical edge score
    edge = analyze_edge(result)
    scores['edge_score'] = 1.0 if edge['has_edge'] else 0.0
    
    # 2. Monte Carlo robustness
    mc_score = 0.0
    if mc_result.prob_profit > 80: mc_score += 0.3
    if mc_result.prob_profit > 90: mc_score += 0.2
    if mc_result.percentile_5 > 0: mc_score += 0.3
    if mc_result.worst_profit > -result.config.initial_capital * 0.5: mc_score += 0.2
    scores['monte_carlo_score'] = mc_score
    
    # 3. Walk Forward robustness
    wf_score = 0.0
    if wf_result.is_robust: wf_score += 0.4
    if wf_result.efficiency_ratio > 0.5: wf_score += 0.3
    if wf_result.oos_sharpe > 0.5: wf_score += 0.3
    scores['walk_forward_score'] = wf_score
    
    # 4. Risk metrics
    risk_score = 0.0
    if result.max_drawdown_pct < 20: risk_score += 0.3
    if result.recovery_factor > 2: risk_score += 0.3
    if result.sharpe_ratio > 1: risk_score += 0.2
    if result.profit_factor > 1.5: risk_score += 0.2
    scores['risk_score'] = risk_score
    
    # 5. Trade quality
    trade_score = 0.0
    if result.win_rate > 40: trade_score += 0.2
    if result.expectancy > 0: trade_score += 0.3
    if result.max_consec_losses < 10: trade_score += 0.2
    if result.total_trades > 100: trade_score += 0.3
    scores['trade_quality_score'] = trade_score
    
    # Overall viability score
    overall = (
        scores['edge_score'] * 0.25 +
        scores['monte_carlo_score'] * 0.20 +
        scores['walk_forward_score'] * 0.25 +
        scores['risk_score'] * 0.15 +
        scores['trade_quality_score'] * 0.15
    )
    
    verdict = 'NOT VIABLE'
    if overall >= 0.7:
        verdict = 'VIABLE - Strong Edge'
    elif overall >= 0.5:
        verdict = 'CONDITIONALLY VIABLE - Needs Specific Market Conditions'
    elif overall >= 0.3:
        verdict = 'MARGINAL - High Risk, Limited Edge'
    
    return {
        'overall_score': overall,
        'verdict': verdict,
        'component_scores': scores,
        'edge_analysis': edge,
        'recommendations': _generate_recommendations(scores, result, mc_result, wf_result)
    }


def _generate_recommendations(scores: Dict, result: BacktestResult,
                               mc_result: MonteCarloResult,
                               wf_result: WalkForwardResult) -> List[str]:
    """Generate actionable recommendations based on analysis."""
    recs = []
    
    if not scores.get('edge_score', 0):
        recs.append("CRITICAL: No statistical edge detected. Strategy may be curve-fitted.")
    
    if scores.get('monte_carlo_score', 0) < 0.5:
        recs.append("Monte Carlo analysis shows fragility. Consider reducing position sizing.")
    
    if scores.get('walk_forward_score', 0) < 0.5:
        recs.append("Walk Forward analysis shows poor out-of-sample performance. Risk of overfitting.")
    
    if result.max_drawdown_pct > 30:
        recs.append(f"Max drawdown of {result.max_drawdown_pct:.1f}% is excessive. Reduce risk per trade.")
    
    if result.whipsaw_losses < -result.config.initial_capital * 0.5:
        recs.append("Whipsaw losses are significant. Consider stronger trend filters or wider reversal distance.")
    
    if result.total_trades < 100:
        recs.append("Insufficient trades for reliable conclusions. Need more data or shorter timeframe.")
    
    if result.profit_factor < 1.3:
        recs.append("Profit factor is marginal. Strategy is sensitive to execution costs.")
    
    if mc_result.percentile_5 < 0:
        recs.append(f"5th percentile Monte Carlo profit is negative ({mc_result.percentile_5:.2f}). "
                    "Strategy has meaningful probability of losing money.")
    
    if not wf_result.is_robust:
        recs.append("Strategy failed Walk Forward robustness test. Performance may not persist.")
    
    # Positive recommendations
    if result.sharpe_ratio > 1.5:
        recs.append("Strong Sharpe ratio suggests good risk-adjusted returns.")
    
    if wf_result.efficiency_ratio > 0.7:
        recs.append("Good Walk Forward efficiency suggests parameters are stable.")
    
    return recs
