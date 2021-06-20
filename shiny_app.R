# Set environment -------------------------------------------------------------
# Appropriate .Rprofile needs to be included in the project folder

virtualenv_dir = Sys.getenv("VIRTUALENV_NAME")
python_path = Sys.getenv("PYTHON_PATH")

if (!reticulate::virtualenv_exists(envname = "venv_shiny_app")) {
    reticulate::virtualenv_create(envname = virtualenv_dir, python = python_path)
    reticulate::virtualenv_install(virtualenv_dir, packages = c("pandas==1.1.0",
                                                                "numpy==1.19.1",
                                                                "xgboost==1.1.1",
                                                                "scikit-learn==0.23.1",
                                                                "dask[dataframe]==0.19.4",
                                                                "lunardate==0.2.0",
                                                                "convertdate==2.2.1",
                                                                "matplotlib==3.2.1",
                                                                "python-dateutil==2.8.1"))
}
reticulate::use_virtualenv(virtualenv = virtualenv_dir, required = TRUE)

# Libraries -------------------------------------------------------------------
# A function to install required functions
install_load <- function(mypkg, to_load = FALSE) {
    for (i in seq_along(mypkg)) {
        if (!is.element(mypkg[i], installed.packages()[,1])) {
            install.packages(mypkg[i], repos="http://cran.irsn.fr/")
        }
        if (to_load) { library(mypkg[i], character.only=TRUE)  }
    }
}
pkgs_to_load <- "shiny"
pkgs_not_load <- c("shiny","reticulate", "purrr", "DT", "readr", "arrow", "data.table")


# Parameters --------------------------------------------------------------
data_path <- "tests/data"
index <- tribble(
    ~name,          ~path,
    "schoolyears",  "calculators/annees_scolaires.csv",
    "strikes",      "calculators/greves.csv",
    "holidays",     "calculators/jours_feries.csv",
    "vacs",         "calculators/vacances.csv",
    "cafets",       "raw/cantines.csv",            
    "effs",         "raw/effectifs.csv",
    "freqs",        "raw/frequentation.csv",
    "menus",        "raw/menus_tous.csv",
    "map_schools",  "mappings/mapping_ecoles_cantines.csv",
    "map_freqs",    "mappings/mapping_frequentation_cantines.csv") %>%
    mutate(path = paste(data_path, path, sep = "/"))

# install_load(pkgs_to_load, to_load = TRUE)
install_load(pkgs_not_load)

# Python functions and R bindings ---------------------------------------------------
reticulate::source_python("main.py")

# Cette fonction exécute la fonction 'run' avec les paramètres par défaut du readme
run_verteego <- function(begin_date = '2017-09-30',
                         column_to_predict = 'reel', 
                         data_path = data_path,
                         confidence = 0.90,
                         end_date = '2017-12-15',
                         prediction_mode=TRUE,
                         preprocessing=TRUE,
                         remove_no_school=TRUE,
                         remove_outliers=TRUE,
                         school_cafeteria='',
                         start_training_date='2012-09-01',
                         training_type='xgb',
                         weeks_latency=10) {
    # On passe les arguments à pyton au travers d'une classe
    args <- PyClass(classname = "arguments", 
                    defs = list(
                        begin_date = begin_date, 
                        column_to_predict = column_to_predict, 
                        data_path = data_path, 
                        confidence = confidence,
                        end_date = end_date, 
                        prediction_mode = prediction_mode, 
                        preprocessing = preprocessing, 
                        remove_no_school = remove_no_school, 
                        remove_outliers = remove_outliers, 
                        school_cafeteria = school_cafeteria, 
                        start_training_date = start_training_date, 
                        training_type = training_type,
                        weeks_latency = weeks_latency))
    prepare_arborescence()
    run(args)
    # On récupère les trois outputs générés par la fonction
    path_results_global <- paste0("output/",
                                  paste("results_global", column_to_predict,
                                        begin_date, end_date, sep = "_"),
                                  ".csv")
    path_results_detailed <- paste0("output/",
                                    paste("results_detailed", column_to_predict,
                                          begin_date, end_date, sep = "_"), ".csv")
    path_results_by_cafeteria <- paste0("output/",
                                        paste("results_by_cafeteria", column_to_predict,
                                              begin_date, end_date, sep = "_"), ".csv")
    # Le signe '<<-' permet de conserver les objets hors du contexte d'exécution
    results_global <<- readr::read_csv(path_results_global)
    results_detailed <<- readr::read_csv(path_results_detailed)
    results_by_cafeteria <<- readr::read_csv(path_results_by_cafeteria)
}

# R functions -------------------------------------------------------------

# A function to load the outputs of the model forecasts
load_results <- function(folder = "output", pattern = "^results_by_cafeteria.*csv$") {
    dir(folder, pattern = pattern, full.names = TRUE) %>%
        dplyr::tibble(filename = ., created = file.info(.)$ctime) %>%
        dplyr::mutate(file_contents = purrr::map(filename, ~ arrow::read_csv_arrow(.))) %>%
        tidyr::unnest(cols = c(file_contents))
}

# A function to load the input data. Defaults to the index specified above
load_data <- function(name = index$name, path = index$path) {
    dt <- purrr::map(path, ~ arrow::read_csv_arrow(.)) %>%
        purrr::set_names(name)
}


# UI ----------------------------------------------------------------------
ui <- fluidPage(
    
    # Application title
    titlePanel("Prévision des repas dans les cantines"),
    
    # Show a plot of the generated distribution
    tabsetPanel(

## Result visualization ----------------------------------------------------
        tabPanel("Consulter des prévisions",
                 sidebarLayout(
                     sidebarPanel(selectInput("etab", "Choisir un établissement",
                                              choices = c("foo", "bar"))),
                     mainPanel(
                         DT::dataTableOutput("out")
                     )
                     )
                 ),

## Data visualization ------------------------------------------------------
        tabPanel("Charger des données"),

## Model parameters --------------------------------------------------------
        tabPanel("Générer des prévisions",
                 selectInput("column_to_predict", "Variable que l'on cherche à prédire :",
                             c("Fréquentation réelle" = "reel", 
                               "Commandes par les écoles" = "prevision")),
                 dateRangeInput("daterange_forecast", "Période à prévoir :",
                                start  = "2017-09-30",
                                end    = "2017-12-15",
                                min    = "2012-01-01",
                                max    = "2021-12-31",
                                format = "dd/mm/yyyy",
                                separator = " - ",
                                language = "fr",
                                weekstart = 1),
                 dateInput("start_training_date", "Date de début d'apprentissage :",
                          value =  "2012-09-01",
                          min    = "2012-01-01",
                          max    = "2021-12-31",
                          format = "dd/mm/yyyy",
                          language = "fr",
                          weekstart = 1),
                 sliderInput("confidence", "Niveau de confiance :",
                             min = 0, max = 1, value = 0.9, step = 0.01),
                 sliderInput("week_latency", "Dernières semaines à exclure pour l'apprentissage :",
                             min = 0, max = 20, value = 10, step = 1, round = TRUE),
                 selectInput("training_type", "Algorithme de prédiction :",
                             c("XGBoost simple" = "xgb", 
                               "XGBoost avec intervalle de confiance" = "xgb_interval")),
                 checkboxGroupInput("model_options", "Autres options",
                                    c("Réexécuter la préparation des données" = "preprocesing", 
                                      "Ne pas prédire les jours sans école" = "remove_no_school", 
                                      "Omettre les valeurs extrèmes (3 sigma)" = "remove_outliers"),
                                      selected = c("preprocesing", "remove_no_school", "remove_outliers")),
                 actionButton("launch_model", "Lancer la prédiction")),



# preprocessing=TRUE,
# remove_no_school=TRUE,
# remove_outliers=TRUE,


# Server ------------------------------------------------------------------

##  Server parameters --------------------------------------------------------
        tabPanel("Informations", 
                 h3('Current architecture info'),
                 '(These values will change when app is run locally vs on Shinyapps.io)',
                 hr(),
                 DT::dataTableOutput('sysinfo'),
                 br(),
                 verbatimTextOutput('which_python'),
                 verbatimTextOutput('python_version'),
                 verbatimTextOutput('ret_env_var'),
                 verbatimTextOutput('venv_root')
        )
        
        
    )
)

# Define server logic required to draw a histogram
server <- function(input, output) {

    

# Display data ------------------------------------------------------------
    prev <- load_results()
    dt <- load_data()
    
    output$out <- renderDataTable({
        DT::datatable(prev) 
        })

## Launch model ------------------------------------------------------------
    observeEvent(input$launch_model, {
        run_verteego(
            begin_date = as.character(input$daterange_forecast[1]),
            column_to_predict =  input$column_to_predict,
            confidence = input$confidence,
            end_date = as.character(input$daterange_forecast[2]),
            preprocessing = "preprocessing" %in% input$model_options,
            remove_no_school = "remove_no_school" %in% input$model_options,
            remove_outliers = "remove_outliers" %in% input$model_options,
            start_training_date = as.character(input$start_training_date),
            training_type = input$training_type,
            weeks_latency = input$week_latency
        )
    })
    

## System info -------------------------------------------------------------
    
    output$sysinfo <- DT::renderDataTable({
        s = Sys.info()
        df = data.frame(Info_Field = names(s),
                        Current_System_Setting = as.character(s))
        return(DT::datatable(df, rownames = F, selection = 'none',
                         style = 'bootstrap', filter = 'none', options = list(dom = 't')))
    })
    # Display system path to python
    output$which_python <- renderText({
        paste0("Emplacement de Python : ", Sys.which('python'))
    })
    # Display Python version
    output$python_version <- renderText({
        rr = reticulate::py_discover_config(use_environment = 'python35_env')
        paste0("Version de Python : ", rr$version)
    })
    # Display RETICULATE_PYTHON
    output$ret_env_var <- renderText({
        paste0('RETICULATE_PYTHON: ', Sys.getenv('RETICULATE_PYTHON'))
    })
    # Display virtualenv root
    output$venv_root <- renderText({
        paste0("Emplacement de l\'environnement virtuel :", reticulate::virtualenv_root())
    })
}

# Run the application 
shinyApp(ui = ui, server = server)
