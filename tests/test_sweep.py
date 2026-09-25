"""The parts of a sweep that fail silently: what it skips and what it records."""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harvester import sweep, universe  # noqa: E402


class PlanTest(unittest.TestCase):
    def test_every_pair_when_the_ledger_is_empty(self):
        got = sweep.plan(["A", "B"], ["1D", "60"])
        self.assertEqual(len(got), 4)
        # Symbol-major: an interrupted sweep leaves whole symbols finished.
        self.assertEqual(got.jobs[:2], [("A", "1D"), ("A", "60")])

    def test_a_recent_pull_is_skipped(self):
        now = time.time()
        ledger = {sweep.key("A", "1D"): {"at": now, "error": ""}}
        got = sweep.plan(["A"], ["1D", "60"], ledger, now=now)
        self.assertEqual(got.jobs, [("A", "60")])
        self.assertEqual(got.fresh, [("A", "1D")])

    def test_a_stale_pull_comes_back(self):
        now = time.time()
        ledger = {sweep.key("A", "1D"): {"at": now - 2 * 86400, "error": ""}}
        got = sweep.plan(["A"], ["1D"], ledger, now=now)
        self.assertEqual(got.jobs, [("A", "1D")])

    def test_a_failure_is_retried_even_when_recent(self):
        now = time.time()
        ledger = {sweep.key("A", "1D"): {"at": now, "error": "no such symbol"}}
        self.assertEqual(sweep.plan(["A"], ["1D"], ledger, now=now).jobs,
                         [("A", "1D")])

    def test_redo_ignores_the_ledger(self):
        now = time.time()
        ledger = {sweep.key("A", "1D"): {"at": now, "error": ""}}
        self.assertEqual(
            sweep.plan(["A"], ["1D"], ledger, redo=True, now=now).jobs,
            [("A", "1D")])

    def test_an_hour_is_the_floor_for_fast_timeframes(self):
        # Without a floor a 1-minute series would be re-pulled every minute and
        # the sweep would never reach the second symbol.
        self.assertGreaterEqual(sweep.stale_after("1"), 3600.0)
        self.assertGreaterEqual(sweep.stale_after("1D"), 86400.0)


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "_ledger_tmp")
        os.makedirs(self.dir, exist_ok=True)

    def tearDown(self):
        for name in os.listdir(self.dir):
            os.remove(os.path.join(self.dir, name))
        os.rmdir(self.dir)

    def test_round_trip(self):
        sweep.save_ledger({"A|1D": {"at": 1.0, "bars": 5}}, self.dir)
        self.assertEqual(sweep.load_ledger(self.dir)["A|1D"]["bars"], 5)

    def test_a_corrupt_ledger_costs_a_re_pull_not_the_run(self):
        with open(sweep.ledger_path(self.dir), "w") as fh:
            fh.write("{not json")
        self.assertEqual(sweep.load_ledger(self.dir), {})

    def test_missing_ledger_is_empty(self):
        self.assertEqual(sweep.load_ledger(self.dir), {})


class RunTest(unittest.TestCase):
    """run() with a stubbed puller: no network, just the bookkeeping."""

    def setUp(self):
        self.dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "_run_tmp")
        os.makedirs(self.dir, exist_ok=True)

    def tearDown(self):
        for name in os.listdir(self.dir):
            os.remove(os.path.join(self.dir, name))
        os.rmdir(self.dir)

    def test_a_failing_symbol_does_not_stop_the_sweep(self):
        def puller(symbol, timeframe, **kw):
            if symbol == "BAD":
                return sweep.Result(symbol, timeframe, error="symbol_error")
            return sweep.Result(symbol, timeframe, bars=10, added=10,
                                start="2020-01-01", end="2020-01-10")

        results = sweep.run(["BAD", "GOOD"], ["1D"], pause=0, directory=self.dir,
                            puller=puller)
        self.assertEqual(len(results), 2)
        summary = sweep.summarise(results)
        self.assertEqual((summary["ok"], summary["failed"]), (1, 1))
        self.assertEqual(summary["bars"], 10)

    def test_the_ledger_is_written_as_it_goes_not_at_the_end(self):
        seen = []

        def puller(symbol, timeframe, **kw):
            # What the ledger holds mid-run is what a crash would leave behind.
            seen.append(len(sweep.load_ledger(self.dir)))
            return sweep.Result(symbol, timeframe, bars=1)

        sweep.run(["A", "B", "C"], ["1D"], pause=0, directory=self.dir,
                  puller=puller)
        self.assertEqual(seen, [0, 1, 2])


class UniverseTest(unittest.TestCase):
    def test_groups_resolve_and_do_not_repeat(self):
        every = universe.group(["all"])
        self.assertEqual(len(every), len(set(every)))
        self.assertIn("AMEX:SPY", every)

    def test_symbols_are_upper_cased_and_deduped_in_order(self):
        self.assertEqual(universe.dedupe([" nasdaq:aapl ", "NASDAQ:AAPL", "X"]),
                         ["NASDAQ:AAPL", "X"])

    def test_an_unknown_group_says_what_is_available(self):
        with self.assertRaises(Exception) as caught:
            universe.group(["nope"])
        self.assertIn("etfs", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
