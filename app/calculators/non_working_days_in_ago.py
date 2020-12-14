#!/usr/bin/python3
# -----------------------------------------------------------
# Calculator to add countdown to non working days features to the dataset
# -----------------------------------------------------------
import pandas as pd
import numpy as np


# pylint: disable=too-many-locals
def add_feature_non_working_days_in_ago(dataset, date_col, date_format, data_path):
    """"
    given a dataframe with a date_col of format date_format and a date index
    add a new columns:
    - nom_jour_ferie: name of the non working day
    - non_working_in: number of days until next non working day included in dataset
    - non_working_ago:  number of days since previous non working day included in dataset
    using an external csv located in data_path using the same date_format
    """

    # generate all dates within start and end
    start = dataset[date_col].min()
    end = dataset[date_col].max()
    all_dates = pd.date_range(start, end, freq="D").to_frame(index=False, name="_date")

    # read external non_working csv
    def _parser(date):
        return pd.datetime.strptime(date, date_format)

    fr_non_working = pd.read_csv(f'{data_path}/calculators/jours_feries.csv', parse_dates=['date'], date_parser=_parser)
    fr_non_working = fr_non_working[["date", "nom_jour_ferie"]]
    # TODO FILTER THIS DATAFRAME TO IMPROVE PERFORMACE

    # simulate an interval based left join using pandas
    # 1/ perform a cross join using const __magic_key
    low_bound = "date"
    key = "_date"
    dtf = all_dates
    additional_data = fr_non_working

    dtf['__magic_key'] = 1
    additional_data['__magic_key'] = 1
    # DO A SIMPLE JOIN TO IMPROVE PERFORMACE
    crossjoindf = pd.merge(dtf, additional_data, on=['__magic_key'])
    dtf.drop(columns=['__magic_key'], inplace=True)
    crossjoindf.drop(columns=['__magic_key'], inplace=True)
    # 2/ filter this cross join using lower_bound <= key <= upper_bound
    conditionnal_join_df = crossjoindf[(crossjoindf[key] == crossjoindf[low_bound])]
    # 3/ merge this conditionnal join on the original DF uing all cols as keys to simulate left join
    dtf_columns = dtf.columns.values.tolist()
    conditionnal_join_df.set_index(dtf_columns, inplace=True)
    dtf = dtf.merge(conditionnal_join_df, left_on=dtf_columns, right_index=True, how='left')

    # find rows index corresponding to non_working
    non_working_index = np.where(~dtf['nom_jour_ferie'].isnull())[0]

    # compute arrays of first day of holiday and last day of non_working
    non_working_min_index = []
    non_working_max_index = []
    i = 0
    while i < len(non_working_index):
        j = 0
        while i + j < len(non_working_index) and (non_working_index[i] + j) == non_working_index[i + j]:
            j += 1
        non_working_min_index.append(non_working_index[i])
        non_working_max_index.append(non_working_index[i + j - 1])
        i += j

    indexes = range(0, len(dtf))

    # compute for each index row the distance with the nearest upcoming non_working
    index_non_working_in = [min([i - x for i in non_working_min_index if i > x], default=0) for x in indexes]
    dtf['non_working_in'] = index_non_working_in

    # compute for each index row the distance with the latest past non_working
    index_non_working_ago = [min([x - i for i in non_working_max_index if i < x], default=0) for x in indexes]
    dtf['non_working_ago'] = index_non_working_ago

    # set non_working_in and non_working_ago to 0 during effective non_working
    dtf.loc[~dtf['nom_jour_ferie'].isnull(), 'non_working_in'] = 0
    dtf.loc[~dtf['nom_jour_ferie'].isnull(), 'non_working_ago'] = 0

    dtf.set_index(key, inplace=True)
    dtf["nom_jour_ferie"] = dtf["nom_jour_ferie"].fillna('jour_ouvre')

    cols_to_use = ['non_working_in', 'non_working_ago', 'nom_jour_ferie']
    dataset = dataset.merge(dtf[cols_to_use], left_index=True, right_index=True, how='left')
    return dataset
