reticulate::use_virtualenv("./venv_shiny_app", required = TRUE)
usethis::edit_r_environ()
    #RETICULATE_PYTHON="/home/florent/.pyenv/versions/3.7.10/bin/python3.7"
    #RETICULATE_PYTHON="./venv_shiny_app"
# reticulate::install_python(version = "3.7.10")
# reticulate::virtualenv_remove('./venv_shiny_app')
if (!reticulate::virtualenv_exists(envname = "./venv_shiny_app")) {
  reticulate::virtualenv_create(envname = './venv_shiny_app')
  # readLines("requirements.txt")
  reticulate::virtualenv_install('./venv_shiny_app',
                                 packages = c("pandas==1.1.0",
                                              "numpy==1.19.1",
                                              "xgboost==1.1.1",
                                              "scikit-learn==0.23.1",
                                              "dask[dataframe]==0.19.4",
                                              "lunardate==0.2.0",
                                              "convertdate==2.2.1",
                                              "matplotlib==3.2.1",
                                              "python-dateutil==2.8.1"))
}

# test