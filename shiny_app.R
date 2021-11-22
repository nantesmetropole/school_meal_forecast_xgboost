# Set parameters -------------------------------------------------------------

## Environment parameters
# Appropriate .Rprofile needs to be included in the project folder
# reticulate::virtualenv_remove("venv_shiny_app")
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
library(magrittr)
library(lubridate)
library(shinyalert)
library(waiter)
# library(dplyr)
# library(tidyr)

# A function to install required packages
install_load <- function(mypkg, to_load = FALSE) {
    for (i in seq_along(mypkg)) {
        if (!is.element(mypkg[i], installed.packages()[,1])) {
            install.packages(mypkg[i], repos="http://cran.irsn.fr/")
        }
        if (to_load) { library(mypkg[i], character.only=TRUE)  }
    }
}
pkgs_to_load <- "shiny"
pkgs_not_load <- c("shiny","reticulate", "purrr", "DT", "readr", "arrow", 
                   "data.table", "stringr", "lubridate", "plotly", "forcats",
                   "shinyalert", "dplyr", "tidyr", "shinyjs", "shinyhttr",
                   "waiter", "odbc", "DBI")


# Parameters --------------------------------------------------------------
data_path <- "tests/data"
index <- dplyr::tribble(
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
    dplyr::mutate(path = paste(data_path, path, sep = "/"))

# Begin and end year for selecting school years when loading headcounts

schoolyear_hq_start <- 2010

schoolyear_hq_end <- 2025


# A function to build open data urls from portal and dataset id
portal = "data.nantesmetropole.fr"

od_url <- function(portal, dataset_id, 
                   params = "/exports/csv") {
  left <- paste0("https://", portal, "/api/v2/catalog/datasets/")
  paste(left, dataset_id, params, sep = "")
}

# Creating a temp folder if needed to handle downloads
if(!(dir.exists("temp"))) {
  dir.create("temp")
}


freq_id = "244400404_nombre-convives-jour-cantine-nantes-2011"
freq_od <- od_url(portal = portal, dataset_id = freq_id)
freq_od_temp_loc <- "temp/freq_od.csv"

menus_id <- "244400404_menus-cantines-nantes-2011-2019"
menus_od <- od_url(portal = portal, dataset_id = menus_id)
menus_od_temp_loc <- "temp/menus_od.csv"


hc_id <- "244400404_effectifs-eleves-ecoles-publiques-maternelles-elementaires-nantes"
hc_od <- od_url(portal = portal, dataset_id = hc_id)
hc_od_temp_loc <- "temp/headcounts_od.csv"

vacs_od <- paste0("https://data.education.gouv.fr/explore/dataset/",
                  "fr-en-calendrier-scolaire/download/?format=csv")
vacs_od_temp_loc <- "temp/vacs_od.csv"

# install_load(pkgs_to_load, to_load = TRUE)
install_load(pkgs_not_load)

# Python functions and R bindings ---------------------------------------------------
reticulate::source_python("main.py")
prepare_arborescence()

# Cette fonction exécute la fonction 'run' avec les paramètres par défaut du readme
run_verteego <- function(begin_date = '2017-09-30',
                         column_to_predict = 'reel', 
                         data_path = "tests/data",
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
    args <- reticulate::PyClass(classname = "arguments", 
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
    run(args)
}

# R functions -------------------------------------------------------------

# A function to load the outputs of the model forecasts
load_results <- function(folder = "output", pattern = "results_by_cafeteria.*csv") {
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

# A function to generate inter-vacation periods from the vacation calendar
gen_piv <- function(vacations) {
    vacations %>%
        dplyr::filter(vacances_nom != "Pont de l'Ascension") %>%
        unique() %>%
        dplyr::arrange(date_debut) %>%
        dplyr::mutate(piv_nom2 = stringr::str_remove(vacances_nom, 
                                                     "Vacances (d'|de la |de )"),
                      piv_nom1 = dplyr::lag(piv_nom2, 1),
                      periode = paste(piv_nom1, piv_nom2, sep = "-"),
                      `Début` = dplyr::lag(date_fin, 1),
                      Fin = date_debut) %>%
        dplyr::filter(!is.na(piv_nom1)) %>%
        dplyr::select(annee = annee_scolaire,periode, `Début`, `Fin`) %>%
        dplyr::mutate(periode = factor(periode, c(
            "Ete-Toussaint", "Toussaint-Noel", "Noel-Hiver", "Hiver-Avril",
            "Avril-Ete"
        )))
}

# A function to inventory the available data 
compute_availability <- function(x) {
    avail_strikes <- x$strikes %>%
        dplyr::mutate("avail_data" = "Grèves") %>%
        dplyr::select(date, avail_data, n= greve)
    
    # Compute the number of values of staff previsions and kid attendance
    avail_freqs <- x$freqs %>%
        dplyr::select(date, prevision, reel) %>%
        tidyr::pivot_longer(cols = -date, names_to = "avail_data") %>%
        dplyr::mutate(avail_data = dplyr::recode(avail_data,
                                                 prevision = "Commandes",
                                                 reel = "Fréquentation")) %>%
        dplyr::group_by(date, avail_data) %>%
        dplyr::summarise(n = dplyr::n())
    
    # Compute the number of menu items registered per day 
    avail_menus <- x$menus %>%
        dplyr::mutate("avail_data" = "Menus",
                      date = lubridate::dmy(date)) %>%
        dplyr::group_by(date, avail_data) %>%
        dplyr::summarise(n = dplyr::n())
    
    # Vacances  
    vacs <- x$vacs
    
    vacs_dates <- purrr:::map2(vacs$date_debut, vacs$date_fin, 
                               ~ seq(.x, .y, by = "1 day")) %>%
        purrr::reduce(c)
    
    avail_vacs <-tidyr::tibble(
        date = vacs_dates,
        avail_data = "Vacances",
        n = 1)
    
    avail_holidays <- x$holidays %>%
        dplyr::mutate(avail_data = "Fériés") %>%
        dplyr::select(date, avail_data, n = jour_ferie)
    
    avail_data <- dplyr::bind_rows(avail_freqs, avail_menus, avail_strikes,
                                   avail_vacs) %>%
        dplyr::bind_rows(dplyr::filter(avail_holidays,
                                       date <= max(.$date),
                                       date >= (min(.$date)))) %>%
        dplyr::mutate(annee = lubridate::year(date),
                      an_scol_start = ifelse(lubridate::month(date) > 8, 
                                             lubridate::year(date), 
                                             lubridate::year(date)-1),
                      an_scol = paste(an_scol_start, an_scol_start+1, sep = "-"),
                      an_scol = forcats::fct_rev(an_scol),
                      `Jour` = lubridate::ymd(
                          paste(ifelse(lubridate::month(date) > 8, "1999", "2000"),
                                lubridate::month(date), lubridate::day(date), sep = "-"))) %>%
        dplyr::group_by(an_scol, avail_data) %>%
        dplyr::mutate(max_year_var = max(n, na.rm = TRUE),
                      nday_vs_nyearmax = n / max_year_var) %>%
        dplyr::mutate(avail_data = factor(avail_data,
                                          levels = c("Vacances", "Fériés", "Grèves", "Menus", "Commandes", "Fréquentation")))
    return(avail_data)
}

# A function to transform data from Fusion for training data
transform_fusion <- function(x, check_against) {
  x %>%
    dplyr::rename(date = DATPLGPRESAT, site_nom = NOMSAT, repas = LIBPRE, convive = LIBCON,
                  reel = TOTEFFREE, prev = TOTEFFPREV) %>%
    dplyr::filter(repas == "DEJEUNER") %>%
    dplyr::filter(stringr::str_starts(site_nom, "CL", negate = TRUE)) %>%
    dplyr::filter(stringr::str_detect(site_nom, "TOURNEE", negate = TRUE)) %>%
    dplyr::select(-repas) %>%
    dplyr::mutate(convive = dplyr::recode(convive, 
                                          "1MATER." = "maternelle",
                                          "2GS." = "grande_section",
                                          "3PRIMAIRE" = "primaire",
                                          "4ADULTE" = "adulte"),
                  site_id = stringr::str_remove(site_nom, "[0-9]{3}"),
                  site_nom = stringr::str_remove(site_nom, "[0-9]{3} "),
                  site_nom = stringr::str_replace(site_nom, "COUDRAY MAT", "COUDRAY M\\."),
                  site_nom = stringr::str_replace(site_nom, "MAT", "M"),
                  site_nom = stringr::str_replace(site_nom, "COUDRAY ELEM", "COUDRAY E\\."),
                  site_nom = stringr::str_replace(site_nom, "ELEM", "E"),
                  site_nom = stringr::str_remove(site_nom, " M/E"),
                  site_nom = stringr::str_remove(site_nom, " PRIM"),
                  site_nom = stringr::str_remove(site_nom, "\\(.*\\)$"),
                  site_nom = stringr::str_trim(site_nom),
                  site_nom = stringr::str_replace(site_nom, "BAUT", "LE BAUT"),
                  site_nom = stringr::str_replace(site_nom, "  ", " "),
                  site_nom = stringr::str_replace(site_nom, "FOURNIER", "FOURNIER E"),
                  site_nom = stringr::str_replace(site_nom, " E / ", "/"),
                  site_nom = stringr::str_replace(site_nom, "MACE$", "MACE M"),
                  site_nom = ifelse(!(site_nom %in% check_against) & stringr::str_ends(site_nom, " (E|M)"),
                                    stringr::str_remove(site_nom, " (E|M)$"), site_nom),
                  site_nom = stringr::str_replace(site_nom, "A.LEDRU-ROLLIN/S.BERNHARDT", 
                                                  "LEDRU ROLLIN/SARAH BERNHARDT"),
                  site_nom = stringr::str_replace(site_nom, "F.DALLET/DOCT TEILLAIS", 
                                                  "FRANCOIS DALLET/DOCTEUR TEILLAIS")) %>%
    dplyr::group_by(date, site_id, site_nom, convive) %>%
    dplyr::summarise(reel = sum(reel, na.rm = TRUE),
                     prev = sum(prev, na.rm = TRUE)) %>%
    tidyr::pivot_wider(names_from = convive, values_from = c(reel, prev),
                       values_fill = 0) %>%
    dplyr::mutate(reel = reel_maternelle + reel_grande_section + reel_primaire + reel_adulte,
                  prevision = prev_maternelle + prev_grande_section + prev_primaire + prev_adulte)
}

load_fusion <- function(x, freqs) {
    new_days <- x %>%
        dplyr::anti_join(freqs, by = c("date", "site_nom"))
    
    alert_exist <- ""
    if (!("reel_adulte" %in% colnames(freqs))) {
        exist_days <- x %>%
            dplyr::select(-reel, -prevision) %>%
            dplyr::inner_join(dplyr::select(freqs, -reel, -prevision, -site_type), 
                              by = c("date", "site_nom"))
        alert_exist <- paste("Complément des fréquentation par type de convive pour",
                             nrow(exist_days), 
                             "effectifs de repas par établissement pour",
                             length(unique(exist_days$date)), 
                             "jours de service.\n")
        freqs <- freqs %>%
            dplyr::left_join(exist_days, by = c("date", "site_nom"))
    }
    freqs <- dplyr::bind_rows(freqs, new_days) %>%
        readr::write_csv(index$path[index$name == "freqs"])
    alert_new <- paste("Ajout des fréquentation par type de convive pour",
                       nrow(new_days), 
                       "effectifs de repas par établissement pour",
                       length(unique(new_days$date)), 
                       "jours de service.")
    
    shinyalert(title = "Import depuis le fichier issu de Fusion réussi !",
               text = paste0(alert_exist, alert_new),
               type = "success")
}

# A function to generate a vector of school years
schoolyears <- function(year_start, year_end) {
  if(!(year_start > 2000 & year_end < 2050 & year_start < year_end)) {
    print("Specified year must be integers between 2000 and 2050 and start must be before end.")
  } else {
    left_side <- year_start:year_end
    right_side <- left_side + 1
    schoolyears <- paste(left_side, right_side, sep = "-")
    return (schoolyears)
  }
}

hc_years <- schoolyears(schoolyear_hq_start, schoolyear_hq_end)

# A function to enrich cafet list after frequentation import
update_mapping_cafet_freq <- function(x, 
                                      map_freq_loc = "tests/data/mappings/mapping_frequentation_cantines.csv") {
  map_freq <-  readr::read_csv(map_freq_loc)
  
  new_site_names <- x %>%
    dplyr::select(site_nom) %>%
    unique() %>%
    dplyr::filter(!(site_nom %in% map_freq$site_nom)) %>%
    dplyr::left_join(dplyr::select(x, site_nom, site_type), by = "site_nom") %>%
    unique() %>%
    dplyr::mutate(site_type = ifelse(is.na(site_type), "M/E", site_type),
                  cantine_nom = site_nom,
                  cantine_type = site_type)
  
  if (nrow(new_site_names) > 0) {
    map_freq <- map_freq %>%
      dplyr::bind_rows(new_site_names)
    readr::write_csv(map_freq, map_freq_loc)
  }
  
}

# UI ----------------------------------------------------------------------
ui <- navbarPage("Prévoir commandes et fréquentation",
                 ## Result visualization ----------------------------------------------------
                 tabPanel("Consulter des prévisions",
                          # Hide temporary error messages
                          tags$style(type="text/css",
                                     ".shiny-output-error { visibility: hidden; }",
                                     ".shiny-output-error:before { visibility: hidden; }"
                          ),
                          fluidRow(
                              column(1, actionButton("avant", 
                                                     "<< Avant",
                                                     style = "margin-top:25px; background-color: #E8E8E8")),
                              column(2, uiOutput("select_period")),
                              column(2, uiOutput("select_year")),
                              column(1, actionButton("apres", 
                                                     "Après >>",
                                                     style = "margin-top:25px; background-color: #E8E8E8")),
                              column(3, uiOutput("select_cafet"))),
                          fluidRow(plotly::plotlyOutput("plot")),
                          fluidRow(
                              column(3, downloadButton("dwn_filtered", 
                                                       "Télécharger les données affichées")))#☺,
                          # column(3, downloadButton("dwn_filtered", 
                          #                          "Télécharger toutes les données")))
                 ),
                 
                 ## Import new data ------------------------------------------------------
                 tabPanel("Charger des données",
                          autoWaiter(id = "available_data",
                                     html = tagList(
                                         spin_flower(),
                                         h4("Inventaire en cours, patientez 20 secondes environ...")
                                     )),
                          shinyalert::useShinyalert(),
                          sidebarLayout(
                              sidebarPanel(
                                  shinyjs::inlineCSS(list(
                                      ".shiny-input-container" = "margin-bottom: -20px",
                                      ".btn" = "margin-bottom: 5px"
                                  )),
                                  # sources for icons: https://icons.getbootstrap.com/
                                  h4("Importer de nouvelles données"),
                                  p(strong("Commandes et fréquentation réelle"),
                                    tags$button(id = "help_freqs",
                                                type = "button",
                                                class="action-button",
                                                HTML("?"))),
                                  #icon("question-circle")),
                                  actionButton("add_effs_real_od", "Open data",
                                               icon = icon("cloud-download")),
                                  actionButton("add_effs_real_sal", "Application Fusion",
                                               icon = icon("hdd")),
                                  fileInput("add_effs_real", 
                                            label = NULL,
                                            buttonLabel = "Parcourir",
                                            placeholder = "Fichier extrait de Fusion",
                                            width = "271px"),
                                  p(strong("Menus pour la restauration scolaire"),
                                    tags$button(id = "help_menus",
                                                type = "button",
                                                class="action-button",
                                                HTML("?"))),
                                  actionButton("add_menus_od", "Open data",
                                               icon = icon("cloud-download")),
                                  actionButton("add_menus_sal", "Application Fusion",
                                               icon = icon("hdd")),
                                  fileInput("add_menus", label = NULL,
                                            buttonLabel = "Parcourir",
                                            placeholder = "Fichier extrait de Fusion",
                                            width = "271px"),
                                  p(strong("Grèves (éducation ou restauration)"),
                                    tags$button(id = "help_strikes",
                                                type = "button",
                                                class="action-button",
                                                HTML("?"))),
                                  fileInput("add_strikes", label = NULL,
                                            buttonLabel = "Parcourir",
                                            placeholder = "Fichier de suivi",
                                            width = "271px"),
                                  p(strong("Effectifs des écoles"),
                                    tags$button(id = "help_effs",
                                                type = "button",
                                                class="action-button",
                                                HTML("?"))),
                                  actionButton("add_hc_od", "Open data",
                                               icon = icon("cloud-download")),
                                  fileInput("add_headcounts", label = NULL,
                                            buttonLabel = "Parcourir",
                                            placeholder = "Fichier sur le PC",
                                            accept = c(".xls", ".xlsx"),
                                            width = "271px"),
                                  selectInput("schoolyear_hc", NULL,
                                              choices = c("Préciser l'année",
                                                hc_years),
                                              width = "271px"),
                                  p(strong("Vacances scolaires pour la zone B"),
                                    tags$button(id = "help_holi",
                                                type = "button",
                                                class="action-button",
                                                HTML("?"))),
                                  actionButton("add_vacs_od", "Open data",
                                               icon = icon("cloud-download")),
                                  width = 3),
                              mainPanel(actionButton("process_inventory", 
                                                     "Inventorier les données disponibles"),
                                        plotOutput("available_data"))
                          )
                 ),
                 
                 ## Model parameters --------------------------------------------------------
                 tabPanel("Générer des prévisions",
                          fluidRow(
                              column(4,
                                     selectInput("column_to_predict", "Variable que l'on cherche à prédire :",
                                                 c("Fréquentation réelle" = "reel", 
                                                   "Commandes par les écoles" = "prevision")),
                                     br(),
                                     dateRangeInput("daterange_forecast", "Période à prévoir :",
                                                    start  = "2017-09-30",
                                                    end    = "2017-12-15",
                                                    min    = "2012-01-01",
                                                    max    = "2021-12-31",
                                                    format = "dd/mm/yyyy",
                                                    separator = " - ",
                                                    language = "fr",
                                                    weekstart = 1),
                                     br(), br(),
                                     dateInput("start_training_date", "Date de début d'apprentissage :",
                                               value =  "2012-09-01",
                                               min    = "2012-01-01",
                                               max    = "2021-12-31",
                                               format = "dd/mm/yyyy",
                                               language = "fr",
                                               weekstart = 1)),
                              column(4,
                                     sliderInput("confidence", "Niveau de confiance :",
                                                 min = 0, max = 1, value = 0.9, step = 0.01),
                                     br(), br(),
                                     sliderInput("week_latency", "Dernières semaines à exclure pour l'apprentissage :",
                                                 min = 0, max = 20, value = 10, step = 1, round = TRUE),
                                     br(), br(),
                                     selectInput("training_type", "Algorithme de prédiction :",
                                                 c("XGBoost simple" = "xgb", 
                                                   "XGBoost avec intervalle de confiance" = "xgb_interval"))),
                              column(4,
                                     checkboxGroupInput("model_options", "Autres options",
                                                        c("Réexécuter la préparation des données" = "preprocessing", 
                                                          "Ne pas prédire les jours sans école" = "remove_no_school", 
                                                          "Omettre les valeurs extrèmes (3 sigma)" = "remove_outliers"),
                                                        selected = c("preprocessing", "remove_no_school", "remove_outliers")),
                                     br(), br(),
                                     actionButton("launch_model", "Lancer la prédiction")))
                 ),
                 
                 
                 ##  UI display of server parameters --------------------------------------------------
                 tabPanel("Superviser", 
                          h3('Information système'),
                          "(Ces valeurs changent selon le poste ou serveur qui fait tourner l'application)",
                          hr(),
                          DT::dataTableOutput('sysinfo'),
                          br(),
                          verbatimTextOutput('which_python'),
                          verbatimTextOutput('python_version'),
                          verbatimTextOutput('ret_env_var'),
                          verbatimTextOutput('venv_root'))
)



# Server ------------------------------------------------------------------

# Define server logic required to draw a histogram
server <- function(session, input, output) {
    
    
    # Reactive values for result display -----------------------------------
    
    
    prev <- reactive({ load_results() }) # Previsions
    dt <- reactive({ load_data() }) # training data
    vacs <- reactive({ return(dt()$vacs) }) # vacations
    pivs <- reactive({ gen_piv(vacs()) }) # Period between vacations
    cafets <- reactive({ c("Tous", # List of cafeteria
                           levels(factor(prev()$cantine_nom))) })
    periods <- reactive({ levels(pivs()$periode) }) # Name of the periods
    years <- reactive({ # School years
        levels(forcats::fct_rev(pivs()$annee)) 
    })
    
    selected_cafet <- reactive({ input$select_cafet })
    selected_dates <- reactive({  
        pivs() %>%
            dplyr::filter(periode == input$select_period & 
                              annee == input$select_year) %>%
            dplyr::select(`Début`, `Fin`)
    })
    
    filtered_prev <- reactive({ # Filtering the prevision based on parameters
        date_start <- lubridate::ymd(selected_dates()[[1]])
        date_end <- lubridate::ymd(selected_dates()[[2]])
        filtered <- prev() %>%
            dplyr::mutate(date_str = lubridate::ymd(date_str)) %>%
            dplyr::filter(date_str >= date_start & date_str <= date_end)
        if (selected_cafet() != "Tous") {
            filtered <- filtered %>%
                dplyr::filter(site_nom == selected_cafet())
        }
        filtered <- filtered %>%
            dplyr::group_by(Date = lubridate::ymd(date_str)) %>%
            dplyr::summarise(Repas = sum(output, na.rm = TRUE))
        return(filtered)
    })
    
    
    filtered_dt <- reactive({
        # Filter parameters
        # selected_cafet <- "Tous"
        # selected_dates <- c("2019-01-01", "2019-04-15")
        date_start <- lubridate::ymd(selected_dates()[[1]])
        date_end <- lubridate::ymd(selected_dates()[[2]])
        cafet <- input$select_cafet
        # previsions for selected dates
        filtered_prevs <- prev() %>%
            dplyr::mutate(Date = lubridate::as_date(date_str)) %>%
            dplyr::rename(site_nom = cantine_nom) %>%
            dplyr::filter(Date >= date_start & Date <= date_end)
        # attendance for selected dates
        filtered_freqs <- dt()$freqs %>%
            dplyr::mutate(Date = lubridate::as_date(date)) %>%
            dplyr::filter(Date >= date_start & Date <= date_end)
        # consolidating
        join_filtered <- filtered_freqs %>%
            dplyr::full_join(filtered_prevs, by = c("Date", "site_nom"))
        # Filtering on cafeteria
        if (cafet != "Tous") {
            join_filtered <- join_filtered %>%
                dplyr::filter(site_nom == cafet)
        }
        
        filtered <- join_filtered  %>%
            dplyr::group_by(Date) %>%
            dplyr::summarise(`prevision_modele` = sum(output, na.rm = TRUE),
                             `prevision_agents` = sum(prevision, na.rm = TRUE),
                             `reel` = sum(reel, na.rm = TRUE)) %>%
            dplyr::ungroup() %>% # needed to filter at follwing line
            dplyr::filter(if_any(where(is.numeric), ~ .x > 0)) %>% # only keep days with lunches
            tidyr::pivot_longer(-Date, values_to = "Repas", names_to = "Source") %>%
            dplyr::mutate(Type = ifelse(Source == "reel", "reel", "prevision"))
        return(filtered)
    })
    
    last_prev <- reactive ({
        max(ymd(prev()$date_str))
    })
    
    piv_last_prev <- reactive({
        pivs() %>%
            dplyr::filter(last_prev() %within% lubridate::interval(`Début`, Fin))
    })
    
    # Navigation - bouton "Après" ---------------------------------------------
    
    observeEvent(input$apres, {
        period_rank <- which(periods() == input$select_period)
        if (period_rank == 5) {
            year_rank <- which(years() == input$select_year)
            if (year_rank == 1) {
                shinyalert::shinyalert("Attention",
                                       paste("Les données ne sont pas préparées
                                       pour des dates après l'année scolaire", 
                                             input$select_year, "."), 
                                       type = "error", html = TRUE)
            } else {
                new_year <- years()[year_rank - 1]
                updateSelectInput(inputId = "select_period",
                                  choices = periods(),
                                  selected = "Ete-Toussaint")
                updateSelectInput(inputId = "select_year",
                                  choices = years(),
                                  selected = new_year)
            }
        } else {
            new_period <- periods()[period_rank + 1]
            updateSelectInput(inputId = "select_period",
                              choices = periods(),
                              selected = new_period)
        }
    })
    
    # Navigation - bouton "Avant" ---------------------------------------------
    
    observeEvent(input$avant, {
        period_rank <- which(periods() == input$select_period)
        if (period_rank == 1) {
            year_rank <- which(years() == input$select_year)
            if (year_rank == length(years())) {
                shinyalert::shinyalert("Attention",
                                       paste("Les données ne sont pas préparées
                                       pour des dates avant l'année scolaire", 
                                             input$select_year, "."), 
                                       type = "error", html = TRUE)
            } else {
                new_year <- years()[year_rank + 1]
                updateSelectInput(inputId = "select_period",
                                  choices = periods(),
                                  selected = "Avril-Ete")
                updateSelectInput(inputId = "select_year",
                                  choices = years(),
                                  selected = new_year)
            }
        } else {
            new_period <- periods()[period_rank - 1]
            updateSelectInput(inputId = "select_period",
                              choices = periods(),
                              selected = new_period)
        }
    })
    output$select_period <- renderUI({
        selectInput("select_period", "Période inter-vacances",
                    choices = periods(),
                    selected = piv_last_prev()$periode)
    })
    output$select_year <- renderUI({
        selectInput("select_year", "Année scolaire",
                    choices = years(),
                    selected = piv_last_prev()$annee
        )
    })
    output$select_cafet <- renderUI({
        selectInput("select_cafet", "Filtrer un restaurant scolaire",
                    choices = cafets())
    })
    
    output$filters <- DT::renderDataTable({
        DT::datatable(filtered_prev())
    })
    
    output$dwn_filtered <- downloadHandler(
        filename = function() {
            paste("previsions_", 
                  input$select_period, "_", 
                  input$select_year, "_",
                  input$select_cafet, ".csv", sep="")
        },
        content = function(file) {
            write.csv(filtered_prev(), file)
        }
    )
    
    ## Consult results -----------------------------------------------------
    
    
    output$plot <- plotly::renderPlotly({
        dt2 <- filtered_dt()
        static <- dt2 %>%
            ggplot2::ggplot(ggplot2::aes(x = Date, y = Repas, color = Source, fill = Source)) +
            ggplot2::geom_line(data = subset(dt2, stringr::str_starts(Source, "prevision"))) +
            ggplot2::geom_bar(data = subset(dt2, stringr::str_starts(Source, "reel")),
                              ggplot2::aes(x = Date, y = Repas), stat = "identity") +
            ggplot2::theme(axis.title.x=ggplot2::element_blank()) 
        
        plotly::ggplotly(static) %>%
            plotly::config(displayModeBar = FALSE) %>%
            plotly::layout(legend = list(orientation = "h", x = 0, y = 1.1))
        
    })
    
    
    ## Visualize existing data for each day-----------------------------------------
    
    
    ### Compute and format days where strike events ----------------------------
    avail_strikes <- reactive({ 
        dt()$strikes %>%
            dplyr::mutate("avail_data" = "Grèves") %>%
            dplyr::select(date, avail_data, n= greve)
    })
    
    ### Compute the number of values of staff previsions and kid attendance --- 
    avail_freqs <- reactive ({
        dt()$freqs %>%
            dplyr::select(date, prevision, reel) %>%
            tidyr::pivot_longer(cols = -date, names_to = "avail_data") %>%
            dplyr::mutate(avail_data = dplyr::recode(avail_data,
                                                     prevision = "Commandes",
                                                     reel = "Fréquentation")) %>%
            dplyr::group_by(date, avail_data) %>%
            dplyr::summarise(n = dplyr::n()) 
    })
    
    ### Compute the number of menu items registered per day -------------------
    avail_menus <- reactive ({
        dt()$menus %>%
            dplyr::mutate("avail_data" = "Menus",
                          date = lubridate::dmy(date)) %>%
            dplyr::group_by(date, avail_data) %>%
            dplyr::summarise(n = dplyr::n())
    })
    
    
    avail_vacs <- reactive ({
        vacs <- dt()$vacs
        purrr:::map2(vacs$date_debut, vacs$date_fin, 
                     ~ seq(.x, .y, by = "1 day")) %>%
            purrr::reduce(c) -> vacs_dates
        tidyr::tibble(
            date = vacs_dates,
            avail_data = "Vacances",
            n = 1
        )
    })
    
    avail_holidays <-reactive ({
        dt()$holidays %>%
            dplyr::mutate(avail_data = "Fériés") %>%
            dplyr::select(date, avail_data, n = jour_ferie)
    })
    
    ### Plot available data ---------------------------------------------------
    observeEvent(input$process_inventory, {
        output$available_data <- renderPlot({
            dt_act <- dt()
            compute_availability(x = dt_act) %>%
                ggplot2::ggplot(ggplot2::aes(x = `Jour`, y = avail_data)) +
                ggplot2::geom_tile(ggplot2::aes(fill = avail_data,
                                                alpha = nday_vs_nyearmax)) +
                ggplot2::scale_alpha(guide = "none") +
                ggplot2::scale_fill_discrete("") +
                ggplot2::facet_grid(forcats::fct_rev(an_scol) ~ ., # fct_rev to have recent first
                                    switch = "both") + 
                ggplot2::scale_x_date(labels = function(x) format(x, "%b"),
                                      date_breaks = "1 month", date_minor_breaks = "1 month",
                                      position = "top") +
                ggplot2::theme(axis.title.x = ggplot2::element_blank(),
                               axis.title.y = ggplot2::element_blank(),
                               axis.text.x = ggplot2::element_text(hjust = 0),
                               # axis.text.y = ggplot2::element_blank(),
                               legend.position = "none")+
                ggplot2::ggtitle("Données déjà chargées dans l'outil")
            
        }, height = 600)
    })
    
    ## Import new data ----------------------------------------------------------
    
    ### Help --------------------------------------------------------------
    observeEvent(input$help_freqs, {
        shinyalert::shinyalert("Import de données de fréquentation", 
                               "Ces données peuvent être importées de plusieurs manières :
                               - en allant récupérer les inormations les plus récentes sur l'open data
                               - en changeant les données brutes extraites d'un sauvegarde de la base de données de Fusion
                               - en se connectation directement à l'outil Fusion", 
                               type = "info")
    }) 
    observeEvent(input$help_menus, {
        shinyalert::shinyalert("Import de données de menus", 
                               "Ces données peuvent être importées de plusieurs manières :
                               - en allant récupérer les inormations les plus récentes sur l'open data
                               - en changeant les données brutes extraites d'un sauvegarde de la base de données de Fusion
                               - en se connectation directement à l'outil Fusion", 
                               type = "info")
    })
    observeEvent(input$help_strikes, {
        shinyalert::shinyalert("Import de données de grèves", 
                               paste("Ces données doivent reconstruites à partir des fichiers de suivi des grêves",
                                     "de la direction de l'éducation. Il suffit de construire un tableau avec, dans",
                                     "une première colonne nommée 'date' la date des grêves de l'éducation ou de la", 
                                     "restauration ayant fait l'objet d'un préavis à Nantes Métropole, et une colonne", 
                                     "nommée 'greve' indiquant des 1 pour chaque date ayant connu une grève. Pour des",
                                     "exemples, Voir le fichier readme ou le fichier tests/data/calculators/greves.csv"), 
                               type = "info")
    })
    observeEvent(input$help_effs, {
        shinyalert::shinyalert("Import de données d'effectifs des écoles", 
                               paste("Ces données sont fournies par la direction de l'éducation et correspondent aux",
                                     "effectifs en octobre. Le format à suivre correspond à trois colonnes 'ecole',", 
                                     "'annee_scolaire' et 'effectif'. Il faut s'assurer que la table de correspondance", 
                                     "entre les noms d'écoles et les noms de restaurants scolaires associés soit à jour",
                                     "dans tests/data/mappings/mapping_ecoles_cantines.csv"), 
                               type = "info")
    }) 
    observeEvent(input$help_holi, {
        shinyalert::shinyalert("Import des données de vacances scolaires", 
                               paste("Ces données sont importées automatiquement à partir du portail open data de",
                                     "l'éducation nationale. Les dates correspondent à la zone B."), 
                               type = "info")
    }) 
    ### Import attendance OD -------------------------------------------------
    observeEvent(input$add_effs_real_od, {
        httr::GET(freq_od, # httr_progress(waitress_od),
                  httr::write_disk(freq_od_temp_loc, overwrite = TRUE))
        to_add <- arrow::read_delim_arrow(freq_od_temp_loc, delim = ";",
                                          col_select = c(
                                              site_id, site_type, date, 
                                              prevision_s = prevision, 
                                              reel_s = reel, site_nom
                                          )) %>%
            dplyr::anti_join(dt()$freqs)
        
        nrows_to_add <- nrow(to_add)
        ndays_to_add <- length(unique(to_add$date))
        to_add %>%
            dplyr::bind_rows(dt()$freqs) %>%
            readr::write_csv(index$path[index$name == "freqs"])
        
        update_mapping_cafet_freq(to_add)
        shinyalert(title = "Import réussi !",
                   text = paste("Ajout de",
                                nrows_to_add,
                                "effectifs de repas par établissements pour",
                                ndays_to_add,
                                "jours de service."),
                   type = "success")
        shinyalert(title = "Mise à jour du graphique impossible",
                   text = paste("Un problème technique empêche la mise à jour",
                                "du graphique indiquant la disponibilité des données.",
                                "Les nouvelles données ajoutées seront visibles après",
                                "le redémarrage de l'application"),
                   type = "warning")
        
    })
    ### Import attendance parquet ---------------------------------------------
    # Manually load datafile
    observeEvent(input$add_effs_real, {
        file_in <- input$add_effs_real
        dt_in <- arrow::read_parquet(file_in$datapath,
                                     col_select = c("DATPLGPRESAT", "NOMSAT", "LIBPRE",
                                                    "LIBCON","TOTEFFREE", "TOTEFFPREV")) %>%
            transform_fusion(check_against = dt()$map_freqs$cantine_nom) %>%
            load_fusion(freqs = dt()$freqs)
    })
    
    
    ### Import attendance Firebase ----------------------------------------------
    observeEvent(input$add_effs_real_sal, {
        drivers <- sort(unique(odbc::odbcListDrivers()[[1]]))
        if (sum(stringr::str_detect(drivers, "Firebird"), na.rm = TRUE) < 1) {
            shinyalert(title = "Besoin d'un accès spécial pour cette option",
                       text = paste("Cette méthode d'import requiert de",
                                    "disposer d'un poste disposant des droits",
                                    "en lecture et des drivers permettant de",
                                    "lire la base de donnée de l'application",
                                    "métier"),
                       type = "error")
        } else {
            # On charge le mot de passe de la base
            load("secret.Rdata")
            # On paramètre la connexion
            con <- DBI::dbConnect(odbc::odbc(), 
                                  .connection_string = paste0(
                                      "DRIVER=Firebird/InterBase(r) driver;
                 UID=SYSDBA; PWD=", secret, ";
                 DBNAME=C:\\Users\\FBEDECARRA\\Documents\\Fusion\\FUSION.FDB;"),
                                  timeout = 10)
            dt_in <- DBI::dbReadTable(con, "VIFC_EFFECTIFS_REEL_PREV_CNS") %>%
                dplyr::select(DATPLGPRESAT, NOMSAT, LIBPRE, LIBCON, 
                       TOTEFFREE, TOTEFFPREV) %>%
                transform_fusion(check_against = dt()$map_freqs$cantine_nom) %>%
                load_fusion(freqs = dt()$freqs)
            update_mapping_cafet_freq(dt_in)
        }
        
    })
    
    ### Import menus Firebase ----------------------------------------------
    observeEvent(input$add_menus_sal, {
      drivers <- sort(unique(odbc::odbcListDrivers()[[1]]))
      if (sum(stringr::str_detect(drivers, "Firebird"), na.rm = TRUE) < 1) {
        shinyalert(title = "Besoin d'un accès spécial pour cette option",
                   text = paste("Cette méthode d'import requiert de",
                                "disposer d'un poste disposant des droits",
                                "en lecture et des drivers permettant de",
                                "lire la base de donnée de l'application",
                                "métier"),
                   type = "error")
      } else {
        # On charge le mot de passe de la base
        load("secret.Rdata")
        # On paramètre la connexion
        con <- DBI::dbConnect(odbc::odbc(), 
                              .connection_string = paste0(
                                "DRIVER=Firebird/InterBase(r) driver;
                 UID=SYSDBA; PWD=", secret, ";
                 DBNAME=C:\\Users\\FBEDECARRA\\Documents\\Fusion\\FUSION.FDB;"),
                              timeout = 10)
        new_menus <- DBI::dbReadTable(con, "VIFC_MENU") %>%
          dplyr::filter(LIBPRE == "DEJEUNER" & LIBCATFIT != "PAIN") %>%
          dplyr::select(date = "DATPLGPRE", rang = "ORDRE_LIBCATFIT", 
                        plat = "LIBCLIFIT") %>%
          unique() %>%
          # arrange(date, rang) %>% # nicer to inspect the table this way
          dplyr::mutate(date = format(date, "%d/%m/%Y")) %>%
          dplyr::filter(!(date %in% dt()$menus$date)) 
        dplyr::bind_rows(dt()$menus, new_menus) %>%
          readr::write_csv(index$path[index$name == "menus"])
        shinyalert(title = "Import des menus depuis l'open data réussi !",
                   text = paste("Ajout des menus de convive pour",
                                nrow(new_menus), 
                                "plats pour",
                                length(unique(new_menus$date)), 
                                "jours de service."),
                   type = "success")
      }
      
    })
    
    ### Import menus OD -------------------------------------------------
    observeEvent(input$add_menus_od, {
      httr::GET(menus_od, # httr_progress(waitress_od),
                httr::write_disk(menus_od_temp_loc, overwrite = TRUE))
      new_menus <- arrow::read_delim_arrow(menus_od_temp_loc, delim = ";") %>%
        dplyr::mutate(date = format(date, "%d/%m/%Y")) %>%
        dplyr::filter(!(date %in% dt()$menus$date))
      menu_path <- as.character(index[index$name == "menus", "path"])
      menus <- readr::read_csv(menu_path)
      dplyr::bind_rows(menus, new_menus) %>%
        readr::write_csv(index$path[index$name == "menus"])
      shinyalert(title = "Import des menus depuis l'open data réussi !",
                 text = paste("Ajout des menus de convive pour",
                              nrow(new_menus), 
                              "plats pour",
                              length(unique(new_menus$date)), 
                              "jours de service."),
                 type = "success")
      
    })
    
    ### Import vacations from open data ----------------------------------------
    observeEvent(input$add_vacs_od, {
      httr::GET(vacs_od, # httr_progress(waitress_od),
                httr::write_disk(vacs_od_temp_loc, overwrite = TRUE))
      old_vacs <- dt()$vacs
      new_vacs <- readr::read_delim(vacs_od_temp_loc, delim = ";") %>%
        dplyr::filter(location == "Nantes" & population != "Enseignants")  %>%
        dplyr::select(annee_scolaire, vacances_nom = description,
                      date_debut = start_date, date_fin = end_date) %>%
        dplyr::mutate(zone = "B", vacances = 1, 
                      date_debut = as.Date(date_debut),
                      date_fin = as.Date(date_fin)) %>%
        # dplyr::anti_join(old_vacs)
        dplyr::filter(!(annee_scolaire %in% old_vacs$annee_scolaire))
      new_vacs %>%
        dplyr::bind_rows(old_vacs) %>%
        readr::write_csv(index$path[index$name == "vacs"])
      shinyalert(title = "Import des vacances depuis l'open data de l'éducation nationale réussi !",
                 text = paste("Ajout des vacances scolaires pour la Zone B, pour",
                              nrow(new_vacs), 
                              "périodes de vacances."),
                 type = "success")
      
    })
    
    ### Import headcounts  ---------------------------------------------
    
    # Manually load datafile
    observeEvent(input$add_headcounts, {
      file_in <- input$add_headcounts
      if (stringr::str_starts(input$schoolyear_hc, "[0-9]", negate = TRUE)) {
        shinyalert("Sélectionner une année", 
                   "Veuillez sélectionner l'année scolaire correspondante au fichier importé et relancer l'import.",
                   type = "error")
      } else {
        an_scol_import <- input$schoolyear_hc
        hc_new <- readxl::read_excel(file_in$datapath, 
                                     skip = 1) %>%
          dplyr::filter(!is.na(.[[colnames(.)[1]]])) %>%
          dplyr::select(ecole = Ecoles, effectif = starts_with("Total g")) %>%
          dplyr::mutate(annee_scolaire = an_scol_import)
        hc_all <- dt()$effs %>%
          dplyr::filter(!(paste(ecole, annee_scolaire) %in% paste(hc_new$ecole, hc_new$annee_scolaire))) %>%
          dplyr::bind_rows(hc_new) %>%
          readr::write_csv(index$path[index$name == "effs"])
        shinyalert(title = "Import manuel des effectifs réussi !",
                   text = paste("Ajout de ",
                                nrow(hc_new), 
                                "effectifs d'écoles."),
                   type = "success")
      }
    })
    
    ### Import headcounts OD -------------------------------------------------
    observeEvent(input$add_hc_od, {
      old_hc <- dt()$effs
      httr::GET(hc_od, # httr_progress(waitress_od),
                httr::write_disk(hc_od_temp_loc, overwrite = TRUE))
      new_hc <- arrow::read_delim_arrow(hc_od_temp_loc, delim = ";") %>%
        dplyr::select(ecole, annee_scolaire, effectif)
      old_hc <- dt()$effs %>%
        dplyr::filter(!(paste(ecole, annee_scolaire) %in% paste(new_hc$ecole, new_hc$annee_scolaire)))
      hc_path <- as.character(index[index$name == "effs", "path"])
      dplyr::bind_rows(old_hc, new_hc) %>%
        readr::write_csv(index$path[index$name == "effs"])
      shinyalert(title = "Import des effectifs depuis l'open data réussi !",
                 text = paste("Ajout de",
                              nrow(new_hc), 
                              "effectifs d'écoles."),
                 type = "success")
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
        dt$prev <- load_results()
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
