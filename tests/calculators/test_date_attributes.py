#!/usr/bin/python3
from datetime import datetime
import unittest

import pandas as pd

import app.calculators as calc


class TestDateAttributes(unittest.TestCase):
    # pylint: disable=no-self-use
    def _test_date_calcs(self, test_dict, expected_calc_features, col_names):
        test_dtf = pd.DataFrame(test_dict)

        df_with_calc_date_train = calc.date_attributes.add_feature_date_attributes(
            dtf=test_dtf.copy(),
            date_col='date_str',
            attributes_list=col_names,
            date_format="%Y-%m-%d")

        expected_cols = test_dict.copy()
        expected_cols.update(expected_calc_features)
        expected_dtf = pd.DataFrame(expected_cols)
        pd.testing.assert_frame_equal(expected_dtf, df_with_calc_date_train)

    def test_calc_date_attribute_invalid(self):
        self.assertRaises(ValueError, self._test_date_calcs, {'date_str': [None]}, {'day': [-1]}, ["day"])
        self.assertRaises(ValueError, self._test_date_calcs, {'date_str': [datetime(1980, 9, 6)]}, {'day': [-1]}, ["day"])
        self.assertRaises(ValueError, self._test_date_calcs, {'date_str': ["6/9/1980"]}, {'day': [-1]}, ["day"])
        self.assertRaises(ValueError, self._test_date_calcs, {'date_str': [0.4]}, {'day': [-1]}, ["day"])

    def test_calc_date_attribute_future(self):
        date = datetime(datetime.now().year + 2, 4, 26)
        test_dict = {'date_str': [date]}
        self._test_date_calcs(test_dict, {'day': [26]}, ["day"])
        self._test_date_calcs(test_dict, {'month': [4]}, ["month"])

    def test_month_and_week(self):
        test_dict = {'date_str': [datetime(2019, 5, 12), datetime(2019, 7, 31)]}
        self._test_date_calcs(test_dict, {'month': [5, 7]}, ["month"])

        test_dict = {'date_str': ["2019-05-12", "2019-07-31"]}
        self._test_date_calcs(test_dict, {'month': [5, 7]}, ["month"])

        # week
        test_dict = {'date_str': [datetime(2019, 5, 12), datetime(2019, 7, 31)]}
        self._test_date_calcs(test_dict, {'week': [19, 31]}, ["week"])

        test_dict = {'date_str': ["2019-05-12", "2019-07-31"]}
        self._test_date_calcs(test_dict, {'week': [19, 31]}, ["week"])

    def test_all_date_attributes(self):
        test_dict = {'date_str': [datetime(2019, 5, 12), datetime(2020, 7, 31)]}
        added_cols = {'day': [12, 31], 'month': [5, 7], 'weekday': [6, 4], 'year': [2019, 2020]}
        self._test_date_calcs(test_dict, added_cols, ["day", "month", "weekday", "year"])


if __name__ == '__main__':
    unittest.main()
