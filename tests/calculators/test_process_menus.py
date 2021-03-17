#!/usr/bin/python3
import json
import unittest

import pandas as pd

import app.calculators as calc


class TestMenus(unittest.TestCase):
    # pylint: disable=too-many-statements
    def test_process_menus(self):
        dtf = pd.DataFrame({
            'index_date': ["2011-12-15", "2016-09-04", "2016-09-05", "2016-09-06", "2016-09-07"],
            'date_col': ["2011-12-15", "2016-09-04", "2016-09-05", "2016-09-06", "2016-09-07"]})
        dtf.set_index('index_date', inplace=True)

        train_dtf = calc.add_feature_special_meals(dtf.copy(), "date_col", "%Y-%m-%d", "tests/data")

        dict_special_dishes = {}
        with open("tests/data/calculators/menus.json") as f_in:
            dict_special_dishes = json.load(f_in)

        self.assertEqual(train_dtf.shape, (5, 2 + len(list(dict_special_dishes.keys()))))

        for col in list(dict_special_dishes.keys()):
            self.assertTrue(col in train_dtf)

        pd.testing.assert_frame_equal(pd.read_csv("tests/fixtures/menus_dataset.csv", index_col=0), train_dtf)


if __name__ == '__main__':
    unittest.main()
