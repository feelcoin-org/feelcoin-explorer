"""Mocked analytics tests; no daemon or network required."""
import unittest
from unittest.mock import patch
import explorer


class ExplorerAnalyticsTests(unittest.TestCase):
    def setUp(self):
        explorer._ANALYTICS_CACHE.clear()

    def test_network_samples_are_bounded_and_target_based(self):
        def header(height):
            return {"result": {"block_header": {
                "timestamp": 1_700_000_000 + height * 120,
                "difficulty": 120_000,
                "height": height
            }}}
        with patch.object(explorer, "get_info", return_value={"height": 101, "target": 120}), \
             patch.object(explorer, "get_block_header", side_effect=header) as lookup:
            result = explorer.network_analytics("7d")
            self.assertLessEqual(len(result["samples"]), 25)
            self.assertEqual(len(result["samples"]), lookup.call_count)
            self.assertTrue(result["sampled_by_target_blocks"])
            self.assertEqual(result["samples"][-1]["hashrate"], 1000)
            self.assertEqual(result["samples"][-1]["avg_block_seconds"], 120)
            explorer.network_analytics("7d")
            self.assertEqual(lookup.call_count, len(result["samples"]), "Expected cache hit")

    def test_bad_window_is_rejected_without_rpc_call(self):
        with patch.object(explorer, "get_info") as info:
            with self.assertRaises(ValueError):
                explorer.network_analytics("1000d")
            info.assert_not_called()

    def test_economics_distinguishes_estimate_from_verified_outputs(self):
        atom = 10**12
        def coins(height, count):
            if height == 0 and count == 590:
                n = 200
            elif height == 280 and count == 720:
                n = 100
            else:
                raise AssertionError((height,count))
            return {"result": {"status": "OK", "emission_amount": n * atom}}
        verified = {"result": {"reward_breakdown": {
            "miner": int(.294*atom),
            "treasury": int(.006*atom)
        }}}
        with patch.object(explorer, "get_info", return_value={"height":1000}), \
             patch.object(explorer, "get_emitted_supply",
                          return_value={"emitted_atomic":1000*atom}), \
             patch.object(explorer, "get_coinbase_tx_sum", side_effect=coins), \
             patch.object(explorer, "get_block", return_value={}), \
             patch.object(explorer, "enrich_block_reward", return_value=verified):
            result = explorer.economics_analytics()
        self.assertEqual(result["issued_feel"], "1000.000000000000")
        self.assertEqual(result["recent_emission_feel"], "100.000000000000")
        self.assertEqual(result["estimated_treasury_feel"], "16.000000000000")
        self.assertEqual(result["latest_verified_split"]["treasury_feel"], "0.006000000000")
        self.assertTrue(result["treasury_estimate_only"])
        self.assertFalse(result["treasury_balance_known"])
        self.assertTrue(result["fees_excluded"])

    def test_no_treasury_before_activation(self):
        atom = 10**12
        with patch.object(explorer, "get_info", return_value={"height":1}), \
             patch.object(explorer, "get_emitted_supply",
                          return_value={"emitted_atomic":atom}), \
             patch.object(explorer, "get_coinbase_tx_sum",
                          return_value={"result":{"status":"OK","emission_amount":atom}}), \
             patch.object(explorer, "get_block") as get_block:
            result = explorer.economics_analytics()
        self.assertEqual(result["estimated_treasury_feel"],"0.000000000000")
        self.assertIsNone(result["latest_verified_split"])
        get_block.assert_not_called()


if __name__ == "__main__":
    unittest.main()
