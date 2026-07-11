import unittest

from agenticwisp import pricing


class PricingTest(unittest.TestCase):
    def test_rate_exact_prefix_default(self):
        self.assertEqual(pricing.rate("claude-opus-4-8"), (5.0, 25.0))
        self.assertEqual(pricing.rate("claude-haiku-4-5"), (1.0, 5.0))
        self.assertEqual(pricing.rate("claude-opus-4-8-20250101"), (5.0, 25.0))  # 前缀
        self.assertEqual(pricing.rate("gpt-4"), (5.0, 25.0))                     # default

    def test_cost_components(self):
        self.assertAlmostEqual(pricing.cost("claude-opus-4-8", 1_000_000, 0, 0, 0), 5.0)
        self.assertAlmostEqual(pricing.cost("claude-opus-4-8", 0, 1_000_000, 0, 0), 25.0)
        self.assertAlmostEqual(pricing.cost("claude-opus-4-8", 0, 0, 1_000_000, 0), 0.5)   # cache_read 0.1x
        self.assertAlmostEqual(pricing.cost("claude-opus-4-8", 0, 0, 0, 1_000_000), 6.25)  # cache_write 1.25x
        self.assertAlmostEqual(pricing.cost("claude-haiku-4-5", 1_000_000, 0, 0, 0), 1.0)
        self.assertAlmostEqual(pricing.cost("claude-fable-5", 1_000_000, 0, 0, 0), 10.0)

    def test_synthetic_and_zero(self):
        self.assertEqual(pricing.cost("<synthetic>", 0, 0, 0, 0), 0.0)
