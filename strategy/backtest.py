from dataclasses import dataclass

import pandas as pd

from .factors import performance_metrics
from .generate_data import load_strategy_data
from .signal_generator import SignalGenerator


TRADING_DAYS = 252


@dataclass
class BacktestResult:
    start_date: str
    end_date: str
    years: float
    gross_total_return_pct: float
    gross_cagr_pct: float
    gross_sharpe_ratio: float
    net_total_return_pct: float
    net_cagr_pct: float
    net_annual_volatility_pct: float
    net_sharpe_ratio: float
    net_max_drawdown_pct: float
    net_win_rate_pct: float
    rebalances: int
    final_equity: float
    total_cost_drag_pct: float
    cost_assumptions: dict
    signal_diagnostics: dict
    component_correlations: dict
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
                "growth_real_estate": self.config["strategy"]["target_growth_weight"]
                * (1 - self.config["risk"]["reserve_weight"]),
                "lease_income": self.config["strategy"]["target_income_weight"]
                * (1 - self.config["risk"]["reserve_weight"]),
                "reit_hedge": 0.0,
            }
        )
        gross_equity = [initial_capital]
        net_equity = [initial_capital]
        gross_strategy_returns = []
        net_strategy_returns = []
        total_cost_drag = 0.0
        spread_regime_returns = {"active": [], "inactive": []}
        spread_active_days = 0
        cap_rate_active_days = 0
        rebalances = 0
        costs = self.config["costs"]

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

            turnover = 0.0
            if (target - weights).abs().sum() > rebalance_threshold:
                turnover = float((target - weights).abs().sum())
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
            raw_vol_spread = fast_vol - slow_vol
            spread_excess = max(0.0, raw_vol_spread - self.config["signals"]["spread_trigger"])
            capture_rate = self.config["signals"]["vol_spread_capture_rate"]
            if raw_vol_spread > self.config["signals"]["high_spread_trigger"]:
                capture_rate *= 1.25
            else:
                capture_rate *= 0.75
            hedge_alpha = (
                abs(weights["reit_hedge"])
                * spread_excess
                * capture_rate
                / TRADING_DAYS
            )
            gross_return = (
                weights["growth_real_estate"] * row["growth_real_estate"]
                + weights["lease_income"] * row["lease_income"]
                + weights["reit_hedge"] * row["reit_hedge"]
                + hedge_alpha
            )
            reserve_drag = self.config["risk"]["reserve_weight"] * 0.00001
            gross_return -= reserve_drag

            transaction_drag = turnover * (
                costs["transaction_cost_per_turnover"] + costs["slippage_per_turnover"]
            )
            borrow_drag = abs(weights["reit_hedge"]) * costs["short_borrow_cost_annual"] / TRADING_DAYS
            management_drag = costs["management_fee_annual"] / TRADING_DAYS
            performance_drag = max(gross_return, 0.0) * costs["performance_fee_rate"]
            daily_cost_drag = transaction_drag + borrow_drag + management_drag + performance_drag
            net_return = gross_return - daily_cost_drag

            if raw_vol_spread > self.config["signals"]["high_spread_trigger"]:
                spread_active_days += 1
                spread_regime_returns["active"].append(net_return)
            else:
                spread_regime_returns["inactive"].append(net_return)

            if current_factors.iloc[-1]["cap_rate"] >= self.config["signals"]["cap_rate_buy_threshold"]:
                cap_rate_active_days += 1

            gross_strategy_returns.append(gross_return)
            net_strategy_returns.append(net_return)
            total_cost_drag += daily_cost_drag
            gross_equity.append(gross_equity[-1] * (1 + gross_return))
            net_equity.append(net_equity[-1] * (1 + net_return))

        gross_equity_series = pd.Series(gross_equity, index=prices.index, name="gross_equity")
        net_equity_series = pd.Series(net_equity, index=prices.index, name="net_equity")
        gross_returns_series = pd.Series(
            gross_strategy_returns, index=prices.index[1:], name="gross_returns"
        )
        net_returns_series = pd.Series(
            net_strategy_returns, index=prices.index[1:], name="net_returns"
        )
        gross_metrics = performance_metrics(gross_equity_series, gross_returns_series)
        net_metrics = performance_metrics(net_equity_series, net_returns_series)
        latest_signal = self.signal_generator.generate_signal(prices, factors)
        correlations = asset_returns[
            ["growth_real_estate", "lease_income", "reit_hedge"]
        ].corr()
        component_correlations = {
            "growth_vs_reit_hedge": round(
                float(correlations.loc["growth_real_estate", "reit_hedge"]), 4
            ),
            "lease_vs_reit_hedge": round(
                float(correlations.loc["lease_income", "reit_hedge"]), 4
            ),
            "growth_vs_lease": round(
                float(correlations.loc["growth_real_estate", "lease_income"]), 4
            ),
        }
        active_returns = pd.Series(spread_regime_returns["active"], dtype=float)
        inactive_returns = pd.Series(spread_regime_returns["inactive"], dtype=float)
        signal_diagnostics = {
            "spread_active_days_pct": round(spread_active_days / max(len(net_returns_series), 1) * 100, 2),
            "cap_rate_rule_active_days_pct": round(
                cap_rate_active_days / max(len(net_returns_series), 1) * 100, 2
            ),
            "avg_daily_net_return_when_spread_active_pct": round(
                float(active_returns.mean() * 100) if not active_returns.empty else 0.0,
                4,
            ),
            "avg_daily_net_return_when_spread_inactive_pct": round(
                float(inactive_returns.mean() * 100) if not inactive_returns.empty else 0.0,
                4,
            ),
        }
        cost_assumptions = {
            "transaction_cost_per_turnover_pct": costs["transaction_cost_per_turnover"] * 100,
            "slippage_per_turnover_pct": costs["slippage_per_turnover"] * 100,
            "short_borrow_cost_annual_pct": costs["short_borrow_cost_annual"] * 100,
            "management_fee_annual_pct": costs["management_fee_annual"] * 100,
            "performance_fee_rate_pct": costs["performance_fee_rate"] * 100,
        }

        return BacktestResult(
            start_date=net_metrics["start_date"],
            end_date=net_metrics["end_date"],
            years=net_metrics["years"],
            gross_total_return_pct=gross_metrics["total_return_pct"],
            gross_cagr_pct=gross_metrics["cagr_pct"],
            gross_sharpe_ratio=gross_metrics["sharpe_ratio"],
            net_total_return_pct=net_metrics["total_return_pct"],
            net_cagr_pct=net_metrics["cagr_pct"],
            net_annual_volatility_pct=net_metrics["annual_volatility_pct"],
            net_sharpe_ratio=net_metrics["sharpe_ratio"],
            net_max_drawdown_pct=net_metrics["max_drawdown_pct"],
            net_win_rate_pct=net_metrics["win_rate_pct"],
            rebalances=rebalances,
            final_equity=round(float(net_equity_series.iloc[-1]), 2),
            total_cost_drag_pct=round(total_cost_drag * 100, 2),
            cost_assumptions=cost_assumptions,
            signal_diagnostics=signal_diagnostics,
            component_correlations=component_correlations,
            latest_signal=latest_signal,
        )
