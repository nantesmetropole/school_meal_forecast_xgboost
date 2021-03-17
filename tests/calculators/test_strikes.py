#!/usr/bin/python3
import unittest

import pandas as pd

import app.calculators as calc


class TestStrikes(unittest.TestCase):
    # pylint: disable=too-many-statements
    def test_add_feature_strikes(self):
        dtf = pd.DataFrame({
            'index_date': ["2011-12-15", "2017-09-04"],
            'date_col': ["2011-12-15", "2017-09-04"]})
        dtf.set_index('index_date', inplace=True)

        train_dtf = calc.add_feature_strikes(dtf.copy(), "%Y-%m-%d", "tests/data")

        self.assertTrue('date_col' in train_dtf)
        self.assertEqual(train_dtf.shape, (2, 2))
        self.assertEqual(train_dtf[train_dtf['greve'] == 0]['date_col'].iloc[0], '2017-09-04')
        self.assertEqual(train_dtf[train_dtf['greve'] == 1]['date_col'].iloc[0], '2011-12-15')


if __name__ == '__main__':
    unittest.main()
