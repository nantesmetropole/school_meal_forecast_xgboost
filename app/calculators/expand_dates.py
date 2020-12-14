#!/usr/bin/python3
# -----------------------------------------------------------
# Calculator to generate a dataset containing a range of dates
# -----------------------------------------------------------
import datetime
import dateutil

import pandas as pd


# pylint: disable=no-member
def generate_dates_df(start, end, date_format, date_col):
    """
    Generate a dataframe containing a date_index and a string column date_col formatted using date_format
    between start and end + 10 weeks
    This delay is used to be sure to incorporate next holidays
    """
    end_delayed = datetime.datetime.strptime(end, date_format) + dateutil.relativedelta.relativedelta(weeks=10)

    all_dates = pd.date_range(start, end_delayed.strftime(date_format), freq="D")
    all_dates_df = pd.DataFrame({"date_index": all_dates, date_col: all_dates.strftime(date_format)})
    all_dates_df = all_dates_df.set_index("date_index")
    return all_dates_df
