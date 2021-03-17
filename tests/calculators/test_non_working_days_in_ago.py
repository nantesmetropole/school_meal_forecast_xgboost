#!/usr/bin/python3
import unittest

import pandas as pd

import app.calculators as calc


class TestNonWorkingDaysInAgo(unittest.TestCase):
    # pylint: disable=too-many-statements
    def test_add_feature_non_working_days_in_ago(self):
        dtf = pd.DataFrame({
            'index_date': ["2017-09-04", "2017-09-05", "2019-05-07", "2019-05-08", "2019-07-15"],
            'date_col': ["2017-09-04", "2017-09-05", "2019-05-07", "2019-05-08", "2019-07-15"]})
        dtf.set_index('index_date', inplace=True)

        train_dtf = calc.add_feature_non_working_days_in_ago(dtf.copy(), 'date_col', "%Y-%m-%d", "tests/data")

        print(train_dtf)
        self.assertTrue('nom_jour_ferie' in train_dtf)
        self.assertTrue('non_working_in' in train_dtf)
        self.assertTrue('non_working_ago' in train_dtf)
        self.assertEqual(train_dtf.shape, (5, 4))

        self.assertEqual(train_dtf[train_dtf['nom_jour_ferie'] == "jour_ouvre"]['date_col'].iloc[0], '2017-09-04')
        self.assertEqual(train_dtf[train_dtf['nom_jour_ferie'] == "jour_ouvre"]['non_working_in'].iloc[0], 58)
        self.assertEqual(train_dtf[train_dtf['nom_jour_ferie'] == "jour_ouvre"]['non_working_ago'].iloc[0], 0)
        self.assertEqual(train_dtf[train_dtf['nom_jour_ferie'] == "jour_ouvre"]['date_col'].iloc[1], '2017-09-05')
        self.assertEqual(train_dtf[train_dtf['nom_jour_ferie'] == "jour_ouvre"]['non_working_in'].iloc[1], 57)
        self.assertEqual(train_dtf[train_dtf['nom_jour_ferie'] == "jour_ouvre"]['non_working_ago'].iloc[1], 0)
        self.assertEqual(train_dtf[train_dtf['nom_jour_ferie'] == "jour_ouvre"]['date_col'].iloc[2], '2019-05-07')
        self.assertEqual(train_dtf[train_dtf['nom_jour_ferie'] == "jour_ouvre"]['non_working_in'].iloc[2], 1)
        self.assertEqual(train_dtf[train_dtf['nom_jour_ferie'] == "jour_ouvre"]['non_working_ago'].iloc[2], 6)
        self.assertEqual(train_dtf[train_dtf['nom_jour_ferie'] == "jour_ouvre"]['date_col'].iloc[3], '2019-07-15')
        # latest day in the dataset, thus next non_working_in cannot be computed
        self.assertEqual(train_dtf[train_dtf['nom_jour_ferie'] == "jour_ouvre"]['non_working_in'].iloc[3], 0)
        self.assertEqual(train_dtf[train_dtf['nom_jour_ferie'] == "jour_ouvre"]['non_working_ago'].iloc[3], 1)

        self.assertEqual(train_dtf[train_dtf['nom_jour_ferie'] == "Victoire des alliés"]['date_col'].iloc[0], '2019-05-08')
        self.assertEqual(train_dtf[train_dtf['nom_jour_ferie'] == "Victoire des alliés"]['non_working_in'].iloc[0], 0)
        self.assertEqual(train_dtf[train_dtf['nom_jour_ferie'] == "Victoire des alliés"]['non_working_ago'].iloc[0], 0)


if __name__ == '__main__':
    unittest.main()
