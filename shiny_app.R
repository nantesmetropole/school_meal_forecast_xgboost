# Set environment -------------------------------------------------------------
# .Rprofile needs to be included in the project
# test
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

# Old ---------------------------------------------------------------------
library(reticulate)
library(shiny)
library(DT)

source_python("main.py")

# Paramétrage d'une client R pour le modèle en python -------------------------

# Cette fonction exécute la fonction 'run' avec les paramètres par défaut du readme
run_verteego <- function(begin_date = '2017-09-30',
                         column_to_predict = 'reel', 
                         data_path = 'tests/data',
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

# run_verteego()

# Define UI for application that draws a histogram
ui <- fluidPage(

    # Application title
    titlePanel("Old Faithful Geyser Data"),

    # Sidebar with a slider input for number of bins 
    sidebarLayout(
        sidebarPanel(
            sliderInput("bins",
                        "Number of bins:",
                        min = 1,
                        max = 50,
                        value = 30)
        ),

        # Show a plot of the generated distribution
        mainPanel('Architecture Info', 
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

    output$distPlot <- renderPlot({
        # generate bins based on input$bins from ui.R
        x    <- faithful[, 2]
        bins <- seq(min(x), max(x), length.out = input$bins + 1)

        # draw the histogram with the specified number of bins
        hist(x, breaks = bins, col = 'darkgray', border = 'white')
    })
    # Display info about the system running the code
    output$sysinfo <- DT::renderDataTable({
        s = Sys.info()
        df = data.frame(Info_Field = names(s),
                        Current_System_Setting = as.character(s))
        return(datatable(df, rownames = F, selection = 'none',
                         style = 'bootstrap', filter = 'none', options = list(dom = 't')))
    })
    # Display system path to python
    output$which_python <- renderText({
        paste0('which python: ', Sys.which('python'))
    })
    # Display Python version
    output$python_version <- renderText({
        rr = reticulate::py_discover_config(use_environment = 'python35_env')
        paste0('Python version: ', rr$version)
    })
    # Display RETICULATE_PYTHON
    output$ret_env_var <- renderText({
        paste0('RETICULATE_PYTHON: ', Sys.getenv('RETICULATE_PYTHON'))
    })
    # Display virtualenv root
    output$venv_root <- renderText({
        paste0('virtualenv root: ', reticulate::virtualenv_root())
    })
}

# Run the application 
shinyApp(ui = ui, server = server)
