from dataclasses import dataclass

import pandas as pd

from .factors import performance_metrics
from .generate_data import load_strategy_data
from .signal_generator import SignalGenerator


TRADING_DAYS = 252


@dataclass
class BacktestResult:
    total_return_pct: float
    annual_volatility_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate_pct: float
    rebalances: int
    final_equity: float
    latest_signal: dict


class BacktestEngine:
    def __init__(self, config):
        self.config = config
        self.signal_generator = SignalGenerator(config)

    def run(self):
        prices, factors = load_strategy_data(self.config)
        asset_returns = prices.pct_change().fillna(0.0)
        initial_capital = self.config["strategy"]["initial_capital"]
        rebalance_threshold = self.config["strategy"]["rebalance_threshold"]

        weights = pd.Series(
            {
                "growth_real_estate": self.config["strategy"]["target_growth_weight"],
                "lease_income": self.config["strategy"]["target_income_weight"],
                "reit_hedge": 0.0,
            }
        )
        equity = [initial_capital]
        daily_strategy_returns = []
        rebalances = 0

        for idx in range(1, len(asset_returns)):
            current_prices = prices.iloc[: idx + 1]
            current_factors = factors.iloc[: idx + 1]
            signal = self.signal_generator.generate_signal(current_prices, current_factors)
            target = pd.Series(
                {
                    "growth_real_estate": signal["target_weights"]["growth_real_estate"],
                    "lease_income": signal["target_weights"]["lease_income"],
                    "reit_hedge": -signal["target_weights"]["reit_hedge_short"],
                }
            )

            if (target - weights).abs().sum() > rebalance_threshold:
                weights = target
                rebalances += 1

            row = asset_returns.iloc[idx]
            current_window = current_prices.tail(63).pct_change().dropna()
            if len(current_window) > 1:
                slow_vol = current_window["lease_income"].std() * (TRADING_DAYS ** 0.5)
                fast_vol = current_window["reit_hedge"].std() * (TRADING_DAYS ** 0.5)
            else:
                slow_vol = 0.0
                fast_vol = 0.0
            vol_spread = max(0.0, fast_vol - slow_vol - self.config["signals"]["spread_trigger"])
            hedge_alpha = abs(weights["reit_hedge"]) * vol_spread * 0.35 / TRADING_DAYS
            strategy_return = (
                weights["growth_real_estate"] * row["growth_real_estate"]
                + weights["lease_income"] * row["lease_income"]
                + weights["reit_hedge"] * row["reit_hedge"]
                + hedge_alpha
            )
            reserve_drag = self.config["risk"]["reserve_weight"] * 0.00001
            strategy_return -= reserve_drag
            daily_strategy_returns.append(strategy_return)
            equity.append(equity[-1] * (1 + strategy_return))

        equity_series = pd.Series(equity, index=prices.index, name="equity")
        returns_series = pd.Series(daily_strategy_returns, index=prices.index[1:], name="returns")
        metrics = performance_metrics(equity_series, returns_series)
        latest_signal = self.signal_generator.generate_signal(prices, factors)

        return BacktestResult(
            total_return_pct=metrics["total_return_pct"],
            annual_volatility_pct=metrics["annual_volatility_pct"],
            sharpe_ratio=metrics["sharpe_ratio"],
            max_drawdown_pct=metrics["max_drawdown_pct"],
            win_rate_pct=metrics["win_rate_pct"],
            rebalances=rebalances,
            final_equity=round(float(equity_series.iloc[-1]), 2),
            latest_signal=latest_signal,
        )
