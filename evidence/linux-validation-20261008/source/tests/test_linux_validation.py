"""Check experimental separation, balancing and diagnostic exclusions."""
from collections import Counter, defaultdict
import unittest

from experiments.linux_validation import case_definitions, execution_plan


class LinuxProtocolTests(unittest.TestCase):
    def test_original_workflow_positions_are_balanced_and_threshold_is_frozen(self):
        cases = case_definitions()
        primary = [case for case in cases if case['dataset'] == 'synthetic' and case['phase'] == 'evaluation']
        self.assertEqual(len(primary), 8)
        plan = execution_plan(primary)
        self.assertEqual(len(plan), 8 * 6 * 9)
        positions = defaultdict(list)
        identities = set()
        for row in plan:
            self.assertEqual(row['threshold'], 4096)
            identity = (row['scenario'], row['model'], row['trial_kind'], row['trial'])
            self.assertNotIn(identity, identities)
            identities.add(identity)
            if row['trial_kind'] == 'measured' and row['trial'] <= 6:
                positions[(row['scenario'], row['model'])].append(row['execution_order'])
        for observed in positions.values():
            self.assertEqual(sorted(observed), list(range(1, 7)))

    def test_threshold_supplement_uses_both_sides_of_frozen_candidate(self):
        cases = [case for case in case_definitions() if case['phase'] == 'threshold-supplement']
        counts = [case['spec']['commits'] * case['spec']['changes_per_commit'] for case in cases]
        self.assertLess(min(counts), 16384)
        self.assertGreater(max(counts), 16384)
        for case in cases:
            self.assertEqual(case['threshold'], 16384)
            self.assertEqual(set(case['models']), {'revon-log', 'revon-m', 'revon-h'})

    def test_million_row_feasibility_is_excluded_from_measured_comparisons(self):
        plan = execution_plan(case_definitions())
        scale = [row for row in plan if row['phase'] == 'scale-feasibility']
        self.assertEqual(len(scale), 3)
        self.assertTrue(all(row['trial_kind'] == 'diagnostic' for row in scale))
        self.assertEqual(Counter(row['trial_kind'] for row in plan),
                         {'warmup': 114, 'measured': 399, 'diagnostic': 3})


if __name__ == '__main__':
    unittest.main()
