#!/usr/bin/python3
# -----------------------------------------------------------
# Calculator to add strikes features to a dataset
# -----------------------------------------------------------
import pandas as pd


# pylint: disable=too-many-locals
def add_feature_strikes(dataset, date_format, data_path):
    """"
    given a dataframe with a date index
    add a new column greve using an external csv located in data_path using the same date_format
    """
    # read external strikes csv
    def _parser(date):
        return pd.datetime.strptime(date, date_format)

    fr_strikes = pd.read_csv(f'{data_path}/calculators/greves.csv', parse_dates=['date'], date_parser=_parser)
    fr_strikes = fr_strikes[["date", "greve"]]
    fr_strikes = fr_strikes.drop_duplicates()
    fr_strikes = fr_strikes.set_index("date")

    # simulate an interval based left join using pandas
    dataset = dataset.merge(fr_strikes, left_index=True, right_index=True, how='left')
    dataset['greve'] = dataset['greve'].fillna(0)

    return dataset
