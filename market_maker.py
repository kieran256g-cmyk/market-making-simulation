"""Seeded single-asset market-making research simulator; no live orders."""
import argparse
import csv
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import random


@dataclass(frozen=True)
class Config:
    steps: int = 1000
    seed: int = 7
    initial_mid: float = 100.0
    initial_cash: float = 100000.0
    annual_volatility: float = .2
    half_spread_bps: float = 5.0
    inventory_skew_bps: float = .5
    max_inventory: int = 20
    arrival_probability: float = .3
    fill_decay: float = .1
    fee_bps: float = 0.0

    def __post_init__(self):
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in asdict(self).values()):
            raise ValueError("Settings must be finite numbers")
        if type(self.steps) is not int or not 1 <= self.steps <= 200000:
            raise ValueError("steps must be an integer in 1..200000")
        if type(self.seed) is not int:
            raise ValueError("seed must be an integer")
        if type(self.max_inventory) is not int or not 1 <= self.max_inventory <= 1000:
            raise ValueError("max_inventory must be an integer in 1..1000")
        if not 0 < self.initial_mid <= 1e9 or not 0 < self.initial_cash <= 1e12:
            raise ValueError("Initial mid/cash must be positive and within supported bounds")
        if not 0 <= self.annual_volatility <= 2 or not 0 < self.half_spread_bps <= 1000:
            raise ValueError("Volatility must be in 0..2 and half spread in (0,1000] bps")
        if not 0 <= self.inventory_skew_bps <= 100 or not 0 <= self.arrival_probability <= 1:
            raise ValueError("Skew must be in 0..100 bps and arrival probability in 0..1")
        if not 0 <= self.fill_decay <= 100 or not -100 <= self.fee_bps <= 100:
            raise ValueError("Fill decay must be in 0..100 and fees in -100..100 bps")


def quotes(mid, inventory, config):
    """Positive inventory lowers both quotes to encourage selling."""
    center = mid * math.exp(-inventory * config.inventory_skew_bps / 10000)
    width = config.half_spread_bps / 10000
    return center * (1 - width), center * (1 + width)


def simulate(config=Config()):
    rng = random.Random(config.seed)
    mid, cash, inventory = config.initial_mid, config.initial_cash, 0
    peak = config.initial_cash
    max_drawdown = 0.0
    total_fees, fills, spread_capture = 0.0, 0, 0.0
    rows = []
    for step in range(config.steps):
        quoted_mid = mid
        bid, ask = quotes(mid, inventory, config)
        bid_probability = config.arrival_probability * math.exp(-config.fill_decay * max(0, (mid - bid) / mid * 10000))
        ask_probability = config.arrival_probability * math.exp(-config.fill_decay * max(0, (ask - mid) / mid * 10000))
        bought = inventory < config.max_inventory and rng.random() < bid_probability
        if bought:
            fee = bid * config.fee_bps / 10000
            inventory += 1
            cash -= bid + fee
            total_fees += fee
            spread_capture += quoted_mid - bid
            fills += 1
        sold = inventory > -config.max_inventory and rng.random() < ask_probability
        if sold:
            fee = ask * config.fee_bps / 10000
            inventory -= 1
            cash += ask - fee
            total_fees += fee
            spread_capture += ask - quoted_mid
            fills += 1
        # One row is one daily step. Fills occur at posted quotes before this move.
        vol = config.annual_volatility / math.sqrt(252)
        mid *= math.exp(-.5 * vol**2 + vol * rng.gauss(0, 1))
        if not math.isfinite(mid) or mid <= 0:
            raise ValueError("Simulated price left the supported numeric range; reduce steps or volatility")
        equity = cash + inventory * mid
        peak = max(peak, equity)
        drawdown = equity / peak - 1
        max_drawdown = min(max_drawdown, drawdown)
        rows.append({"step": step + 1, "quoted_mid": quoted_mid, "bid": bid, "ask": ask,
                     "bought": int(bought), "sold": int(sold), "mid": mid,
                     "inventory": inventory, "cash": cash, "equity": equity,
                     "cumulative_fees": total_fees, "drawdown": drawdown})
    summary = {"version": "1.0.0", "synthetic_data": True, "config": asdict(config),
               "ending_equity": rows[-1]["equity"], "net_pnl": rows[-1]["equity"] - config.initial_cash,
               "fills": fills, "fees": total_fees, "spread_capture_at_fill": spread_capture,
               "ending_inventory": inventory, "max_abs_inventory": max(abs(r["inventory"]) for r in rows),
               "max_drawdown": max_drawdown, "valuation": "ending inventory marked at final mid; no liquidation fee"}
    return rows, summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    defaults = asdict(Config())
    for name, value in defaults.items():
        parser.add_argument("--" + name.replace("_", "-"), type=type(value), default=value)
    parser.add_argument("--output", type=Path, default=Path("results/demo"))
    args = vars(parser.parse_args(argv))
    output = args.pop("output")
    try:
        rows, summary = simulate(Config(**args))
        output.mkdir(parents=True, exist_ok=True)
        with (output / "ledger.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2, allow_nan=False))
        print(f"Saved ledger and summary to {output.resolve()}")
    except (OSError, ValueError, OverflowError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
