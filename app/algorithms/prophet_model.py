#!/usr/bin/python3
# -----------------------------------------------------------
# Train multiple time series models based on prophet
# -----------------------------------------------------------
import pandas as pd
from fbprophet import Prophet

from app.log import logger


# pylint: disable= too-many-locals
def prophet_train_and_predict(column_to_predict, train_data, test_data):
    """
    train a prophet time serie model for each (cantine_nom, cantine_type) of train_data
    and generates prediction for test_data
    """
    preds = []
    sites = []
    for resolution, data in train_data.groupby(['cantine_nom', 'cantine_type']):
        logger.info("STARTING %s", resolution)
        features = [
            # "holidays_in",
            # "holidays_ago",
            # "non_working_in",
            # "non_working_ago",
            # "weekends_in",
            # "weekends_ago"
        ]
        data = data[['date_str', column_to_predict] + features]
        data.columns = ['ds', 'y'] + features
        model = Prophet()

        for col in features:
            model.add_regressor(col)
        model.fit(data)

        # specify starting date + add holidays as extra regressors for prediction
        # add special days to
        future_data = model.make_future_dataframe(periods=365, freq='d')
        forecast = model.predict(future_data)
        pred = forecast[["ds", "yhat"]]
        pred["cantine_nom"] = resolution[0]
        pred["cantine_type"] = resolution[1]
        preds.append(pred)
        sites.append(resolution[0])

    df_pred = pd.concat(preds)
    df_pred["ds"] = df_pred["ds"].dt.strftime('%Y-%m-%d')
    test_data = test_data.loc[test_data["cantine_nom"].isin(sites)]
    test_data = test_data.merge(
        df_pred,
        left_on=['date_str', "cantine_nom", 'cantine_type'],
        right_on=['ds', "cantine_nom", 'cantine_type'],
        how="left")
    test_data['output'] = test_data["yhat"]

    return test_data
