#!/usr/bin/python3
# -----------------------------------------------------------
# Calculator to add date attributes features to the dataset
# -----------------------------------------------------------
import datetime


# pylint: disable=too-many-return-statements
def _calc_date_attribute(dte, attribute, date_format):
    """
    Extract date attributes from date (year, month, day, week, and/or weekday) given a format
    """

    if not dte or isinstance(dte, float):
        raise ValueError(f"Invalid date: '{dte}'")
    try:
        datetime.datetime.now().strftime(date_format)
    except ValueError:
        raise ValueError(f"Invalid format: '{date_format}'") from None

    if isinstance(dte, str):
        dte = datetime.datetime.strptime(dte, date_format)

    if dte.year < 2000:
        raise ValueError(f"Incoherent date: '{dte}'", )

    if attribute == "month":
        return dte.month
    if attribute == "day":
        return dte.day
    if attribute == "weekday":
        return dte.weekday()
    if attribute == "week":
        return dte.isocalendar()[1]
    if attribute == "year":
        return dte.year

    raise ValueError(f"Unrecognized attribute '{attribute}'")


def add_feature_date_attributes(dtf, date_col, attributes_list, date_format):
    """
    Given a dataframe dtf, a date column date_col and it's date format date_format
    extract date attributes (attributes_list) from date_col (within year, month, day, week, and/or weekday)
    """
    for attribute in attributes_list:
        # pylint: disable=cell-var-from-loop
        def _calculator(row):
            return _calc_date_attribute(row[date_col], attribute, date_format)
        dtf[attribute] = dtf[[date_col]].apply(_calculator, axis=1)

    return dtf
