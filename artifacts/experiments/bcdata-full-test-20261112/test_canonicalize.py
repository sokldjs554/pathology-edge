"""Synthetic source-defect regression checks; no dataset contents embedded."""
import unittest

import numpy as np

from canonicalize import canonicalize


class CanonicalizationTests(unittest.TestCase):
    def test_empty_float_array_adds_no_positive_point(self):
        result = canonicalize(np.array([], dtype=float), np.array([[3, 4]]))
        self.assertEqual(result["points"].tolist(), [[3, 4]])
        self.assertEqual(result["truth"].tolist(), [1])
        self.assertTrue(result["class_counts"][0]["empty_shape_normalized"])
        self.assertEqual(result["excluded"], [])

    def test_duplicates_keep_first_order_and_conflicts_remove_all_records(self):
        result = canonicalize(np.array([[5, 6], [1, 2], [5, 6], [8, 9], [8, 9]]),
                              np.array([[8, 9], [10, 11]]))
        self.assertEqual(result["points"].tolist(), [[5, 6], [1, 2], [10, 11]])
        self.assertEqual(result["truth"].tolist(), [0, 0, 1])
        self.assertEqual(result["duplicates"], [{"class": 0, "source_row_index": 2,
                                                "first_source_row_index": 0, "point": [5, 6]}])
        self.assertEqual(result["cross_label_conflicting_locations"], 1)
        self.assertEqual(len(result["excluded"]), 3)
        self.assertTrue(all(r["reason"] == "cross_label_conflict" for r in result["excluded"]))

    def test_fractional_nonfinite_and_bounds_excluded_without_rounding(self):
        result = canonicalize(np.array([[1.5, 2], [np.nan, 3], [640, 0], [-1, 0], [639, 639]]),
                              np.empty((0, 2), dtype=int))
        self.assertEqual(result["points"].tolist(), [[639, 639]])
        self.assertEqual([r["reason"] for r in result["excluded"]],
                         ["noninteger", "nonfinite", "out_of_bounds", "out_of_bounds"])

    def test_bad_nonempty_shape_is_not_reinterpreted(self):
        with self.assertRaises(ValueError):
            canonicalize(np.array([1, 2]), np.empty((0, 2)))


if __name__ == "__main__":
    unittest.main()
