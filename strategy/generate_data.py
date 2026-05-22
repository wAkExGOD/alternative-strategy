from datetime import datetime

import numpy as np
import pandas as pd


TRADING_DAYS = 252


def _business_dates(start_date, end_date=None):
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    return pd.date_range(start=start_date, end=end_date, freq="B")


def _return_series(
    dates,
    annual_return,
    annual_volatility,
    seed,
    shock_scale=1.0,
    common_factor=None,
    common_beta=0.0,
):
    rng = np.random.default_rng(seed)
    daily_mu = annual_return / TRADING_DAYS
    daily_sigma = annual_volatility / np.sqrt(TRADING_DAYS)
    seasonal = 0.00018 * np.sin(np.linspace(0, 8 * np.pi, len(dates)))
    shocks = rng.normal(daily_mu, daily_sigma, len(dates)) * shock_scale
    if common_factor is not None:
        shocks = shocks + common_beta * common_factor
    return shocks + seasonal


def generate_synthetic_market(config, end_date=None):
    start_date = config["strategy"]["start_date"]
    if end_date is None:
        end_date = config["strategy"].get("end_date")
    dates = _business_dates(start_date, end_date)
    assets = config["assets"]
    rng = np.random.default_rng(7)
    common_real_estate_factor = rng.normal(0, 0.0065, len(dates))

    growth = _return_series(
        dates,
        assets["growth_real_estate"]["annual_return"],
        assets["growth_real_estate"]["annual_volatility"],
        seed=11,
        common_factor=common_real_estate_factor,
        common_beta=0.55,
    )
    lease = _return_series(
        dates,
        assets["lease_income"]["annual_return"],
        assets["lease_income"]["annual_volatility"],
        seed=17,
        shock_scale=0.55,
        common_factor=common_real_estate_factor,
        common_beta=0.12,
    )
    hedge = _return_series(
        dates,
        assets["reit_hedge"]["annual_return"],
        assets["reit_hedge"]["annual_volatility"],
        seed=23,
        shock_scale=1.2,
        common_factor=common_real_estate_factor,
        common_beta=1.25,
    )

    # Stress pockets imitate fast repricing in listed real estate instruments.
    stress_mask = (dates.year == 2022) | ((dates.year == 2025) & (dates.month <= 3))
    hedge[stress_mask] -= 0.0009
    growth[stress_mask] -= 0.00025
    lease[stress_mask] -= 0.00005

    returns = pd.DataFrame(
        {
            "growth_real_estate": growth,
            "lease_income": lease,
            "reit_hedge": hedge,
        },
        index=dates,
    )
    prices = (1 + returns).cumprod() * 100
    return prices


def generate_property_factors(config, market_prices):
    dates = market_prices.index
    rng = np.random.default_rng(101)

    occupancy = 0.94 + 0.025 * np.sin(np.linspace(0, 6 * np.pi, len(dates)))
    occupancy += rng.normal(0, 0.008, len(dates))
    occupancy = np.clip(occupancy, 0.84, 0.985)

    tenant_score = 0.78 + 0.035 * np.cos(np.linspace(0, 5 * np.pi, len(dates)))
    tenant_score += rng.normal(0, 0.01, len(dates))
    tenant_score = np.clip(tenant_score, 0.62, 0.92)

    cap_rate = 0.061 + 0.006 * np.sin(np.linspace(0, 4 * np.pi, len(dates)) + 0.8)
    cap_rate += rng.normal(0, 0.0015, len(dates))
    cap_rate = np.clip(cap_rate, 0.048, 0.078)

    rent_indexation = 0.035 + 0.012 * np.maximum(0, np.sin(np.linspace(0, 3 * np.pi, len(dates))))
    liquidity_score = 0.74 + rng.normal(0, 0.025, len(dates))
    liquidity_score = np.clip(liquidity_score, 0.55, 0.9)

    return pd.DataFrame(
        {
            "occupancy": occupancy,
            "tenant_score": tenant_score,
            "cap_rate": cap_rate,
            "rent_indexation": rent_indexation,
            "liquidity_score": liquidity_score,
        },
        index=dates,
    )


def load_strategy_data(config, end_date=None):
    prices = generate_synthetic_market(config, end_date=end_date)
    factors = generate_property_factors(config, prices)
    return prices, factors
