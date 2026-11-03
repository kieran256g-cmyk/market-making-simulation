# Market Making Simulation — v1

A reproducible, single-asset market-making simulator with explicit cash and
inventory accounting. Python 3.10+; standard library only. It generates synthetic
prices and fills and never connects to a broker.

## Quick start

```bash
python market_maker.py
python market_maker.py --steps 2000 --seed 42 --max-inventory 10 --output results/experiment-42
python market_maker.py --half-spread-bps 8 --inventory-skew-bps 1 --fee-bps 0.5
python -m unittest discover -s tests -v
```

Outputs: `ledger.csv` and `summary.json` under `results/demo` by default.
Rerunning replaces these files; choose a new `--output` to preserve experiments.

## Event sequence and accounting

Each step represents one trading day:

1. Calculate a reservation price from the current mid and inventory.
2. Post a bid and ask around that price.
3. Sample a one-unit customer buy/sell independently, subject to inventory limits.
4. Charge the configured proportional maker fee on each fill.
5. Move the mid using a zero-drift geometric Brownian process and mark inventory.

Reservation price is `mid * exp(-inventory * skew_bps / 10000)`. Bid/ask are
reservation price times `1 -/+ half_spread_bps / 10000`. A long inventory lowers
both quotes; a short inventory raises them. Each side's fill probability is
`arrival_probability * exp(-fill_decay * max(distance_bps, 0))`, where distance
is measured from the current mid. Both sides can fill within one step; buys are
processed first. Fills always occur at the quoted prices.

`equity = cash + inventory * mid`. Cash changes by the executed notional and fee.
The summary includes marked net P&L, maximum drawdown from initial equity, fill
count, inventory usage, total fees, and spread capture measured at the pre-move
mid. Spread capture is a diagnostic and can differ from net P&L. Final inventory
is marked at mid; no terminal liquidation transaction is assumed.

## Parameters

| Argument | Default | Meaning |
| --- | --- | --- |
| `--steps` | 1000 | Daily simulation steps, maximum 200000 |
| `--seed` | 7 | Local pseudorandom seed |
| `--initial-mid` | 100 | Starting mid price |
| `--initial-cash` | 100000 | Starting cash |
| `--annual-volatility` | 0.2 | Annual volatility, decimal, 252 steps/year |
| `--half-spread-bps` | 5 | Quote half-width in basis points |
| `--inventory-skew-bps` | 0.5 | Reservation-price skew per inventory unit |
| `--max-inventory` | 20 | Absolute inventory cap, unit lots |
| `--arrival-probability` | 0.3 | Per-side arrival probability at/inside mid |
| `--fill-decay` | 0.1 | Decay per basis point of quote distance |
| `--fee-bps` | 0 | Notional fee; negative values model rebates |

Use `python market_maker.py --help` for the full CLI. Import `Config`, `quotes`
and `simulate` for experiments. `simulate` returns `(ledger_rows, summary)`.

## Limitations

The fill process is deliberately simple: independent Bernoulli customer flow,
no queue priority, intraday order book, adverse selection, latency, partial fills,
tick size, impact or competition. A day permits at most one fill per side.
Price moves follow fills, so fills contain no information about the next move.
Inventory limits are enforced; cash can become negative and financing/margin are
not modelled. This model does not establish that a strategy will be profitable.

Next extensions: finer time resolution, event-driven order flow, adverse selection,
queue simulation, inventory penalties, and calibrated historical replay.
