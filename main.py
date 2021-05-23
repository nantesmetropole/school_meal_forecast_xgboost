#!/usr/bin/python3
# -----------------------------------------------------------
# run school meal forecast app
# -----------------------------------------------------------

import argparse
import glob
import os
import sys

from pathlib import Path

from app.log import logger
from app.preprocess import compute_min_max_date, smarter_process_data
from app.train import train_and_predict


def load_arguments(args):
    """
    Loads arguments from user input through command line
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-preprocessing",
        dest='preprocessing',
        default=True,
        action='store_false',
        help="whether features should be recaulated or not")

    parser.add_argument(
        "--train-on-no-school-days",
        dest='remove_no_school',
        default=True,
        action='store_false',
        help="whether no school days should be removed from training and prediction set")

    parser.add_argument(
        "--train-on-outliers",
        dest='remove_outliers',
        default=True,
        action='store_false',
        help="whether to include outliers during training stage")

    parser.add_argument(
        "--training-type",
        dest='training_type',
        type=str,
        nargs='?',
        default='xgb',
        help="the algo type to train among 'xgb' or 'prophet'")

    parser.add_argument(
        "--confidence",
        dest='confidence',
        type=float,
        nargs='?',
        default=0.90,
        help="When using xgb_interval, the confidence interval to use for prediction bounds")

    parser.add_argument(
        "--start-training-date",
        dest='start_training_date',
        type=str,
        nargs='?',
        default='2012-09-01',
        help="begin date for training set using date format 'YYYY-MM-DD'")

    parser.add_argument(
        "--begin-date",
        dest='begin_date',
        type=str,
        nargs='?',
        default='',
        help="begin date for prediction or evaluation using date format 'YYYY-MM-DD'")

    parser.add_argument(
        "--end-date",
        dest='end_date',
        type=str,
        nargs='?',
        default='',
        help="end date for prediction or evaluation using date format 'YYYY-MM-DD'")

    parser.add_argument(
        "--school-cafeteria",
        dest='school_cafeteria',
        type=str,
        nargs='?',
        default='',
        help="specify prediction for one school_cafeteria")

    parser.add_argument(
        "--evaluation-mode",
        dest='prediction_mode',
        default=True,
        action='store_false',
        help="whether application predicts new values or evalute existing ones")

    parser.add_argument(
        "--data-path",
        dest='data_path',
        type=str,
        nargs='?',
        default='data',
        help="the folder containing data files")

    parser.add_argument(
        "--column-to-predict",
        dest='column_to_predict',
        type=str,
        nargs='?',
        help="the column to predict")

    parser.add_argument(
        "--week-latency",
        dest='weeks_latency',
        type=int,
        nargs='?',
        default=10,
        help="the column to predict")

    return parser.parse_args(args)


def prepare_arborescence():
    """
    create project folders if not existing
    """
    project_directories = {
        "output_folder": "output",
        "staging": "output/staging",
        "figures": "output/figs",
        "features_importance": "output/variables_explicatives",
    }
    for _, directory in project_directories.items():
        Path(directory).mkdir(parents=True, exist_ok=True)


def run(args):
    """
    run preprocessing, training and prediction
    """
    date_format = '%Y-%m-%d'
    include_wednesday = False

    min_date, max_date = compute_min_max_date(
        args.start_training_date,
        args.begin_date,
        args.end_date,
        date_format,
        args.weeks_latency)

    if args.school_cafeteria:
        school_cafeterias = [args.school_cafeteria]
    else:
        school_cafeterias = []

    if args.column_to_predict not in ["prevision", "reel"]:
        logger.info("bad choice of column to predict")
        return

    missing_calculator_data, missing_mapping_data, missing_raw_data = check_data_exist(args.data_path)
    if missing_calculator_data:
        logger.info(
            "Missing input calculators data in %s: %s",
            os.path.join(args.data_path, "calculators"),
            missing_calculator_data)
    if missing_mapping_data:
        logger.info(
            "Missing input mappings data in %s: %s",
            os.path.join(args.data_path, "mappings"),
            missing_mapping_data)
    if missing_raw_data:
        logger.info(
            "Missing input raw data in %s: %s",
            os.path.join(args.data_path, "raw"),
            missing_raw_data)
    if missing_calculator_data or missing_mapping_data or missing_raw_data:
        return

    # start computation
    if args.preprocessing:
        logger.info("------------- preprocessing ----------------")
        smarter_process_data(args.data_path, min_date, args.end_date, school_cafeterias, include_wednesday, date_format)
        logger.info("------------- preprocessing finished ----------------")

    if args.prediction_mode and args.training_type:
        logger.info("------------- train & prediction step ----------------")
        _ = train_and_predict(
            args.column_to_predict,
            args.training_type,
            min_date,
            max_date,
            args.begin_date,
            args.end_date,
            args.remove_no_school,
            args.remove_outliers,
            args.data_path,
            args.confidence)
        logger.info("------------- finished ----------------")


def check_data_exist(data_path):
    """
    Check that all files exist in order to run the app
    """
    # check calculators data
    missing_calculator_data = []
    for file in ["annees_scolaires.csv", "greves.csv", "jours_feries.csv", "menus.json", "vacances.csv"]:
        if not os.path.exists(os.path.join(data_path, "calculators", file)):
            missing_calculator_data.append(file)

    missing_mapping_data = []
    for file in ["mapping_ecoles_cantines.csv", "mapping_frequentation_cantines.csv"]:
        if not os.path.exists(os.path.join(data_path, "mappings", file)):
            missing_mapping_data.append(file)

    missing_raw_data = []
    for file in ["cantines.csv", "effectifs.csv", "frequentation.csv"]:
        if not os.path.exists(os.path.join(data_path, "raw", file)):
            missing_raw_data.append(file)

    for file in ["menus_*.csv"]:
        if not glob.glob(os.path.join(data_path, "raw", file)):
            missing_raw_data.append(file)

    return missing_calculator_data, missing_mapping_data, missing_raw_data


def main():
    """
    run school-meal-forecast app
    """
    logger.info("############### Starting app ###############")

    # create arborescence
    prepare_arborescence()

    # load parameters
    args = load_arguments(sys.argv[1:])
    if args.confidence < 0.0 or args.confidence > 1.0:
        raise argparse.ArgumentTypeError("%r not in range [0.0, 1.0]" % (args.confidence,))

    run(args)

    logger.info("############### Terminating app ###############")

