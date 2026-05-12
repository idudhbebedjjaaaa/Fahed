"""
Multi-method optimization engine for SAR strategy.
Supports Grid Search, Genetic Algorithm, and Bayesian Optimization.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Callable
from itertools import product
from dataclasses import dataclass
import time
import json
from concurrent.futures import ProcessPoolExecutor
import warnings

from ..backtesting.engine import (
    SARConfig, SARBacktester, BacktestResult,
    DistanceMode, TrailingMode, ExitMode, FilterMode,
    StartDirection, SessionFilter
)


@dataclass
class OptimizationResult:
    """Result of a single optimization trial."""
    params: Dict
    net_profit: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0
    max_drawdown_pct: float = 0.0
    recovery_factor: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    score: float = 0.0


class ParameterSpace:
    """Defines the optimization parameter space."""
    
    @staticmethod
    def get_default_space() -> Dict:
        """Get default parameter search space."""
        return {
            'distance_mode': [dm.value for dm in DistanceMode],
            'fixed_distance': [50, 100, 150, 200, 300],
            'atr_distance_mult': [1.0, 1.5, 2.0, 2.5, 3.0],
            'atr_period': [10, 14, 20],
            
            'exit_mode': [em.value for em in ExitMode],
            'take_profit': [100, 200, 300, 500],
            
            'trailing_mode': [tm.value for tm in TrailingMode],
            'trail_atr_mult': [1.0, 1.5, 2.0, 2.5, 3.0],
            'chandelier_mult': [2.0, 3.0, 4.0],
            
            'filter_mode': [fm.value for fm in FilterMode],
            'adx_threshold': [15, 20, 25, 30],
            'ema_fast': [10, 20, 30],
            'ema_slow': [50, 100, 200],
            
            'session_filter': [sf.value for sf in SessionFilter],
            'start_direction': [sd.value for sd in StartDirection],
            
            'max_consec_reversals': [3, 5, 7, 10],
            'cooldown_bars': [0, 2, 3, 5],
            
            'risk_percent': [0.5, 1.0, 1.5, 2.0],
        }
    
    @staticmethod
    def get_reduced_space() -> Dict:
        """Get reduced space for faster optimization."""
        return {
            'distance_mode': ['atr', 'volatility'],
            'atr_distance_mult': [1.5, 2.0, 2.5, 3.0],
            
            'trailing_mode': ['atr', 'chandelier', 'volatility'],
            'trail_atr_mult': [1.5, 2.0, 2.5],
            
            'filter_mode': ['adx', 'ema_cross', 'composite'],
            'adx_threshold': [20, 25],
            
            'session_filter': ['all', 'london_ny'],
            
            'max_consec_reversals': [5, 7],
            'cooldown_bars': [2, 3],
        }


def score_result(result: BacktestResult, weights: Optional[Dict] = None) -> float:
    """
    Score a backtest result for optimization.
    
    Uses a composite fitness function combining multiple metrics.
    """
    if weights is None:
        weights = {
            'sharpe': 0.30,
            'profit_factor': 0.20,
            'recovery_factor': 0.15,
            'net_profit_norm': 0.15,
            'win_rate': 0.10,
            'drawdown_penalty': 0.10
        }
    
    if result.total_trades < 30:
        return -999
    
    score = 0.0
    
    # Sharpe ratio component
    score += weights.get('sharpe', 0) * min(result.sharpe_ratio, 5.0)
    
    # Profit factor component
    pf = min(result.profit_factor, 5.0) if result.profit_factor != float('inf') else 5.0
    score += weights.get('profit_factor', 0) * pf
    
    # Recovery factor
    rf = min(result.recovery_factor, 10.0) if result.recovery_factor != float('inf') else 10.0
    score += weights.get('recovery_factor', 0) * rf
    
    # Net profit (normalized to initial capital)
    np_norm = result.net_profit / result.config.initial_capital
    score += weights.get('net_profit_norm', 0) * min(np_norm, 10.0)
    
    # Win rate
    score += weights.get('win_rate', 0) * (result.win_rate / 100.0)
    
    # Drawdown penalty
    dd_penalty = max(0, result.max_drawdown_pct - 20) * 0.1
    score -= weights.get('drawdown_penalty', 0) * dd_penalty
    
    return score


def params_to_config(params: Dict, base_config: Optional[SARConfig] = None) -> SARConfig:
    """Convert parameter dict to SARConfig."""
    config = base_config if base_config else SARConfig()
    
    mapping = {
        'distance_mode': lambda v: DistanceMode(v),
        'trailing_mode': lambda v: TrailingMode(v),
        'exit_mode': lambda v: ExitMode(v),
        'filter_mode': lambda v: FilterMode(v),
        'start_direction': lambda v: StartDirection(v),
        'session_filter': lambda v: SessionFilter(v),
    }
    
    for key, value in params.items():
        if key in mapping:
            setattr(config, key, mapping[key](value))
        elif hasattr(config, key):
            setattr(config, key, value)
    
    return config


def run_single_backtest(args: Tuple) -> OptimizationResult:
    """Run a single backtest (for parallel execution)."""
    params, data_dict, base_config_dict = args
    
    # Reconstruct data
    data = pd.DataFrame(data_dict)
    data.index = pd.DatetimeIndex(data.index)
    
    # Build config
    config = SARConfig()
    for k, v in base_config_dict.items():
        if hasattr(config, k):
            setattr(config, k, v)
    
    config = params_to_config(params, config)
    
    try:
        bt = SARBacktester(config)
        result = bt.run(data)
        
        opt_result = OptimizationResult(
            params=params,
            net_profit=result.net_profit,
            sharpe_ratio=result.sharpe_ratio,
            profit_factor=result.profit_factor if result.profit_factor != float('inf') else 99.0,
            max_drawdown_pct=result.max_drawdown_pct,
            recovery_factor=result.recovery_factor if result.recovery_factor != float('inf') else 99.0,
            win_rate=result.win_rate,
            total_trades=result.total_trades,
            score=score_result(result)
        )
        return opt_result
    except Exception as e:
        return OptimizationResult(params=params, score=-9999)


class GridSearchOptimizer:
    """Grid search optimization."""
    
    def __init__(self, param_space: Dict, base_config: Optional[SARConfig] = None):
        self.param_space = param_space
        self.base_config = base_config or SARConfig()
        self.results: List[OptimizationResult] = []
    
    def optimize(self, data: pd.DataFrame, max_combinations: int = 5000) -> List[OptimizationResult]:
        """Run grid search optimization."""
        keys = list(self.param_space.keys())
        values = list(self.param_space.values())
        
        # Generate all combinations
        all_combos = list(product(*values))
        
        if len(all_combos) > max_combinations:
            indices = np.random.choice(len(all_combos), max_combinations, replace=False)
            all_combos = [all_combos[i] for i in indices]
        
        print(f"Grid Search: Testing {len(all_combos)} combinations...")
        
        self.results = []
        for idx, combo in enumerate(all_combos):
            params = dict(zip(keys, combo))
            config = params_to_config(params, SARConfig(
                initial_capital=self.base_config.initial_capital,
                point_value=self.base_config.point_value,
                pip_value=self.base_config.pip_value,
                contract_size=self.base_config.contract_size,
                commission_per_lot=self.base_config.commission_per_lot,
                slippage_points=self.base_config.slippage_points
            ))
            
            try:
                bt = SARBacktester(config)
                result = bt.run(data)
                
                opt_result = OptimizationResult(
                    params=params,
                    net_profit=result.net_profit,
                    sharpe_ratio=result.sharpe_ratio,
                    profit_factor=result.profit_factor if result.profit_factor != float('inf') else 99.0,
                    max_drawdown_pct=result.max_drawdown_pct,
                    recovery_factor=result.recovery_factor if result.recovery_factor != float('inf') else 99.0,
                    win_rate=result.win_rate,
                    total_trades=result.total_trades,
                    score=score_result(result)
                )
                self.results.append(opt_result)
            except Exception as e:
                pass
            
            if (idx + 1) % 100 == 0:
                print(f"  Progress: {idx + 1}/{len(all_combos)}")
        
        self.results.sort(key=lambda x: x.score, reverse=True)
        return self.results


class GeneticOptimizer:
    """Genetic algorithm optimization."""
    
    def __init__(self, param_space: Dict, base_config: Optional[SARConfig] = None,
                 population_size: int = 50, generations: int = 30,
                 mutation_rate: float = 0.15, elite_ratio: float = 0.1):
        self.param_space = param_space
        self.base_config = base_config or SARConfig()
        self.pop_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.elite_count = max(2, int(population_size * elite_ratio))
        self.results: List[OptimizationResult] = []
        self.generation_best: List[float] = []
    
    def _random_individual(self) -> Dict:
        """Create a random individual."""
        individual = {}
        for key, values in self.param_space.items():
            individual[key] = values[np.random.randint(len(values))]
        return individual
    
    def _crossover(self, parent1: Dict, parent2: Dict) -> Dict:
        """Single-point crossover."""
        child = {}
        keys = list(self.param_space.keys())
        crossover_point = np.random.randint(1, len(keys))
        
        for i, key in enumerate(keys):
            if i < crossover_point:
                child[key] = parent1[key]
            else:
                child[key] = parent2[key]
        
        return child
    
    def _mutate(self, individual: Dict) -> Dict:
        """Mutate an individual."""
        mutated = individual.copy()
        for key in self.param_space:
            if np.random.random() < self.mutation_rate:
                mutated[key] = self.param_space[key][
                    np.random.randint(len(self.param_space[key]))
                ]
        return mutated
    
    def _evaluate(self, individual: Dict, data: pd.DataFrame) -> float:
        """Evaluate fitness of an individual."""
        config = params_to_config(individual, SARConfig(
            initial_capital=self.base_config.initial_capital,
            point_value=self.base_config.point_value,
            pip_value=self.base_config.pip_value,
            contract_size=self.base_config.contract_size,
            commission_per_lot=self.base_config.commission_per_lot,
            slippage_points=self.base_config.slippage_points
        ))
        
        try:
            bt = SARBacktester(config)
            result = bt.run(data)
            return score_result(result), result
        except Exception:
            return -9999, None
    
    def optimize(self, data: pd.DataFrame) -> List[OptimizationResult]:
        """Run genetic optimization."""
        print(f"Genetic Optimization: pop={self.pop_size}, gen={self.generations}")
        
        # Initialize population
        population = [self._random_individual() for _ in range(self.pop_size)]
        
        all_results = []
        
        for gen in range(self.generations):
            # Evaluate fitness
            fitness_results = []
            for ind in population:
                score, result = self._evaluate(ind, data)
                fitness_results.append((ind, score, result))
            
            # Sort by fitness
            fitness_results.sort(key=lambda x: x[1], reverse=True)
            
            best_score = fitness_results[0][1]
            self.generation_best.append(best_score)
            
            if (gen + 1) % 5 == 0:
                print(f"  Generation {gen + 1}/{self.generations}: Best score = {best_score:.4f}")
            
            # Store results
            for ind, score, result in fitness_results:
                if result is not None:
                    opt_result = OptimizationResult(
                        params=ind,
                        net_profit=result.net_profit,
                        sharpe_ratio=result.sharpe_ratio,
                        profit_factor=result.profit_factor if result.profit_factor != float('inf') else 99.0,
                        max_drawdown_pct=result.max_drawdown_pct,
                        recovery_factor=result.recovery_factor if result.recovery_factor != float('inf') else 99.0,
                        win_rate=result.win_rate,
                        total_trades=result.total_trades,
                        score=score
                    )
                    all_results.append(opt_result)
            
            # Selection
            elite = [fr[0] for fr in fitness_results[:self.elite_count]]
            
            # Create next generation
            new_population = list(elite)
            
            # Tournament selection + crossover
            while len(new_population) < self.pop_size:
                # Tournament selection
                t1 = fitness_results[np.random.randint(min(len(fitness_results), self.pop_size // 2))]
                t2 = fitness_results[np.random.randint(min(len(fitness_results), self.pop_size // 2))]
                parent1 = t1[0] if t1[1] > t2[1] else t2[0]
                
                t1 = fitness_results[np.random.randint(min(len(fitness_results), self.pop_size // 2))]
                t2 = fitness_results[np.random.randint(min(len(fitness_results), self.pop_size // 2))]
                parent2 = t1[0] if t1[1] > t2[1] else t2[0]
                
                child = self._crossover(parent1, parent2)
                child = self._mutate(child)
                new_population.append(child)
            
            population = new_population[:self.pop_size]
        
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        # Deduplicate
        seen = set()
        unique_results = []
        for r in all_results:
            key = str(sorted(r.params.items()))
            if key not in seen:
                seen.add(key)
                unique_results.append(r)
        
        self.results = unique_results
        return self.results


class BayesianOptimizer:
    """Bayesian optimization using Optuna."""
    
    def __init__(self, param_space: Dict, base_config: Optional[SARConfig] = None,
                 n_trials: int = 200):
        self.param_space = param_space
        self.base_config = base_config or SARConfig()
        self.n_trials = n_trials
        self.results: List[OptimizationResult] = []
    
    def optimize(self, data: pd.DataFrame) -> List[OptimizationResult]:
        """Run Bayesian optimization using Optuna."""
        try:
            import optuna
            optuna.logging.set_verbosity(optuna.logging.WARNING)
        except ImportError:
            print("Optuna not available, falling back to genetic optimization")
            ga = GeneticOptimizer(self.param_space, self.base_config,
                                  generations=50, population_size=60)
            return ga.optimize(data)
        
        print(f"Bayesian Optimization: {self.n_trials} trials")
        
        all_results = []
        
        def objective(trial):
            params = {}
            for key, values in self.param_space.items():
                if isinstance(values[0], (int, float)) and len(values) > 2:
                    if isinstance(values[0], int):
                        params[key] = trial.suggest_int(key, min(values), max(values))
                    else:
                        params[key] = trial.suggest_float(key, min(values), max(values))
                else:
                    params[key] = trial.suggest_categorical(key, values)
            
            config = params_to_config(params, SARConfig(
                initial_capital=self.base_config.initial_capital,
                point_value=self.base_config.point_value,
                pip_value=self.base_config.pip_value,
                contract_size=self.base_config.contract_size,
                commission_per_lot=self.base_config.commission_per_lot,
                slippage_points=self.base_config.slippage_points
            ))
            
            try:
                bt = SARBacktester(config)
                result = bt.run(data)
                scr = score_result(result)
                
                opt_result = OptimizationResult(
                    params=params,
                    net_profit=result.net_profit,
                    sharpe_ratio=result.sharpe_ratio,
                    profit_factor=result.profit_factor if result.profit_factor != float('inf') else 99.0,
                    max_drawdown_pct=result.max_drawdown_pct,
                    recovery_factor=result.recovery_factor if result.recovery_factor != float('inf') else 99.0,
                    win_rate=result.win_rate,
                    total_trades=result.total_trades,
                    score=scr
                )
                all_results.append(opt_result)
                
                return scr
            except Exception:
                return -9999
        
        study = optuna.create_study(direction='maximize',
                                     sampler=optuna.samplers.TPESampler(seed=42))
        study.optimize(objective, n_trials=self.n_trials, show_progress_bar=False)
        
        all_results.sort(key=lambda x: x.score, reverse=True)
        self.results = all_results
        
        print(f"  Best score: {study.best_value:.4f}")
        print(f"  Best params: {study.best_params}")
        
        return self.results
