#!/usr/bin/python3
import datetime
import unittest

import pandas as pd

import app.calculators as calc
from app.calculators.events_countdown import Events, \
    compute_events_dates, add_countdown_ago, add_countdown_in, \
    compute_first_weekday_of_a_month, compute_last_weekday_of_a_month


class TestSpecialDaysCountdown(unittest.TestCase):
    def _test_events_countdown(self, use_string):
        x_m1y = datetime.datetime(2018, 12, 24)
        christmas = datetime.datetime(2019, 12, 24)
        x_p9 = christmas + datetime.timedelta(days=9)
        x_p2 = christmas + datetime.timedelta(days=2)
        x_p1 = christmas + datetime.timedelta(days=1)
        x_m1 = christmas + datetime.timedelta(days=-1)
        x_m2 = christmas + datetime.timedelta(days=-2)
        x_m3 = christmas + datetime.timedelta(days=-3)

        if use_string:
            x_m1y = x_m1y.strftime("%Y-%m-%d")
            christmas = christmas.strftime("%Y-%m-%d")
            x_p9 = x_p9.strftime("%Y-%m-%d")
            x_p2 = x_p2.strftime("%Y-%m-%d")
            x_p1 = x_p1.strftime("%Y-%m-%d")
            x_m1 = x_m1.strftime("%Y-%m-%d")
            x_m2 = x_m2.strftime("%Y-%m-%d")
            x_m3 = x_m3.strftime("%Y-%m-%d")

        dtf = pd.DataFrame({'date': [x_m1y, x_m3, x_m2, x_m1, christmas, x_p1, x_p2, x_p9]})

        train_dtf = calc.add_feature_events_countdown(dtf.copy(), 'date', "%Y-%m-%d")
        self.assertTrue("Events.RAMADAN_in" in train_dtf)
        self.assertTrue("Events.RAMADAN_ago" in train_dtf)
        # 2 columns for the original data (date) and 14 columns for the 16 special dates
        self.assertEqual(train_dtf.shape, (8, 15))

        self.assertEqual(train_dtf[train_dtf['date'] == christmas]["Events.EPIPHANIE_ago"].iloc[0], 13)
        self.assertEqual(train_dtf[train_dtf['date'] == x_p9]["Events.EPIPHANIE_ago"].iloc[0], 4)
        self.assertEqual(train_dtf[train_dtf['date'] == x_p2]["Events.EPIPHANIE_ago"].iloc[0], 11)
        self.assertEqual(train_dtf[train_dtf['date'] == x_p1]["Events.EPIPHANIE_ago"].iloc[0], 12)
        self.assertEqual(train_dtf[train_dtf['date'] == x_m1]["Events.EPIPHANIE_ago"].iloc[0], 14)
        self.assertEqual(train_dtf[train_dtf['date'] == x_m2]["Events.EPIPHANIE_ago"].iloc[0], 15)
        self.assertEqual(train_dtf[train_dtf['date'] == x_m3]["Events.EPIPHANIE_ago"].iloc[0], 16)

    def test_events_countdown(self):
        self._test_events_countdown(False)
        self._test_events_countdown(True)

    def test_compute_special_dates(self):
        special_dates = compute_events_dates([2018])
        self.assertEqual(7, len(special_dates))
        self.assertEqual(1, len(special_dates[Events.RAMADAN]))

        special_dates = compute_events_dates([2017, 2019])
        self.assertEqual(7, len(special_dates))
        self.assertEqual(2, len(special_dates[Events.RAMADAN]))
        self.assertEqual(5, special_dates[Events.RAMADAN][0].month)
        self.assertEqual(5, special_dates[Events.RAMADAN][1].month)
        self.assertEqual(27, special_dates[Events.RAMADAN][0].day)
        self.assertEqual(6, special_dates[Events.RAMADAN][1].day)
        self.assertEqual(2017, special_dates[Events.RAMADAN][0].year)
        self.assertEqual(2019, special_dates[Events.RAMADAN][1].year)

    def test_add_countdown(self):
        test_event_dates = {}
        test_event_dates["st_nicolas"] = {datetime.date(2017, 12, 6), datetime.date(2018, 12, 6), datetime.date(2019, 12, 6)}
        test_event_dates["noel"] = {datetime.date(2017, 12, 24), datetime.date(2018, 12, 24), datetime.date(2019, 12, 24)}

        test_date = datetime.date(2018, 12, 24)

        self.assertEqual(18, add_countdown_ago(test_date, "st_nicolas", test_event_dates))
        self.assertEqual(0, add_countdown_ago(test_date, "noel", test_event_dates))
        self.assertEqual(347, add_countdown_in(test_date, "st_nicolas", test_event_dates))

    def test_compute_last_weekday_of_a_month(self):
        last_monday = compute_last_weekday_of_a_month(2019, 9, 1)
        self.assertEqual(last_monday, datetime.date(2019, 9, 30))

    def test_compute_first_weekday_of_a_month(self):
        first_monday = compute_first_weekday_of_a_month(2019, 9, 1)
        self.assertEqual(first_monday, datetime.date(2019, 9, 2))


if __name__ == '__main__':
    unittest.main()
