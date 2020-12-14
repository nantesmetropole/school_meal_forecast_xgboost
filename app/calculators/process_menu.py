#!/usr/bin/python3
# -----------------------------------------------------------
# Calculator to add meals description features to a dataset
# -----------------------------------------------------------
from collections import Counter
import json
import os
import re

import dask.dataframe as dd
import pandas as pd


def delete_special_char(text):
    """
    given a string, remove all special chars among ([)]{}.+
    """
    return re.sub(r'[\(\[\)\]\{\}\.]+', '', text)


def _parser(date):
    """
    date parser to cast a string in the format "%d/%m/%Y" to a date
    """
    return pd.datetime.strptime(date, "%d/%m/%Y")


def add_feature_special_meals(all_dates, col_to_merge, date_format, data_path):
    """"
    given a dataframe with a date_col `col_to_merge` of format date_format and a date index
    add a new columns based on:
    - the menus csv files in data_path using the same date_format
    - the dictionnary of meals to identify providen through app/data/calculators/menus.json
    """
    menus = dd.read_csv(f"{data_path}/raw/menus_*.csv", parse_dates=['date'], date_parser=_parser)
    menus = menus.compute()
    menus[col_to_merge] = menus['date'].apply(lambda x: pd.datetime.strftime(x, date_format))

    dict_special_dishes = {}
    with open(os.path.join(data_path, "calculators/menus.json")) as f_in:
        dict_special_dishes = json.load(f_in)

    for spcial_menu, list_of_food in dict_special_dishes.items():
        menus[spcial_menu] = menus['plat']
        menus[spcial_menu] = menus[spcial_menu].apply(lambda plat: any(word in plat.lower() for word in list_of_food))

    menus['info_menu'] = menus['plat']
    menus['info_menu'] = menus['info_menu'].apply(lambda plat: 1 if plat else 0)
    keys_of_interest = [col_to_merge] + ['info_menu'] + list(dict_special_dishes.keys())
    menus_features = menus[keys_of_interest].groupby([col_to_merge]).any().astype(int).reset_index()

    all_dates = all_dates.merge(menus_features, left_on=[col_to_merge], right_on=[col_to_merge], how='left')

    for spcial_menu, _ in dict_special_dishes.items():
        all_dates[spcial_menu] = all_dates[spcial_menu].fillna(0)
    all_dates['info_menu'] = all_dates['info_menu'].fillna(0)

    return all_dates


def meals_composition(data_path):
    """
    given data_path where menus_*.csv files are located, generates and return a dictionnary with:
    - dishes as keys
    - number of occurences as values
    after removing french stop words and special chars
    """
    menus = dd.read_csv(f"{data_path}/raw/menus_*.csv", parse_dates=['date'], date_parser=_parser)
    menus['words'] = menus['plat'].apply(lambda x: re.split(r'\+|\s|\/|\'', delete_special_char(x.lower())))
    slist = []
    for item in menus['words'].compute():
        slist.extend(item)

    words_ordered = dict(sorted(Counter(slist).items(), key=lambda item: item[1]))
    stop_words = ["le", "la", "l", "aux", "au", "d", "des", "du", "à", "un", "une", "avec"]

    for key in stop_words:
        words_ordered.pop(key, None)

    return words_ordered
