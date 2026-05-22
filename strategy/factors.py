import numpy as np
import pandas as pd


TRADING_DAYS = 252


class RealEstateFactorModel:
    def __init__(self, config):
        self.config = config

    def score_latest(self, prices, factors):
        row = factors.iloc[-1]
        fast_vol = self._annualized_vol(prices["reit_hedge"])
        slow_vol = self._annualized_vol(prices["lease_income"])
        spread = fast_vol - slow_vol

        risk = self.config["risk"]
        signals = self.config["signals"]
        occupancy_score = self._clip_score((row["occupancy"] - risk["min_occupancy"]) / 0.10)
        tenant_score = self._clip_score((row["tenant_score"] - risk["min_tenant_score"]) / 0.22)
        cap_rate_score = self._clip_score((row["cap_rate"] - 0.048) / 0.03)
        indexation_score = self._clip_score(row["rent_indexation"] / 0.06)
        liquidity_score = self._clip_score(row["liquidity_score"])

        stability_score = np.mean([occupancy_score, tenant_score, indexation_score, liquidity_score])
        alpha_score = np.mean([cap_rate_score, indexation_score, liquidity_score])
        hedge_pressure = self._clip_score((spread - signals["spread_trigger"]) / 0.12)

        return {
            "stability_score": round(float(stability_score), 4),
            "alpha_score": round(float(alpha_score), 4),
            "hedge_pressure": round(float(hedge_pressure), 4),
            "fast_volatility": round(float(fast_vol), 4),
            "slow_volatility": round(float(slow_vol), 4),
            "volatility_spread": round(float(spread), 4),
            "breakdown": {
                "occupancy": round(float(row["occupancy"]), 4),
                "tenant_score": round(float(row["tenant_score"]), 4),
                "cap_rate": round(float(row["cap_rate"]), 4),
                "rent_indexation": round(float(row["rent_indexation"]), 4),
                "liquidity_score": round(float(row["liquidity_score"]), 4),
            },
        }

    @staticmethod
    def _annualized_vol(series, window=63):
        returns = series.pct_change().dropna().tail(window)
        if returns.empty:
            return 0.0
        return returns.std() * np.sqrt(TRADING_DAYS)

    @staticmethod
    def _clip_score(value):
        return float(np.clip(value, 0.0, 1.0))


def rolling_max_drawdown(equity):
    running_max = equity.cummax()
    drawdown = equity / running_max - 1
    return drawdown


def performance_metrics(equity, daily_returns):
    total_return = equity.iloc[-1] / equity.iloc[0] - 1
    years = max((equity.index[-1] - equity.index[0]).days / 365.25, 1 / TRADING_DAYS)
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1
    vol = daily_returns.std() * np.sqrt(TRADING_DAYS)
    sharpe = 0.0 if vol == 0 else daily_returns.mean() * TRADING_DAYS / vol
    max_dd = rolling_max_drawdown(equity).min()
    win_rate = (daily_returns > 0).mean()
    return {
        "start_date": equity.index[0].strftime("%Y-%m-%d"),
        "end_date": equity.index[-1].strftime("%Y-%m-%d"),
        "years": round(years, 2),
        "total_return_pct": round(total_return * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "annual_volatility_pct": round(vol * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "win_rate_pct": round(win_rate * 100, 2),
    }
