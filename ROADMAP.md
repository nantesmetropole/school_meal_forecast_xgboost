# The school-meal-forecast Roadmap

The goal of the school-meal-forecast project is to help estimate the number of guests per school cafeteria per day on a given period.
This document describes the plan for the project.

The best way to give feedback is to open an issue in this repo.

## Goals for future improvements

### Include Regex in menu pre-processing
Use regex (re) instead of litteral matching in [process_menu.py](/app/calculators/process_menu.py/), around line 45.

### Analyse feature contribution per day and school
Use the library eli5 to return an explanation from XGboost prediction with feature weights at event level.
A complementary option consists in adding a tree visualisation function.


### Consider size of meals
Currently a number of guests is predicted but this does not take into account the weight of the portion of food which depends on the profile of the guest (child, adult)

### Interface for the model
Command line tools may not be easy to use. Thus providing a dashboard or an API to help the user to train and monitor models but also to load new data seems important.
