#!/usr/bin/python3
# -----------------------------------------------------------
# Calculator to add countdown features to the dataset
# -----------------------------------------------------------
import calendar
import datetime
from enum import Enum
import dateutil
import lunardate
import convertdate
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype as is_datetime


class Events(Enum):
    """
    A class used to represent all Events as Enum
    """
    EPIPHANIE = "epiphanie"
    CHANDELEUR = "chandeleur"
    MARDI_GRAS = "mardi_gras"
    HALLOWEEN = "halloween"
    NOUVEL_AN_CHINOIS = "nouvel_an_chinois"
    AID = "aid"
    RAMADAN = "ramadan"


def compute_last_weekday_of_a_month(year, month, weekday):
    """
    given a year, month and weekday (1 = monday, 2 = tuesday, ..., 7 = sunday)
    returns the last occurence of this weekday in this month of this year as a date
    """

    last_day = max(
        week[-1 + weekday] for week in calendar.monthcalendar(year, month)
    )
    return datetime.date(year, month, last_day)


def compute_first_weekday_of_a_month(year, month, weekday):
    """
    given a year, month and weekday (1 = monday, 2 = tuesday, ..., 7 = sunday)
    returns the first occurence of this weekday in this month of this year as a date
    """
    first_day = min(
        week[-1 + weekday] for week in calendar.monthcalendar(year, month) if week[-1 + weekday] > 0
    )
    return datetime.date(year, month, first_day)


def compute_events_dates(years):
    """
    For a given list of years compute a dict of events with a list of dates for each event
    """

    events_dates_by_event = {}
    for event in Events:
        events_dates_by_event[event] = []

    for year in years:
        # epiphanie
        events_dates_by_event[Events.EPIPHANIE].append(datetime.date(year, 1, 6))
        # chandeleur
        events_dates_by_event[Events.CHANDELEUR].append(datetime.date(year, 2, 2))
        # mardi_gras :
        date_easter = dateutil.easter.easter(year, 3)
        # date_easter = easter(year)
        events_dates_by_event[Events.MARDI_GRAS].append(date_easter - datetime.timedelta(days=47))

        # Halloween : 31/10
        events_dates_by_event[Events.HALLOWEEN].append(datetime.date(year, 10, 31))

        # Ramadan
        islamic_year = convertdate.islamic.from_gregorian(year, 1, 1)[0]
        ramadan = datetime.datetime(
            convertdate.islamic.to_gregorian(islamic_year, 9, 1)[0],
            convertdate.islamic.to_gregorian(islamic_year, 9, 1)[1],
            convertdate.islamic.to_gregorian(islamic_year, 9, 1)[2],
        )
        events_dates_by_event[Events.RAMADAN].append(ramadan.date())
        # aid
        events_dates_by_event[Events.AID].append((ramadan + datetime.timedelta(days=30)).date())
        # chinese new year
        events_dates_by_event[Events.NOUVEL_AN_CHINOIS].append(lunardate.LunarDate(year, 1, 1, 0).toSolarDate())

    return events_dates_by_event


def add_countdown_ago(date, event, events_dates_per_event):
    """
    Given a date and an even,
    compute the number of days since the previous occurence of this events within events_dates_per_event
    """
    countdown = []
    for special_date in events_dates_per_event[event]:
        date_count_down = (special_date - date).days
        if date_count_down <= 0:
            countdown.append(date_count_down)

    return -1 * max(countdown)


def add_countdown_in(date, event, events_dates_per_event):
    """
    Given a date and an even,
    compute the number of days until the next occurence of this events within events_dates_per_event
    """
    countdown = []
    for special_date in events_dates_per_event[event]:
        date_count_down = (special_date - date).days
        if date_count_down >= 0:
            countdown.append(date_count_down)

    return min(countdown)


# pylint: disable=W0613
def add_feature_events_countdown(dtf, date_col, date_format):
    """
    Given a dataframe dtf, a date_col and its format date_format generate two cols:
    - number of days before next event occurence
    - number of day since last event occurence
    for each of the following events:
    - epiphanie
    - chandeleur
    - mardi_gras
    - halloween
    - nouvel_an_chinois
    - aid
    - ramadan
    """
    col_retyped = False
    if not is_datetime(dtf[date_col]):
        new_date_col = f'{date_col}_retyped'
        dtf[new_date_col] = pd.to_datetime(dtf[date_col], format=date_format)
        date_col = new_date_col
        col_retyped = True

    years = range(dtf[date_col].min().year - 2, dtf[date_col].max().year + 2)
    events_dates = compute_events_dates(years)

    for event in Events:
        dtf[str(event) + "_in"] = dtf.apply(
            lambda row, evt=event: add_countdown_ago(row[date_col].date(), evt, events_dates),
            axis=1)
        dtf[str(event) + "_ago"] = dtf.apply(
            lambda row, evt=event: add_countdown_in(row[date_col].date(), evt, events_dates),
            axis=1)
    if col_retyped:
        dtf.drop(date_col, inplace=True, axis=1)

    return dtf
