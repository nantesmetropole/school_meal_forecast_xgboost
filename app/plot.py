#!/usr/bin/python3
# -----------------------------------------------------------
# Plot training and results
# -----------------------------------------------------------
from matplotlib import pyplot
import numpy as np


def plot_curve(results, name):
    """
    Plot training cuvers to check overfitting
    """
    for metric_key, _ in results['validation_0'].items():

        epochs = len(results['validation_0'][metric_key])
        x_a_xis = range(0, epochs)
        _, a_x = pyplot.subplots()
        a_x.plot(x_a_xis, results['validation_0'][metric_key], label='Train')
        if len(results) == 2:
            a_x.plot(x_a_xis, results['validation_1'][metric_key], label='Test')
        a_x.legend()
        pyplot.ylabel(metric_key)
        pyplot.title(f"ALGO {metric_key}")
        pyplot.savefig(f"output/figs/{name}_{metric_key}.png")


def plot_confidence_intervale(res, x_test, y_test, y_upper_smooth, y_lower_smooth, ):
    """
    Plot confidence interval predicted as curves
    """
    index = res['upper_bound'] < 0
    print(res[res['upper_bound'] < 0])
    print(x_test[index])

    max_length = 150
    _ = pyplot.figure()
    pyplot.plot(list(y_test[:max_length]), 'gx', label=u'real value')
    pyplot.plot(y_upper_smooth[:max_length], 'y_', label=u'Q up')
    pyplot.plot(y_lower_smooth[:max_length], 'b_', label=u'Q low')
    index = np.array(range(0, len(y_upper_smooth[:max_length])))
    pyplot.fill(
        np.concatenate([index, index[::-1]]),
        np.concatenate([y_upper_smooth[:max_length], y_lower_smooth[:max_length][::-1]]),
        alpha=.5, fc='b', ec='None', label='90% prediction interval')
    pyplot.xlabel('$index$')
    pyplot.ylabel('$duration$')
    pyplot.legend(loc='upper left')
    pyplot.show()


def plot_error(dataset, name, resolution=None):
    """
    Plot errors as bar chart
    """
    if resolution:
        for res, data in dataset.groupby(resolution):
            data_to_trace = data.groupby("date_str")["relative_error"].sum()
            _ = pyplot.figure(figsize=(20, 20))
            pyplot.bar(data_to_trace.index, data_to_trace)
            pyplot.legend()
            pyplot.grid(True)
            pyplot.xticks(rotation='vertical')
            pyplot.axhline(0, color='black', lw=1)
            pyplot.ylabel("error")
            pyplot.title(f"relative error by day for {res}")
            pyplot.savefig(f"output/figs/{name}_{res.replace('/', ' ')}_error.png")
    else:
        data_to_trace = dataset.groupby("date_str")["relative_error"].sum()
        _ = pyplot.figure(figsize=(20, 20))
        pyplot.bar(data_to_trace.index, data_to_trace)
        pyplot.legend()
        pyplot.grid(True)
        pyplot.xticks(rotation='vertical')
        pyplot.axhline(0, color='black', lw=1)
        pyplot.ylabel("error")
        pyplot.title("relative error by day")
        pyplot.savefig(f"output/figs/{name}_error.png")
