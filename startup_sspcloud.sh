#!/bin/sh

# Est-ce que ça marche d'installer python au démarrage ?
sudo apt install python3.8-venv


# Create variables
WORK_DIR=/home/rstudio/school_meal_forecast_xgboost
REPO_URL=https://github.com/fBedecarrats/school_meal_forecast_xgboost
TEMP_DIR=${WORK_DIR}/temp

# Git
git clone $REPO_URL $WORK_DIR
chown -R rstudio:users $WORK_DIR

# Folders to store data and documentation
mkdir $TEMP_DIR


# launch RStudio in the right project
# Copied from InseeLab UtilitR
    echo \
    "
    setHook('rstudio.sessionInit', function(newSession) {
        if (newSession && identical(getwd(), path.expand('~')))
        {
            message('On charge directement le bon projet :-) ')
            rstudioapi::openProject('~/school_meal_forecast_xgboost')
            }
            }, action = 'append')
            " >> /home/rstudio/.Rprofile