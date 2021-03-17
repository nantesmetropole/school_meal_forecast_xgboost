#!/usr/bin/python3
import unittest

import pandas as pd

import app.calculators as calc


class TestHolidaysInAgo(unittest.TestCase):
    # pylint: disable=too-many-statements
    def test_add_feature_holidays_in_ago(self):
        dtf = pd.DataFrame({
            'index_date': ["2017-09-01", "2017-09-04", "2017-09-05", "2018-02-25", "2019-05-07", "2019-05-08", "2019-09-07"],
            'date_col': ["2017-09-01", "2017-09-04", "2017-09-05", "2018-02-25", "2019-05-07", "2019-05-08", "2019-09-07"]})
        dtf.set_index('index_date', inplace=True)

        train_dtf = calc.add_feature_holidays_in_ago(dtf.copy(), 'date_col', "%Y-%m-%d", "tests/data")

        self.assertTrue('holidays_in' in train_dtf)
        self.assertTrue('holidays_ago' in train_dtf)
        self.assertTrue('vacances_nom' in train_dtf)
        self.assertEqual(train_dtf.shape, (7, 4))

        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "ecole"]['date_col'].iloc[0], '2017-09-04')
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "ecole"]['holidays_in'].iloc[0], 47)
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "ecole"]['holidays_ago'].iloc[0], 1)
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "ecole"]['date_col'].iloc[1], '2017-09-05')
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "ecole"]['holidays_in'].iloc[1], 46)
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "ecole"]['holidays_ago'].iloc[1], 2)
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "ecole"]['date_col'].iloc[2], '2019-05-07')
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "ecole"]['holidays_in'].iloc[2], 61)
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "ecole"]['holidays_ago'].iloc[2], 16)
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "ecole"]['date_col'].iloc[3], '2019-05-08')
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "ecole"]['holidays_in'].iloc[3], 60)
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "ecole"]['holidays_ago'].iloc[3], 17)
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "ecole"]['date_col'].iloc[4], '2019-09-07')
        # latest day in the dataset, thus next holidays cannot be computed
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "ecole"]['holidays_in'].iloc[4], 0)
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "ecole"]['holidays_ago'].iloc[4], 6)
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "Vacances d'Ete"]['date_col'].iloc[0], '2017-09-01')
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "Vacances d'Ete"]['holidays_in'].iloc[0], 0)
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "Vacances d'Ete"]['holidays_ago'].iloc[0], 0)
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "Vacances d'Hiver"]['date_col'].iloc[0], '2018-02-25')
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "Vacances d'Hiver"]['holidays_in'].iloc[0], 0)
        self.assertEqual(train_dtf[train_dtf['vacances_nom'] == "Vacances d'Hiver"]['holidays_ago'].iloc[0], 0)


if __name__ == '__main__':
    unittest.main()
