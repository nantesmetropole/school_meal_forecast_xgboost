#!/usr/bin/python3
# -----------------------------------------------------------
# Calculator to add school year features to a dataset
# -----------------------------------------------------------
import pandas as pd


# pylint: disable=too-many-locals
def add_feature_school_year(dataset, date_col, date_format, data_path):
    """"
    given a dataframe with a date_col of format date_format and a date index
    add a new column annee_scolaire using an external csv located in data_path using the same date_format
    """

    # generate all dates within start and end
    start = dataset[date_col].min()
    end = dataset[date_col].max()
    all_dates = pd.date_range(start, end, freq="D").to_frame(index=False, name="date")

    # read external holidays csv
    def _parser(date):
        return pd.datetime.strptime(date, date_format)

    fr_holidays = pd.read_csv(f'{data_path}/calculators/annees_scolaires.csv',
                              parse_dates=['date_debut', 'date_fin'],
                              date_parser=_parser)
    fr_holidays = fr_holidays[["annee_scolaire", "date_debut", "date_fin"]]
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
    dtf.set_index(key, inplace=True)
    cols_to_use = ['annee_scolaire']
    dataset = dataset.merge(dtf[cols_to_use], left_index=True, right_index=True, how='left')
    dataset['annee_scolaire'] = dataset['annee_scolaire'].fillna("ete")
    return dataset
