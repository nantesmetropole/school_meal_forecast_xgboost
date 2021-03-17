#!/usr/bin/python3
import unittest

import pandas as pd

import app.calculators as calc


class TestSchoolYear(unittest.TestCase):
    # pylint: disable=too-many-statements
    def test_add_feature_school_year(self):
        dtf = pd.DataFrame({
            'index_date': ["2017-09-01", "2017-09-04", "2017-09-05", "2018-02-25", "2018-05-01", "2018-10-01"],
            'date_col': ["2017-09-01", "2017-09-04", "2017-09-05", "2018-02-25", "2018-05-01", "2018-10-01"]})
        dtf.set_index('index_date', inplace=True)

        train_dtf = calc.add_feature_school_year(dtf.copy(), 'date_col', "%Y-%m-%d", "tests/data")

        self.assertTrue('date_col' in train_dtf)
        self.assertEqual(train_dtf.shape, (6, 2))
        self.assertEqual(train_dtf[train_dtf['annee_scolaire'] == "ete"]['date_col'].iloc[0], '2017-09-01')
        self.assertEqual(train_dtf[train_dtf['annee_scolaire'] == "2017-2018"]['date_col'].iloc[0], '2017-09-04')
        self.assertEqual(train_dtf[train_dtf['annee_scolaire'] == "2017-2018"]['date_col'].iloc[1], '2017-09-05')
        self.assertEqual(train_dtf[train_dtf['annee_scolaire'] == "2017-2018"]['date_col'].iloc[2], '2018-02-25')
        self.assertEqual(train_dtf[train_dtf['annee_scolaire'] == "2017-2018"]['date_col'].iloc[3], '2018-05-01')
        self.assertEqual(train_dtf[train_dtf['annee_scolaire'] == "2018-2019"]['date_col'].iloc[0], '2018-10-01')


if __name__ == '__main__':
    unittest.main()
