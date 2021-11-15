#!/usr/bin/python3
# -----------------------------------------------------------
# Train XGBoost model to estimate a confidence interval
# -----------------------------------------------------------
import json
import multiprocessing as mp
import os

import numpy as np
from xgboost import XGBRegressor

from app.algorithms.xgb_model import evaluate_feature_importance, multi_custom_metrics, ratio_split
from app.exceptions import EmptyTrainingSet
from app.log import logger
from app.plot import plot_curve


# pylint: disable=too-many-locals
def xgb_interval_train_and_predict(column_to_predict, train_data, evaluation_data, confidence_interval, data_path):
    """
    train a xgboost model on column_to_predict from train_data
    and generates predictions for evaluation_data which are stored in a column named `output`
    data_path specify path to data in order to compute external features
    Note: here, the model does not directly learn from column to_predict but from the bound of a confidence_interval
    see here for more details: https://towardsdatascience.com/confidence-intervals-for-xgboost-cac2955a8fde

    """
    features = [
        "site_id",
        "secteur_cat",
        "week",
        "wednesday",  # this feature is only used if the dedicated parameter include_wednesday is set to True
        "non_working_in",
        "holidays_in",
        "effectif",
        "frequentation_prevue",
        "Events.RAMADAN_ago",  # "Events.AID_ago"
    ]

    logger.info("----------- check training data -------------")
    for resolution, dtf in train_data.groupby(['cantine_nom', 'cantine_type']):
        logger.info("canteen %s has %s days of history to train on starting on %s and ending on %s",
                    resolution,
                    len(dtf),
                    dtf["date_str"].min(),
                    dtf['date_str'].max(),
                    )

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

    train_data_y = train_data_reduced[column_to_predict]
    train_data_x = train_data_reduced[features]
    if len(train_data_x) == 0:
        raise EmptyTrainingSet("")
    # prepare test_dataset to control overfitting
    train_data_x, train_data_y, test_data_x, test_data_y = ratio_split(train_data_x, train_data_y, 0.1)
    eval_set = [(train_data_x, train_data_y), (test_data_x, test_data_y)]

    # prepare prediction dataset
    evaluation_data_x = evaluation_data[features]

    params = {
        "n_jobs": mp.cpu_count(),
        'base_score': train_data_y.mean(),
        "objective": 'reg:squarederror',
        "n_estimators": 5000,
        "learning_rate": 0.09,
        "max_depth": 5,
        "booster": 'gbtree',
        "importance_type": 'gain',
        "max_delta_step": 0,
        "min_child_weight": 1,
        "random_state": 0,
        "reg_alpha": 0,
        "reg_lambda": 1,
        "scale_pos_weight": 1,
        "subsample": 1,
        "verbosity": 0,
    }

    confidence_step = (1 - confidence_interval) / 2
    # under predict
    params.update({"objective": log_cosh_quantile(1 - confidence_step)})

    confidence_upper_bound_model = XGBRegressor(**params)
    confidence_upper_bound_model.fit(
        train_data_x,
        train_data_y,
        early_stopping_rounds=100,
        eval_set=eval_set,
        eval_metric=multi_custom_metrics,
        verbose=False)
    y_upper_smooth = np.ceil(confidence_upper_bound_model.predict(evaluation_data_x))

    # over predict
    params.update({"objective": log_cosh_quantile(confidence_step)})
    confidence_lower_bound_model = XGBRegressor(**params)
    confidence_lower_bound_model.fit(train_data_x, train_data_y, verbose=False)
    y_lower_smooth = np.ceil(confidence_lower_bound_model.predict(evaluation_data_x))

    evaluation_data['pred_lower_bound'] = y_lower_smooth
    evaluation_data['pred_upper_bound'] = y_upper_smooth
    evaluation_data['output'] = np.maximum.reduce([y_upper_smooth, y_lower_smooth])

    logger.info("----------- check predictions -------------")
    for resolution, dtf in evaluation_data.groupby(['cantine_nom', 'cantine_type']):
        logger.info("canteen %s has predictions for %s days starting on %s and ending on %s",
                    resolution,
                    len(dtf),
                    dtf["date_str"].min(),
                    dtf['date_str'].max(),
                    )

    logger.info("----------- evaluate model -------------")

    feature_importance_list = evaluate_feature_importance(evaluation_data_x, confidence_upper_bound_model)
    
    ## Generates errors on Windows with Reticulate
    plot_curve(confidence_upper_bound_model.evals_result(), "nantes_metropole_xgb")

    return evaluation_data, feature_importance_list


def log_cosh_quantile(alpha):
    """
    log cosh quantile is a regularized quantile loss function
    """
    def _log_cosh_quantile(y_true, y_pred):
        err = np.float64(y_pred - y_true)
        err = np.where(err < 0, np.float64(alpha * err), np.float64((1 - alpha) * err))

        # approximate hessian when abs(error) becomes to big to avoid overflow
        def _f_hess(error):
            if abs(error) > 350:
                return 0
            return 1 / np.cosh(error)**2
        v_hess = np.vectorize(_f_hess)
        hess = v_hess(err)

        grad = np.float64(np.tanh(err))
        return grad, hess
    return _log_cosh_quantile
