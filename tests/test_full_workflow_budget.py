import unittest

from vpnsci_sustech.full_workflow_budget import (
    FULL_TIER_BUDGETS,
    format_budget_stop_reason,
    resolve_full_tier_budget,
)


class FullWorkflowBudgetTests(unittest.TestCase):
    def test_resolves_full_tier_budgets_from_contract(self):
        self.assertEqual(FULL_TIER_BUDGETS["quick"], 60)
        self.assertEqual(resolve_full_tier_budget("standard"), 180)
        self.assertEqual(resolve_full_tier_budget("Deep"), 400)
        self.assertEqual(resolve_full_tier_budget(" audit "), 1000)

    def test_rejects_unknown_tier_instead_of_guessing(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_full_tier_budget("seed")

        self.assertIn("Unknown full workflow tier", str(ctx.exception))

    def test_formats_budget_stop_reason_from_resolved_budget(self):
        self.assertEqual(format_budget_stop_reason("standard"), "budget_max_papers (180)")


if __name__ == "__main__":
    unittest.main()
