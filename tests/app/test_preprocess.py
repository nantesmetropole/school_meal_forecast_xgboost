#!/usr/bin/python3
import os
import unittest

import pandas as pd

from app.exceptions import InconsistentDates, OverlappingColumns
from app.preprocess import add_statistical_features, compute_dates_dataframe, compute_min_max_date, cross_product


class TestPreprocess(unittest.TestCase):

    def test_add_statistical_features(self):
        data = {
            "date_str": [
                "2011-02-01",
                "2013-02-01",
                "2014-02-01",
                "2015-02-01",
                "2019-02-01",
                "2020-02-01",
                "2011-02-01",
                "2013-02-01",
                "2014-02-01",
                "2015-02-01",
            ],
            "cantine_nom": ["A"] * 6 + ["B"] * 4,
            "cantine_type": ["M"] * 10,
            "annee_scolaire": [
                "2010-2011",
                "2012-2013",
                "2014-2015",
                "2014-2015",
                "2018-2019",
                "2019-2020",
                "2010-2011",
                "2012-2013",
                "2014-2015",
                "2014-2015",
            ],
            "prevision": [15, 15, 15, 15, 100, 100, 50, 50, 50, 50],
            "effectif": [100] * 6 + [200] * 4,
            "reel": [10, 10, 10, 10, 20, 60, 100, 100, 50, 50],
            "week": [1] * 8 + [2] * 2
        }

        test_data = pd.DataFrame(data)

        expected = pd.DataFrame(data)
        expected["frequentation_prevue"] = [0.15] * 6 + [0.25] * 4
        expected["frequentation_reel"] = [0.1] * 6 + [0.5] * 2 + [0.25] * 2
        pd.testing.assert_frame_equal(add_statistical_features(test_data), expected)

    def test_cross_product(self):
        data_a = pd.DataFrame({"col_1": ["1", "2", "3"], "col_2": ["a", "a", "b"]})
        data_b = pd.DataFrame({"col_3": ["10", "20"], "col_2": ["a", "a"]})
        self.assertRaises(OverlappingColumns,
                          cross_product,
                          data_b,
                          data_a,)

        data_a = pd.DataFrame({"col_1": ["1", "2", "3"], "col_2": ["a", "a", "b"]})
        data_b = pd.DataFrame({"col_3": ["10", "20"], "col_4": ["c", "c"]})
        expected = pd.DataFrame({
            "col_1": ["1", "2", "3", "1", "2", "3"],
            "col_2": ["a", "a", "b", "a", "a", "b"],
            "col_3": ["10", "10", "10", "20", "20", "20"],
            "col_4": ["c", "c", "c", "c", "c", "c"]})
        pd.testing.assert_frame_equal(cross_product(data_b, data_a), expected, check_like=True)

    def test_compute_dates_dataframe(self):
        date_format = "%Y-%m-%d"
        all_data, date_col = compute_dates_dataframe("2017-05-01", "2017-07-20", date_format, "tests/data", include_wednesday=False)
        reference = pd.read_csv("tests/fixtures/test_compute_dates_dataframe.csv", index_col=0)

        pd.testing.assert_frame_equal(all_data, reference, check_like=True)

    def test_compute_min_max_date(self):
        min_date, max_date = compute_min_max_date("2015-05-01", "2017-05-08", "2017-07-20", "%Y-%m-%d", 1)
        min_date_expected = "2015-05-01"
        max_date_expected = "2017-05-01"
        self.assertEqual(min_date_expected, min_date)
        self.assertEqual(max_date_expected, max_date)

        self.assertRaises(InconsistentDates,
                          compute_min_max_date,
                          "2012-05-01", "2015-05-01", "2015-04-01", "%Y-%m-%d", 1)

        self.assertRaises(InconsistentDates,
                          compute_min_max_date,
                          "2017-05-01", "2015-05-01", "2015-05-08", "%Y-%m-%d", 1)

        self.assertRaises(InconsistentDates,
                          compute_min_max_date,
                          "2015-05-03", "2015-05-01", "2015-05-08", "%Y-%m-%d", 1)

        self.assertRaises(InconsistentDates,
                          compute_min_max_date,
                          "2015-05-01", "2015-05-08", "2015-05-22", "%Y-%m-%d", 1)


if __name__ == '__main__':
    unittest.main()
