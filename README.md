## Overview  

This application aims at helping estimate the number of guests per school cafeteria per day on a given period. It needs past data to work. Examples of files can be found in `test/data` (see **Data** Section for more details). 
The tool was developed by [Verteego](https://www.verteego.com/) on behalf of Ville de Nantes and Nantes Métropole. Other contributions are welcome, see the file CONTRIBUTION.md


## Structure of the app

```
.
├── .gitignore.py
├── .gitlab-ci.yml        # Continuous integration
├── .pylintrc             # Style check
├── main.py               # Launch file
├── .requirements.txt     # Dependencies
├── app                   # Source files
|  ├── algorithms         # Implementation of the different models available
|  ├── calculators        # Files used to preprocess data
|  ├── __init__.py
|  ├── exceptions.py      # Source file to define custom exceptions
|  ├── log.py             # Source file handle logging through the project
|  ├── plot.py            # Source file to plot results of train.py
|  ├── preprocess.py      # Source file to prepare data
|  └── train.py           # Source file to chose a model, train it and predict
├── tests                 # Automated tests
|  ├── app                # Automated tests of the app
|  ├── calculators        # Automated tests of the calculators
|  ├── data               # Example of data to run the project
|  |   ├── calculators    # More details in Data section
|  |   ├── mappings       # More details in Data section
|  |   └── raw            # More details in Data section
|  └── fixtures           # Items used for verification of automated tests
├── CODE_OF_CONDUCT.md
├── LICENSE.md
├── README.md
└── ROADMAP.md
```

## Running the app

To run the project please:

1/ clone this repository

2/ recommended: set up a local virtual env using **python 3.7** (e.g. `virtualenv venv-37 --python=python3.7`)
and activate it (e.g. `source venv-37/bin/activate`).
*Note that if you are using python 3.8 you may have issues with the installation of fbprophet.*

3/ install python requirements using `pip install -r requirements.txt`  
*Note for Windows users:  
If python is not installed on the machine, install it (Anaconda is recommended). If already present, update python (in Windows search bar, search for the application Anaconda Prompt, launch it, type conda update conda and press ENTER key.
By default, Anaconda installs Python 3.7. If asked during the installation process, please select python version 3.7 (fbprophet malfunctions with 3.8 at the time of writing this README, i.e. Nov. 2020). In case of errors when installing fbprophet from pip, install it from conda forge by typing in Andaconda Prompt: `conda install -c conda-forge fbprophet`.*

4/ ensure you've got files in your data folder `{--data-path}` by default, use `tests/data`. If you want to use your own data, refer to **Data** Section

5/ run `python main.py` with the following arguments:
  - `--begin-date`: predictions begin date using the format `YYYY-mm-dd`
  - `--end-date`: predictions end date using format `YYYY-mm-dd`
  - `--column-to-predict`: the column you want to predict
  - `--start-training-date`: optional, earliest date to train on using format `YYYY-mm-dd` default is set to `2012-09-01`
  - `--data-path`: optional, path to data files (use `tests/data` to check that the project is running) default is set to `data/`
  - `--week-latency`: optional, which is the number of weeks between last day of training set that can be used and begining of prediction. This parameter is introduced for *evaluation purpose*, in order to easily mimic the fact that data files from `--data-path` should emulate a "past" training set and a "future" test set. Technically, `--week-latency` is used to compute the end date of this training set which is exactly `--begin-date` minus `--week-latency`. By default, this number is set to `10` which means that the model will be trained using all data available `--start-training-date` and `--begin-date` minus 10 weeks. This corresponds to a classic scenario considering our use case.

  Note that test files contains a small scope of dates. Here is an example of working command line for this project with test data:
  ```
  python main.py \
    --begin-date 2017-09-30 \
    --end-date 2017-12-15 \
    --start-training-date 2016-10-01 \
    --data-path tests/data \
    --column-to-predict reel
  ```

6/ 4 files are generated, 1 preprocessed dataset and 3 predictions files:
  - `output/staging/prepared_data_{begin_date}_{end_date}.csv` is the preprocessed dataset thanks to which training and prediction is performed
  - `output/results_detailed_{column_to_predict}_{begin_date}_{end_date}.csv` contains predictions by cafeteria by dates with all features
  - `output/results_global_{column_to_predict}_{begin_date}_{end_date}.csv` contains predictions summed by day without all features
  - `output/results_by_cafeteria_{column_to_predict}_{begin_date}_{end_date}.csv` contains predictions by cafeteria by dates without all features

  Note that feature importance is also exported in `output/variables_explicatives/{column_to_predict}_{begin_date}_{end_date}.txt`.


7/ if you want to explore and tune the trainings, you can use the following optional parameters:
  - `--training-type`: optional, type of training algorithm (`xgb`, `xgb_interval`, `prophet` or `benchmark` refer to **Algorithms** Section) default is set to `xgb`
  - `--confidence`: optional, when using `xgb_interval` as `--training-type`, allows specifying the confidence interval (between 0 and 1) to base predictions on, by default the confidence interval chosen is 0.90 (i.e. 90%)
  - `--no-preprocessing`: optional, only training and prediction will be performed on an existing preprocessed dataset   
  - `--evaluation-mode`: optional, only prediction will be performed on an existing preprocessed dataset
  - `--train-on-no-school-days`: optional, precossing will not filter no school days out of the preprocessed dataset
  - `--train-on-outliers`: optional, preprocessing will not filter 3 sigma outliers out of the preprocessed dataset
  - `--school-cafeteria`: optional, preprocessing, training and evaluation will be done only for this specific cafeteria (if you want to add multiple cafeteria, please repeat this argument for each cafeteria you want to use)


## Data

Examples of files can be found in `tests/data`. Those examples are small extracts of real data and won't provide good predictions.
Those files can be distinguished in 3 categories detailed in their own subsection:
 - raw files
 - calculators related files
 - mapping files to link columns of distinct raw files

*Note that those files must be encoded in UTF-8 and use comma as separator*


### raw files

This project has been implemented considering the following files. Thus it cannot work without them.
Note that Data files contain information related to France, thus their names are in French for more convenience to the users.

*Note that among those files categorical features are automatically one hot encoded.
Thus, one can change the possible values but must ensure that they remain consistent along the files.*

- `{--data-path}/raw/cantines.csv` of which keys are (`cantine_name`, `cantine_type`)
It contains the list of school cafeterias for which a prediction may be requested.

- `{--data-path}/raw/frequentation.csv` of which keys are (`site_nom`, `site_type`, `date`)
It contains the history of the frequentation of every school cafeteria for each date. Note that `site_nom` and `site_type` may contain typos or errors, thus a mapping file is needed to make the link with `{--data-path}/raw/cantines.csv`

- `{--data-path}/raw/effectifs.csv` of which keys are (`ecole`, `annee_scolaire`)
It contains the number of students per school for each school year. Note that a mapping file is required to link each school to each school cafeteria.

- `{--data-path}/raw/menus_*.csv` of which keys are `date`
It sums up the options available for the meal of each day.

### calculators
`{--data-path}/calculators` contains files used to compute external features.

- `annees_scolaires.csv`
- `greves.csv`
- `jours_feries.csv`
- `vacances_nantes.csv`


### mappings

The 2 mappings can be generated automatically or manually depending on the complexity of your data.

- `{--data-path}/mappings/mapping_ecoles_cantines.csv` maps schools of `effectifs.csv` to school cafeterias of `cantines.csv`

- `{--data-path}/mappings/mapping_frequentation_cantines.csv` maps school cafeterias of `frequentation.csv` to real school cafeterias of `cantines.csv`


## Algorithms

One can specify the method used to provide predictions. Three main methods are available:
 - `benchmark`: computes and uses as prediction the average number of guests of each school cafeteria per week
 - `xgb`: is a globally trained gradient boosting model using `xgboost` library
 - `xgb_interval`: train two gradient boosting models using `xgboost` library on the bounds of the dedicated confidence interval. The `output` field will contain an upper_bound. To get both upper and lower_bound predicted, please refer to the corresponding fields of the file `output/results_detailed_{column_to_predict}_{begin_date}_{end_date}.csv`
 More details on the implementation can be found here: https://towardsdatascience.com/confidence-intervals-for-xgboost-cac2955a8fde
*Note: This is a predictive method. Occasionally, upper bound and lower bound seem to be reversed, thus a maximum filtering is applied before choosing the output result.*
 - `prophet`: is performing time series analysis using `fbprophet` **note that one model is trained per school cafeteria, this may thus take more time to train**


## Continuous Integration

This project uses Gitlab-CI to check:  
  - global code quality (using `pylint` and `pycodestyle`) see `pylintrc`
  - code correctness of some of its components (using `pytest`) see `tests/`



## Parameters for developers

Some parameters in the code can be updated if needed. They are listed in function `run` of `main.py`. **Those parameters have been added in order to be handle to handle future situations but are not sufficient to handle them properly.** The tests may not pass if those parameters are updated.
  - `include_wednesday` (nominal case set to `False`) this parameter consider Wednesday as a non-working day. Wednesdays are thus removed from the training set and a prediction output of 0 is set for them.
  - `date_format` (nominal case set to `%Y-%m-%d`) this parameter is the format of date for all the files used in the project. If you change this format, dates comparisons may encounter errors.
  - One can decide to predict confidence intervals setting the parameter `confidence_intervale` inside `train.py` function `train_and_predict` to an actual percentage. (nomical value is `None`). Note that this will predict additionnal columns that won't be exported.




## License

The code of this project was developped by Verteego on behalf of Nantes Métropole under the MIT license.
Please refer to LICENSE.md
