from datetime import datetime

from .factors import RealEstateFactorModel


class SignalGenerator:
    def __init__(self, config):
        self.config = config
        self.factor_model = RealEstateFactorModel(config)

    def generate_signal(self, prices, factors):
        scores = self.factor_model.score_latest(prices, factors)
        strategy = self.config["strategy"]
        risk = self.config["risk"]
        signals = self.config["signals"]

        growth_weight = strategy["target_growth_weight"]
        income_weight = strategy["target_income_weight"]
        hedge_weight = 0.0

        if scores["hedge_pressure"] > 0:
            hedge_weight = min(risk["max_hedge_weight"], 0.06 + scores["hedge_pressure"] * 0.16)
            growth_weight -= hedge_weight * 0.70
            income_weight -= hedge_weight * 0.30

        if scores["breakdown"]["occupancy"] < signals["occupancy_warning"]:
            growth_weight -= 0.05
            income_weight += 0.05

        if scores["breakdown"]["tenant_score"] < signals["tenant_warning"]:
            income_weight -= 0.04
            hedge_weight += 0.04

        if scores["breakdown"]["cap_rate"] >= signals["cap_rate_buy_threshold"]:
            growth_weight += 0.04
            income_weight -= 0.04

        total = growth_weight + income_weight + hedge_weight
        reserve_weight = risk["reserve_weight"]
        investable_weight = 1.0 - reserve_weight
        weights = {
            "growth_real_estate": round((growth_weight / total) * investable_weight, 4),
            "lease_income": round((income_weight / total) * investable_weight, 4),
            "reit_hedge_short": round((hedge_weight / total) * investable_weight, 4),
            "cash_reserve": round(reserve_weight, 4),
        }
        exposure = {
            "long_exposure": round(weights["growth_real_estate"] + weights["lease_income"], 4),
            "short_exposure": round(weights["reit_hedge_short"], 4),
            "gross_exposure": round(
                weights["growth_real_estate"]
                + weights["lease_income"]
                + weights["reit_hedge_short"],
                4,
            ),
            "net_market_exposure": round(
                weights["growth_real_estate"]
                + weights["lease_income"]
                - weights["reit_hedge_short"],
                4,
            ),
            "uses_leverage": False,
        }

        if (
            weights["reit_hedge_short"] > 0.01
            and scores["hedge_pressure"] >= signals["hedge_pressure_trigger"]
        ):
            action = "CAPTURE_VOLATILITY_SPREAD"
        elif weights["reit_hedge_short"] > 0.01:
            action = "HEDGE_AND_HOLD"
        elif scores["alpha_score"] > 0.72 and scores["stability_score"] > 0.68:
            action = "ADD_VALUE_ADD_EXPOSURE"
        else:
            action = "HOLD_CORE_PORTFOLIO"

        return {
            "strategy": strategy["name"],
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "target_weights": weights,
            "exposure": exposure,
            "hold_period_months": signals["hold_period_months"],
            "signal_logic": {
                "volatility_spread_rule": (
                    f"spread > {signals['high_spread_trigger']:.2f} means listed REIT/futures "
                    "are repricing much faster than private real estate; activate volatility-spread capture"
                ),
                "hedge_pressure_rule": (
                    f"hedge_pressure >= {signals['hedge_pressure_trigger']:.2f} activates short REIT hedge"
                ),
                "cap_rate_rule": (
                    f"cap_rate >= {signals['cap_rate_buy_threshold']:.3f} supports value-add real estate exposure"
                ),
                "hold_period_rationale": (
                    "12 months matches private real-estate deal cadence and avoids pretending the asset is daily-liquid"
                ),
                "lease_income_definition": (
                    "private net-lease commercial real estate sleeve with long-term tenants, not a daily traded REIT"
                ),
            },
            "scores": scores,
        }
