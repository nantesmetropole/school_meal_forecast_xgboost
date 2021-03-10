#!/usr/bin/python3
# -----------------------------------------------------------
# Preprocess data to generate training and test datasets
# -----------------------------------------------------------
import datetime
import os

import dateutil.relativedelta
import pandas as pd
import numpy as np

import app.calculators as calculators
from app.exceptions import OverlappingColumns, InconsistentDates
from app.log import logger


def compute_min_max_date(begin_training, begin_prediction, end_prediction, date_format, weeks_latency):
    """
    check consistency of dates providen by the user and compute end_training date as follow:
        - training will be performed between `begin_training` and `end_training`
        - prediction will be performed between `begin_prediction` and `end_prediction`
        - last training day i.e. `end_training` and first prediction day i.e. `begin_prediction`
          are spaced of `weeks_latency` weeks
    """
    if datetime.datetime.strptime(begin_prediction, date_format) > datetime.datetime.strptime(end_prediction, date_format):
        raise InconsistentDates(f"begin_prediction ({begin_prediction}) must be prior to end_prediction ({end_prediction})")

    if datetime.datetime.strptime(begin_training, date_format) >= datetime.datetime.strptime(begin_prediction, date_format):
        raise InconsistentDates(f"begin_training ({begin_training}) must be prior to begin_prediction ({begin_prediction})")

    # begin_training is the starting of the training date
    # TODO: compute end_training based on available data
    begin_prediction_datetime = datetime.datetime.strptime(begin_prediction, date_format)
    end_training = begin_prediction_datetime - dateutil.relativedelta.relativedelta(weeks=weeks_latency)
    # TODO: compute end_training based on available data
    if end_training <= datetime.datetime.strptime(begin_training, date_format):
        error = f"end_training ({end_training.strftime(date_format)}) must be after begin_training ({begin_training}) \
                  and respect the latency of {weeks_latency} weeks with begin_prediction ({begin_prediction})"
        raise InconsistentDates(error)

    return (begin_training, end_training.strftime(date_format))


def compute_dates_dataframe(start, end, date_format, data_path, include_wednesday):
    """
    generates a dataframe of dates between start and end at day resolution
    with:
        - a `date_index`
        - a column `date_str` formatted using date_format
        - various dates related features
    """

    date_col = "date_str"

    # generate dates rows
    all_dates = calculators.generate_dates_df(start, end, date_format, date_col)

    # add dates related features
    all_dates = calculators.add_feature_school_year(all_dates, date_col, date_format, data_path)
    all_dates = calculators.add_feature_strikes(all_dates, date_format, data_path)
    time_data = ["year", "month", "day", "week", "weekday"]
    all_dates = calculators.add_feature_date_attributes(all_dates, date_col, time_data, date_format)
    all_dates = calculators.add_feature_holidays_in_ago(all_dates, date_col, date_format, data_path)
    all_dates = calculators.add_feature_non_working_days_in_ago(all_dates, date_col, date_format, data_path)
    all_dates = calculators.add_feature_events_countdown(all_dates, date_col, date_format)
    all_dates = calculators.add_feature_special_meals(all_dates, date_col, date_format, data_path)

    mask_working = (all_dates["weekday"] != 5) & \
        (all_dates["weekday"] != 6) & \
        (all_dates["vacances_nom"] == "ecole") &\
        (all_dates["nom_jour_ferie"] == "jour_ouvre")

    if not include_wednesday:
        mask_working = mask_working & (all_dates["weekday"] != 2)

    all_dates["working"] = 0
    all_dates.loc[mask_working, "working"] = 1

    mask_wednesday = (all_dates["weekday"] == 2)

    all_dates["wednesday"] = 0
    all_dates.loc[mask_wednesday, "wednesday"] = 1

    return all_dates, date_col


def cross_product(dataframe_1, dataframe_2):
    """
    returns the cross product of dataframe_1 and dataframe_2 as a new dataset
    """
    common_columns = set(dataframe_1.columns.values).intersection(set(dataframe_2.columns.values))
    if common_columns:
        raise OverlappingColumns(common_columns)
    dataframe_1['__magic_key'] = 1
    dataframe_2['__magic_key'] = 1
    cross_df = pd.merge(dataframe_1, dataframe_2, on=['__magic_key'])
    cross_df.drop(columns=['__magic_key'], inplace=True)
    return cross_df


def read_raw_input_files(data_path):
    """
    reads input files stored in data_path and specified in this function
    returns a dict of DataFrames and a dict of mapping DataFrames
    """
    datasets = {}
    mappings = {}
    # define data_input
    data_input = {
        "frequentation": {
            "date": str,
            "site_nom": str,
            "site_type": str,
            "prevision": lambda x: np.nan if x in ['NA', ''] else float(x),
            "reel": lambda x: np.nan if x in ['NA', ''] else float(x),
        },
        "cantines": {
            "cantine_nom": str,
            "cantine_type": str,
            "secteur": str,
        },
        "effectifs": {
            "ecole": str,
            "annee_scolaire": str,
            "effectif": float,
        }
    }

    # define data_input
    mapping_files = {
        "mapping_ecoles_cantines": {
            "ecole": str,
            "cantine_nom": str,
            "cantine_type": str,
        },
        "mapping_frequentation_cantines": {
            "site_nom": str,
            "site_type": str,
            "cantine_nom": str,
            "cantine_type": str,
        },
    }

    # load datasets and check data input
    for file_name, cols_type in data_input.items():
        datasets[file_name] = pd.read_csv(os.path.join(data_path, "raw", file_name + ".csv"),
                                          na_values=['NA', ''],
                                          converters=cols_type)

    # load mappings and check data input
    for file_name, cols_type in mapping_files.items():
        mappings[file_name] = pd.read_csv(os.path.join(data_path, "mappings", file_name + ".csv"),
                                          converters=cols_type)
    return datasets, mappings


def compute_datafiles_related_dataframes(data_path, school_cafeterias=None):
    """
    returns a tuple of DataFrames used for this project based on files stored in `data_path`
    DataFrames can be filtered to keep only school_cafeterias belonging to the parameter `school_cafeterias`
    """
    datasets, mappings = read_raw_input_files(data_path)

    # Read Canteens
    all_school_cafeterias = datasets["cantines"]
    if school_cafeterias:
        logger.info('working only with school_cafeteria(s) %s', school_cafeterias)
        all_school_cafeterias = all_school_cafeterias[all_school_cafeterias["cantine_nom"].isin(school_cafeterias)]

    # Read Real values
    real_values = datasets["frequentation"]
    # fill na instead ?
    # real_values = real_values[(real_values['prevision'].notna()) & (real_values['reel'].notna())]

    real_values = real_values.merge(
        mappings['mapping_frequentation_cantines'],
        left_on=["site_nom", "site_type"],
        right_on=["site_nom", "site_type"],
        how='left')

    real_values = real_values[["cantine_nom", "cantine_type", "date", "prevision", "reel"]]
    # fix problem when two lines are used in real_values file with typo in the site_nom
    real_values = real_values.groupby(["cantine_nom", "cantine_type", "date"])["prevision", "reel"].sum().reset_index()

    # Read effectifs data
    effectifs = datasets["effectifs"].merge(mappings['mapping_ecoles_cantines'],
                                            left_on="ecole",
                                            right_on="ecole",
                                            how='left')
    effectifs = effectifs.groupby(['annee_scolaire', 'cantine_nom', 'cantine_type'])["effectif"].sum()

    real_values.rename(columns={"date": "date_str"}, inplace=True)
    return all_school_cafeterias, real_values, effectifs


def add_statistical_features(all_data):
    """
    compute statistical features using ratio, means etc
    """
    # TODO improve filtering here and remove NANs
    remove_real_lines = all_data[(all_data["annee_scolaire"] != "2019-2020") & (all_data["annee_scolaire"] != "2018-2019")]
    # calculus
    remove_real_lines["frequentation_prevue"] = remove_real_lines["prevision"] / remove_real_lines["effectif"]
    remove_real_lines["frequentation_reel"] = remove_real_lines["reel"] / remove_real_lines["effectif"]
    # resolution and average manipulation
    updated_resol = remove_real_lines.groupby(["cantine_nom", "cantine_type", "week", "annee_scolaire"])
    updated_resol = updated_resol['frequentation_prevue', 'frequentation_reel', 'prevision', 'reel'].mean().reset_index()
    stats = updated_resol.groupby(["cantine_nom", "cantine_type", "week"])
    stats = stats['frequentation_prevue', 'frequentation_reel'].mean()

    all_data = all_data.merge(
        stats,
        left_on=["cantine_nom", "cantine_type", "week"],
        right_index=True,
        how='left')

    return all_data


def tag_outliers(all_data, column, n_sigma):
    """
    Given a dataset all_date, a column and n_sigma
    Create new columns upper_outlier and lower_outlier to identify all outliers of the column
    using respectively the following classic filtering:
    `mean + n_simga * std` and `mean - n_simga * std`
    """
    outliers = all_data[(all_data[column] != 0)]
    outliers = outliers.groupby(["cantine_nom", "cantine_type", "annee_scolaire"])
    outliers = outliers[column].agg(["mean", "std"])

    outliers['lower_bound'] = outliers['mean'] - (n_sigma * outliers['std'])
    outliers['upper_bound'] = outliers['mean'] + (n_sigma * outliers['std'])

    # TODO merge and then filter
    all_data = all_data.merge(
        outliers,
        left_on=["cantine_nom", "cantine_type", "annee_scolaire"],
        right_index=True,
        how='left')
    all_data["upper_outlier"] = all_data[column] > all_data['upper_bound']
    all_data["lower_outlier"] = all_data[column] < all_data['lower_bound']

    return all_data


def smarter_process_data(data_path, start, end, school_cafeterias, include_wednesday, date_format):
    """
    Computes dataset based on datafiles stored in `data_path` such that:
        - one line by date and school_cafeteria
        - dates belong to [start, end]
        - school_cafeterias belong to `school_cafeterias`
    """

    # generate dataframes based on input datafiles
    all_school_cafeterias, real_values, effectifs = compute_datafiles_related_dataframes(data_path, school_cafeterias)

    # generate dates rows
    all_dates, date_col = compute_dates_dataframe(start, end, date_format, data_path, include_wednesday)

    # cross product school_cafeterias x dates
    all_dates_x_all_school_cafeterias = cross_product(all_dates, all_school_cafeterias)

    # join real values
    all_data = all_dates_x_all_school_cafeterias.merge(
        real_values,
        left_on=[date_col, "cantine_nom", "cantine_type"],
        right_on=[date_col, "cantine_nom", "cantine_type"],
        how='left')

    # join effectif values
    all_data = all_data.merge(
        effectifs,
        left_on=["annee_scolaire", "cantine_nom", "cantine_type"],
        right_index=True,
        how='left')

    # compute statistical features
    all_data = add_statistical_features(all_data)
    all_data = tag_outliers(all_data, 'reel', 3)

    for resolution, dtf in all_data.groupby(['cantine_nom', 'cantine_type']):
        logger.info("dataset for school_cafeteria %s generated contains %s days", str(resolution), str(len(dtf)))

    # fillnans with 0
    all_data.loc[(all_data["working"] == 0) & np.isnan(all_data["reel"]), 'reel'] = 0
    all_data.loc[(all_data["working"] == 0) & np.isnan(all_data["prevision"]), 'prevision'] = 0

    all_data.loc[(all_data["wednesday"] == 1) & np.isnan(all_data["reel"]), 'reel'] = 0
    all_data.loc[(all_data["wednesday"] == 1) & np.isnan(all_data["prevision"]), 'prevision'] = 0

    all_data.to_csv(f'output/staging/prepared_data_{start}_{end}.csv', index=False)
