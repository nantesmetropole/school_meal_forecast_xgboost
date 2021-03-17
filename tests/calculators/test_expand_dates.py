#!/usr/bin/python3
import unittest

import pandas as pd

import app.calculators as calc


class TestExpandDates(unittest.TestCase):
    # pylint: disable=too-many-statements
    def test_generate_dates_df(self):
        begin = "2020-01-01"
        end = "2020-01-08"
        date_format = "%Y-%m-%d"
        col_name = "date_generated"
        data = calc.generate_dates_df(begin, end, date_format, col_name)

        # read external fixture csv
        def _parser(date):
            return pd.datetime.strptime(date, date_format)

        reference = pd.read_csv("./tests/fixtures/expand_dates.csv",
                                parse_dates=['date_index'],
                                date_parser=_parser,
                                index_col=0)

        self.assertEqual(len(data), 8 + 7 * 10)
        pd.testing.assert_frame_equal(data, reference)


if __name__ == '__main__':
    unittest.main()
