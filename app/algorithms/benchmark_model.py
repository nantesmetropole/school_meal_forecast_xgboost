#!/usr/bin/python3
# -----------------------------------------------------------
# Train a statistics model based on average values
# -----------------------------------------------------------
from app.log import logger


def benchmark_train_and_predict(column_to_predict, train_data, test_data):
    """
    add a prediction column to `test_data` called `output` which contains exactly
    the statistical features computed during preprocessing:
    'frequentation_prevue' or 'frequentation_reel' times 'effectif'
    """
    logger.info("----------- check training data -------------")
    for resolution, dtf in train_data.groupby(['cantine_nom', 'cantine_type']):
        logger.info("canteen %s has %s days of history to train on starting on %s and ending on %s",
                    resolution,
                    len(dtf),
                    dtf["date_str"].min(),
                    dtf['date_str'].max(),
                    )

    if column_to_predict == "prevision":
        test_data['output'] = test_data['frequentation_prevue'] * test_data['effectif']
    else:
        test_data['output'] = test_data['frequentation_reel'] * test_data['effectif']

    logger.info("----------- check predictions -------------")
    for resolution, dtf in test_data.groupby(['cantine_nom', 'cantine_type']):
        logger.info("canteen %s has predictions for %s days starting on %s and ending on %s",
                    resolution,
                    len(dtf),
                    dtf["date_str"].min(),
                    dtf['date_str'].max(),
                    )

    logger.info("----------- export predictions -------------")

    return test_data
