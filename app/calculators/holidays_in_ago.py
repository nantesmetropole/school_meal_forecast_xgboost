#!/usr/bin/python3
# -----------------------------------------------------------
# Calculator to add countdown to holidays features to the dataset
# -----------------------------------------------------------
import pandas as pd
import numpy as np


# pylint: disable=too-many-locals
def add_feature_holidays_in_ago(dataset, date_col, date_format, data_path):
    """"
    given a dataframe with a date_col of format date_format and a date index
    add a new columns:
    - vacances_nom: name of the holidays
    - holidays_in: number of days until next holidays included in dataset
    - holidays_ago:  number of days since previous holidays included in dataset
    using an external csv located in data_path using the same date_format
    """

    # generate all dates within start and end
    start = dataset[date_col].min()
    end = dataset[date_col].max()
    all_dates = pd.date_range(start, end, freq="D").to_frame(index=False, name="date")

    # read external holidays csv
    def _parser(date):
        return pd.datetime.strptime(date, date_format)

    fr_holidays = pd.read_csv(f'{data_path}/calculators/vacances.csv',
                              parse_dates=['date_debut', 'date_fin'],
                              date_parser=_parser)
    fr_holidays = fr_holidays[["vacances_nom", "date_debut", "date_fin", "zone", "vacances"]]
    fr_holidays = fr_holidays.drop_duplicates()

    # simulate an interval based left join using pandas
    # 1/ perform a cross join using const __magic_key
    up_bound = "date_fin"
    low_bound = "date_debut"
    key = "date"
    dtf = all_dates
    additional_data = fr_holidays

    dtf['__magic_key'] = 1
    additional_data['__magic_key'] = 1
    crossjoindf = pd.merge(dtf, additional_data, on=['__magic_key'])
    dtf.drop(columns=['__magic_key'], inplace=True)
    crossjoindf.drop(columns=['__magic_key'], inplace=True)
    # 2/ filter this cross join using lower_bound <= key <= upper_bound
    conditionnal_join_df = crossjoindf[
        (crossjoindf[key] >= crossjoindf[low_bound]) & (crossjoindf[key] <= crossjoindf[up_bound])]
    # 3/ merge this conditionnal join on the original DF uing all cols as keys to simulate left join
    dtf_columns = dtf.columns.values.tolist()
    conditionnal_join_df.set_index(dtf_columns, inplace=True)
    dtf = dtf.merge(conditionnal_join_df, left_on=dtf_columns, right_index=True, how='left')
    # find rows index corresponding to holidays
    holidays_index = np.where(~dtf['vacances_nom'].isnull())[0]

    # compute arrays of first day of holiday and last day of holidays
    holidays_min_index = []
    holidays_max_index = []
    i = 0
    while i < len(holidays_index):
        j = 0
        while i + j < len(holidays_index) and (holidays_index[i] + j) == holidays_index[i + j]:
            j += 1
        holidays_min_index.append(holidays_index[i])
        holidays_max_index.append(holidays_index[i + j - 1])
        i += j

    indexes = range(0, len(dtf))
    # compute for each index row the distance with the nearest upcoming holidays
    index_holidays_in = [min([i - x for i in holidays_min_index if i > x], default=0) for x in indexes]
    dtf['holidays_in'] = index_holidays_in
    # compute for each index row the distance with the latest past holidays
    index_holidays_ago = [min([x - i for i in holidays_max_index if i < x], default=0) for x in indexes]
    dtf['holidays_ago'] = index_holidays_ago

    # set holidays_in and holidays_ago to 0 during effective holidays
    dtf.loc[~dtf['vacances_nom'].isnull(), 'holidays_in'] = 0
    dtf.loc[~dtf['vacances_nom'].isnull(), 'holidays_ago'] = 0

    dtf.set_index(key, inplace=True)
    dtf["vacances_nom"] = dtf["vacances_nom"].fillna('ecole')

    cols_to_use = ['holidays_in', 'holidays_ago', 'vacances_nom']
    dataset = dataset.merge(dtf[cols_to_use], left_index=True, right_index=True, how='left')
    return dataset
