import math
import unittest
from market_maker import Config, quotes, simulate


class SimulatorTests(unittest.TestCase):
    def test_seed_reproducibility(self):
        self.assertEqual(simulate(Config(steps=50)), simulate(Config(steps=50)))

    def test_no_fills_preserves_cash(self):
        rows, summary = simulate(Config(steps=30, arrival_probability=0))
        self.assertEqual(summary["net_pnl"], 0)
        self.assertTrue(all(r["inventory"] == 0 for r in rows))

    def test_spread_accounting_and_fees(self):
        config = Config(steps=20, annual_volatility=0, arrival_probability=1,
                        fill_decay=0, inventory_skew_bps=0, fee_bps=1)
        rows, summary = simulate(config)
        bid, ask = quotes(100, 0, config)
        expected = 20 * (ask - bid - (ask + bid) / 10000)
        self.assertAlmostEqual(summary["net_pnl"], expected)
        self.assertEqual(summary["fills"], 40)
        self.assertEqual(summary["ending_inventory"], 0)

    def test_inventory_limit_and_ledger_identity(self):
        config = Config(steps=500, max_inventory=2, arrival_probability=.7)
        rows, summary = simulate(config)
        for row in rows:
            self.assertLessEqual(abs(row["inventory"]), 2)
            self.assertAlmostEqual(row["equity"], row["cash"] + row["inventory"] * row["mid"])
            self.assertTrue(all(math.isfinite(value) for value in row.values()))
            self.assertLess(row["bid"], row["ask"])

    def test_quote_skew_reduces_inventory(self):
        config = Config()
        flat = quotes(100, 0, config)
        long = quotes(100, 10, config)
        short = quotes(100, -10, config)
        self.assertLess(long[0], flat[0])
        self.assertLess(long[1], flat[1])
        self.assertGreater(short[0], flat[0])

    def test_invalid_config(self):
        for args in ({"steps": 0}, {"max_inventory": -1}, {"annual_volatility": float("nan")},
                     {"arrival_probability": 2}, {"steps": True}):
            with self.assertRaises(ValueError):
                Config(**args)


if __name__ == "__main__":
    unittest.main()
