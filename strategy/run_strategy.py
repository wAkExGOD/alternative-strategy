import argparse
import json
from pathlib import Path

from .backtest import BacktestEngine
from .generate_data import load_strategy_data
from .signal_generator import SignalGenerator


CONFIG_PATH = Path("/app/config.yaml")
LOCAL_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"


def _parse_scalar(value):
    value = value.strip()
    if not value:
        return ""
    if value[0] == value[-1] and value.startswith(("'", '"')):
        return value[1:-1]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        if any(char in value for char in (".", "e", "E")):
            return float(value)
        return int(value)
    except ValueError:
        return value


def _load_yaml(path):
    try:
        import yaml

        with open(path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)
    except ModuleNotFoundError:
        pass

    config = {}
    stack = [(-1, config)]
    with open(path, "r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.split("#", 1)[0].rstrip()
            if not line:
                continue
            indent = len(line) - len(line.lstrip(" "))
            key, separator, value = line.strip().partition(":")
            if not separator:
                continue
            while stack and indent <= stack[-1][0]:
                stack.pop()
            parent = stack[-1][1]
            if value.strip():
                parent[key] = _parse_scalar(value)
            else:
                parent[key] = {}
                stack.append((indent, parent[key]))
    return config


def load_config(path=CONFIG_PATH):
    config_path = Path(path)
    if not config_path.exists():
        config_path = LOCAL_CONFIG_PATH
    return _load_yaml(config_path)


def run_backtest_only():
    config = load_config()
    result = BacktestEngine(config).run()

    print("=" * 62)
    print("SYBAU COMMERCIAL REAL ESTATE STRATEGY BACKTEST")
    print("=" * 62)
    print(f"Backtest period:    {result.start_date} to {result.end_date} ({result.years} years)")
    print(f"Gross total return: {result.gross_total_return_pct}%")
    print(f"Gross CAGR:         {result.gross_cagr_pct}%")
    print(f"Gross Sharpe:       {result.gross_sharpe_ratio}")
    print(f"Net total return:   {result.net_total_return_pct}%")
    print(f"Net CAGR:           {result.net_cagr_pct}%")
    print(f"Net volatility:     {result.net_annual_volatility_pct}%")
    print(f"Net Sharpe ratio:   {result.net_sharpe_ratio}")
    print(f"Net max drawdown:   {result.net_max_drawdown_pct}%")
    print(f"Net win rate:       {result.net_win_rate_pct}%")
    print(f"Rebalances:         {result.rebalances}")
    print(f"Net final equity:   ${result.final_equity:,.2f}")
    print(f"Total cost drag:    {result.total_cost_drag_pct}%")
    print("Cost assumptions:")
    print(json.dumps(result.cost_assumptions, indent=2))
    print("Signal diagnostics:")
    print(json.dumps(result.signal_diagnostics, indent=2))
    print("Component correlations:")
    print(json.dumps(result.component_correlations, indent=2))
    print("\nLatest signal:")
    print(json.dumps(result.latest_signal, indent=2))
    return result


def run_signal():
    config = load_config()
    prices, factors = load_strategy_data(config)
    signal = SignalGenerator(config).generate_signal(prices, factors)
    print(json.dumps(signal, indent=2))
    return signal


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["backtest", "signal"], default="backtest")
    args = parser.parse_args()

    if args.mode == "backtest":
        run_backtest_only()
    else:
        run_signal()
