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
        weights = {
            "growth_real_estate": round(growth_weight / total, 4),
            "lease_income": round(income_weight / total, 4),
            "reit_hedge_short": round(hedge_weight / total, 4),
        }

        if weights["reit_hedge_short"] > 0.01 and scores["hedge_pressure"] > 0.35:
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
            "hold_period_months": signals["hold_period_months"],
            "scores": scores,
        }
