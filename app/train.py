#!/usr/bin/python3
# -----------------------------------------------------------
# Train model, generates prediction and evaluate when possible
# -----------------------------------------------------------
import math
import os

import pandas as pd
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

from app.log import logger
import app.algorithms
from app.exceptions import EmptyTrainingSet, MissingDataForPrediction
from app.plot import plot_error


def split_train_predict(min_date, max_date, begin_date, end_date):
    """
    split the dataset generated during preprocessing stage in a training set and a prediction set based on dates:
    - `min_date` to `max_date` defines the bounds of the training set
    - `begin_date` to `end_date` defines the bounds of the prediction set
    """
    logger.info("----------- read full dataset -------------")
    dataset = pd.read_csv(f'output/staging/prepared_data_{min_date}_{end_date}.csv')
    # numerize sring columns
    dataset['site_id_built_in'] = pd.Categorical((pd.factorize(dataset.cantine_nom)[0] + 1))
    dataset['site_id'] = dataset['site_id_built_in'].cat.codes
    dataset['site_type_built_in'] = pd.Categorical((pd.factorize(dataset.cantine_type)[0] + 1))
    dataset['site_type_cat'] = dataset['site_type_built_in'].cat.codes
    dataset['secteur_built_in'] = pd.Categorical((pd.factorize(dataset.secteur)[0] + 1))
    dataset['secteur_cat'] = dataset['secteur_built_in'].cat.codes

    # split predict/train based on dates
    logger.info("----------- isolate train data and predict data among all dataset -------------")
    prediction_input_data = dataset.loc[(dataset['date_str'] >= begin_date) & (dataset['date_str'] <= end_date)]
    train_data = dataset.loc[(dataset['date_str'] >= min_date) & (dataset['date_str'] <= max_date)]
    return (train_data, prediction_input_data)


def filter_data(dataset, remove_no_school, remove_outliers, begin_date):
    """
    filter lines out of dataset:
    - remove_no_school: bool, if True day considered as non working are removed
    - remove_outliers: bool, if True day considered as outliers are removed from the training set only
    Note that outliers are here:
    - statistical outliers
    - strikes
    - days with no expected guests
    - days with no effective guests
    """
    # remove weekends and holidays
    if remove_no_school:
        mask = (dataset['working'] != 0)
        dataset = dataset.loc[mask]

    # remove outliers
    if remove_outliers:
        mask =\
            (dataset['prevision'] != 0) &\
            (dataset['reel'] != 0) &\
            (dataset['date_str'] <= begin_date) &\
            (dataset['greve'] != 1) &\
            (dataset['upper_outlier'] != 1) &\
            (dataset['lower_outlier'] != 1)  # | (dataset['date_str'] >= begin_date)
        dataset = dataset.loc[mask]

    return dataset


def export_predictions(prediction_input_data, output_dir, file_name):
    """
    export `prediction_input_data` dataframe to `output_dir/file_name`
    """
    prediction_input_data.to_csv(os.path.join(output_dir, file_name))
    logger.info("data exported to %s", os.path.join(output_dir, file_name))


def evaluate_predictions(reference_data, ref_to_beat, prediction):
    """
    evaluates `predictions` and `ref_to_beat` regarding to true_values `reference_data`
    """
    logger.info("number of predictions: theirs: %s / ours: %s", len(reference_data), len(prediction))
    logger.info("R2: %0.2f", r2_score(reference_data, ref_to_beat))
    logger.info("MAE: %0.2f", mean_absolute_error(reference_data, ref_to_beat))
    logger.info("MSE: %0.2f", mean_squared_error(reference_data, ref_to_beat))
    logger.info("weighted prec: %0.2f", weighted_precision_calculus(reference_data, ref_to_beat))
    logger.info("prec: %0.2f", precision_calculus(reference_data, ref_to_beat))

    logger.info("OURS:")
    logger.info("R2: %0.2f", r2_score(reference_data, prediction))
    logger.info("MAE: %0.2f", mean_absolute_error(reference_data, prediction))
    logger.info("MSE: %0.2f", mean_squared_error(reference_data, prediction))
    logger.info("weighted prec: %0.2f", weighted_precision_calculus(reference_data, prediction))
    logger.info("prec: %0.2f", precision_calculus(reference_data, prediction))


def evaluate_predictions_by_resolution(column_to_predict, complete_pred_df, predicted_col, resolution):
    """
    evaluates `predicted_col` within dataframe `complete_pred_df` regarding to true_values `column_to_predict`
    after aggregating the values predicting using the list of columns `resolution` to group lines
    """
    logger.info("OURS BY RESOLUTION %s:", resolution)
    for res, data in complete_pred_df.groupby(resolution):
        logger.info("***************************")
        logger.info("res: %s", res)
        logger.info("expected: %0.2f, predicted: %0.2f", data[column_to_predict].sum(), data[predicted_col].sum())
        logger.info("R2: %0.2f", r2_score(data[column_to_predict], data[predicted_col]))
        logger.info("MAE: %0.2f", mean_absolute_error(data[column_to_predict], data[predicted_col]))
        logger.info("MSE: %0.2f", mean_squared_error(data[column_to_predict], data[predicted_col]))
        logger.info("weighted prec: %0.2f", weighted_precision_calculus(data[column_to_predict], data[predicted_col]))
        logger.info("prec: %0.2f", precision_calculus(data[column_to_predict], data[predicted_col]))


def weighted_precision_calculus(ytrue, y_pred):
    """
    computes the weighted precision
    """
    precision = (1 - abs(y_pred - ytrue) / ytrue).apply(lambda x: max(x, 0))
    score = ((precision * ytrue).sum()) / (ytrue.sum())
    return score


def precision_calculus(ytrue, y_pred):
    """
    computes the precision
    """
    precision = (1 - abs(y_pred - ytrue) / ytrue).apply(lambda x: max(x, 0))
    score = precision.mean()
    return score


# pylint: disable=too-many-statements
def train_and_predict(column_to_predict, training_type, min_date, max_date, begin_date, end_date,
                      remove_no_school, remove_outliers, data_path, confidence):
    """
    performs training and prediction

    column_to_predict: str, define the column to predict
    training_type: str, provide the algorithm to use for training and predicting
    min_date: str, lower bound of the training set
    max_date: str, upper bound of the training set
    begin_date: str, lower bound of the prediction set
    end_date: str, upper bound of the prediction set
    remove_no_school: bool, wether of not non working days are removed from training set
    remove_outliers: bool, wether of not non outliers days are removed from training set
    data_path: str, folder where data files are stored
    confidence: float, between 0 and 1
    """
    # split prediction_input/train based on dates
    train_data, prediction_input_data = split_train_predict(min_date, max_date, begin_date, end_date)
    train_data = filter_data(train_data, remove_no_school, remove_outliers, begin_date)

    if len(train_data) == 0:
        raise EmptyTrainingSet(f"cannot build a training set between {min_date} and {max_date}")

    if len(prediction_input_data) == 0:
        raise MissingDataForPrediction(f"cannot build prediction set between {begin_date} and {end_date}")

    if training_type == 'xgb':
        preds, feature_importance = app.algorithms.xgb_train_and_predict(
            column_to_predict,
            train_data,
            prediction_input_data,
            data_path)

        file_fi = f'output/variables_explicatives/{column_to_predict}_{begin_date}_{end_date}.txt'
        file = open(file_fi, 'w+')
        for element in feature_importance:
            file.write(f'{element[0]}: {element[1]}')
            file.write('\n')
        file.close()

    if training_type == 'xgb_interval':
        preds, feature_importance = app.algorithms.xgb_interval_train_and_predict(
            column_to_predict,
            train_data,
            prediction_input_data,
            confidence,
            data_path)

        file_fi = f'output/variables_explicatives/{column_to_predict}_{begin_date}_{end_date}.txt'
        file = open(file_fi, 'w+')
        for element in feature_importance:
            file.write(f'{element[0]}: {element[1]}')
            file.write('\n')
        file.close()

    if training_type == "benchmark":
        preds = app.algorithms.benchmark_train_and_predict(
            column_to_predict,
            train_data,
            prediction_input_data)

    # force week_ends, wednesday and holidays to 0 and complete nans
    mask = (preds["working"] == 0)
    preds.loc[mask, "output"] = 0

    # to check if data predicted can be evaluated
    # we compute the percentage of nan in the original dataset between begin_date and end_date
    nb_working_days = len(preds.loc[~mask, 'reel'])
    is_data_evaluable = preds.loc[~mask, 'reel'].apply(lambda x: not math.isnan(x) and x > 0).sum() / nb_working_days > .5

    print("################### Exporting results ################### ")
    preds[column_to_predict] = preds[column_to_predict].fillna(0)
    preds["prevision"] = preds["prevision"].fillna(0)
    preds["output"] = preds['output'].fillna(0)

    export_predictions(preds, "output", f"results_detailed_{column_to_predict}_{begin_date}_{end_date}.csv")
    export_predictions(
        preds.groupby(["date_str"])['output'].agg('sum'),
        "output",
        f"results_global_{column_to_predict}_{begin_date}_{end_date}.csv")
    export_predictions(
        preds.groupby(["date_str", "cantine_nom", "cantine_type"])['output'].agg('sum'),
        "output",
        f"results_by_cafeteria_{column_to_predict}_{begin_date}_{end_date}.csv")

    if is_data_evaluable:
        print("######## The app has run on existing data, results will be evaluated. ########")

        # remove 0 for evaluation
        preds = preds[preds[column_to_predict] != 0]

        print("-------- AVERAGE OF ALL INDIVIDUAL PREDICTIONS")
        evaluate_predictions(preds[column_to_predict], preds["prevision"], preds['output'])
        print("-------- AVERAGE OF PREDICTIONS AGGREGATED BY DAY (for logistics)")
        evaluate_predictions(
            preds.groupby("date_str")[column_to_predict].sum(),
            preds.groupby("date_str")["prevision"].sum(),
            preds.groupby("date_str")['output'].sum())
        print("-------- BY CAFETERIAS DETAILS:")
        evaluate_predictions_by_resolution(column_to_predict, preds, 'output', ['cantine_nom'])
        print("-------- BY DAY DETAILS:")
        evaluate_predictions_by_resolution(column_to_predict, preds, 'output', ['date_str'])

        preds["relative_error"] = preds["output"] - preds[column_to_predict]

        ## To debug : generates errors on windows with Reticulate
        # plot_error(preds, "result_xgb_error")
    else:
        print("######### The app has run on new data, results cannot be evaluated. ########")
    return preds
