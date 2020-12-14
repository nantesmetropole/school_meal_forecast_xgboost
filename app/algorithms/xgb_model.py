#!/usr/bin/python3
# -----------------------------------------------------------
# Train a XGBoost model
# -----------------------------------------------------------
import json
import math
import multiprocessing as mp
import os

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

from app.exceptions import EmptyTrainingSet
from app.log import logger
from app.plot import plot_curve


def multi_custom_metrics(y_pred, dtrain):
    """
    allow to optimize xgboost using multiple metrics for early stopping
    """
    y_true = dtrain.get_label()
    mae = mean_absolute_error(y_true, y_pred)
    rmse = math.sqrt(mean_squared_error(y_true, y_pred))

    return [("mae", mae), ("mse", rmse)]


def ratio_split(x_data, y_data, test_percent):
    """
    split x_data and y_data in x_train, x_test, y_train, y_test based on test_percent such that
    test_ dataframes contains test_percent of the initial dataframes
    """
    if test_percent != 0.0:
        x_train, x_test, y_train, y_test = train_test_split(x_data, y_data, test_size=test_percent, random_state=42)
    else:
        x_train = x_data
        y_train = y_data
        x_test = pd.DataFrame()
        y_test = pd.DataFrame()

    return x_train, y_train, x_test, y_test


# pylint: disable=too-many-locals
def xgb_train_and_predict(column_to_predict, train_data, evaluation_data, data_path):
    """
    train a xgboost model on column_to_predict from train_data
    and generates predictions for evaluation_data which are stored in a column named `output`
    data_path specify path to data in order to compute external features
    """
    logger.info("----------- check training data -------------")
    for resolution, dtf in train_data.groupby(['cantine_nom', 'cantine_type']):
        logger.info("canteen %s has %s days of history to train on starting on %s and ending on %s",
                    resolution,
                    len(dtf),
                    dtf["date_str"].min(),
                    dtf['date_str'].max(),
                    )

    features = [
        "site_id",
        # "date_str",
        # "cantine_nom",
        # "site_type_cat",
        "secteur_cat",
        # "year",
        # "month",
        # "day",
        "week",
        "wednesday",  # this feature is only used if the dedicated parameter include_wednesday is set to True
        # "weekday",  # weekday is not used here because redundant with meal composition
        "holidays_in",
        "non_working_in",
        "effectif",
        "frequentation_prevue",
        "Events.RAMADAN_ago",  # "Events.AID_ago"
    ]

    with open(os.path.join(data_path, "calculators/menus.json")) as f_in:
        dict_special_dishes = json.load(f_in)
    features = features + list(dict_special_dishes.keys())

    # prepare training dataset
    train_data_reduced = train_data[features + [column_to_predict]]
    before_dropping_na = len(train_data_reduced)
    train_data_reduced.dropna(inplace=True)
    after_dropping_na = len(train_data_reduced)
    percent_dropped = round(100 * (before_dropping_na - after_dropping_na) / before_dropping_na)
    logger.info("Dropping %s percent of training data due to NANs", percent_dropped)

    train_data_x = train_data_reduced[features]
    train_data_y = train_data_reduced[column_to_predict]
    if len(train_data_x) == 0:
        raise EmptyTrainingSet("")
    # prepare test_dataset to control overfitting
    train_data_x, train_data_y, test_data_x, test_data_y = ratio_split(train_data_x, train_data_y, 0.1)
    eval_set = [(train_data_x, train_data_y), (test_data_x, test_data_y)]

    # prepare prediction dataset
    evaluation_data_x = evaluation_data[features]

    params = {
        'base_score': train_data_y.mean(),
        "objective": 'reg:squarederror',
        "n_estimators": 5000,
        "learning_rate": 0.09,
        "max_depth": 5,
        "booster": 'gbtree',
        "colsample_bylevel": 1,
        "colsample_bynode": 1,
        "colsample_bytree": 1,
        "gamma": 0,
        "importance_type": 'gain',
        "max_delta_step": 0,
        "min_child_weight": 1,
        "missing": None,
        "n_jobs": mp.cpu_count(),
        "nthread": None,
        "random_state": 0,
        "reg_alpha": 0,
        "reg_lambda": 1,
        "scale_pos_weight": 1,
        "seed": None,
        "subsample": 1,
        "verbosity": 0,
    }
    # define model
    model = XGBRegressor(**params)
    # train model
    model.fit(
        train_data_x,
        train_data_y,
        early_stopping_rounds=100,
        eval_set=eval_set,
        eval_metric=multi_custom_metrics,
        verbose=False)
    # predict values
    evaluation_data['output'] = np.ceil(model.predict(evaluation_data_x))

    logger.info("----------- check predictions -------------")
    for resolution, dtf in evaluation_data.groupby(['cantine_nom', 'cantine_type']):
        logger.info("canteen %s has predictions for %s days starting on %s and ending on %s",
                    resolution,
                    len(dtf),
                    dtf["date_str"].min(),
                    dtf['date_str'].max(),
                    )

    logger.info("----------- evaluate model -------------")

    feature_importance_list = evaluate_feature_importance(evaluation_data_x, model)

    plot_curve(model.evals_result(), "nantes_metropole_xgb")

    return evaluation_data, feature_importance_list


def evaluate_feature_importance(evaluation_data_x, model):
    """
    given a trained model x and a dataframe evaluation_data_x,
    returns a list of features name with their importance for the model
    """
    feature_importance = zip(evaluation_data_x.columns.values, model.feature_importances_)
    feature_importance_list = sorted(feature_importance, key=lambda t: t[1], reverse=True)
    logger.info("FI:")
    logger.info(feature_importance_list)
    return feature_importance_list
