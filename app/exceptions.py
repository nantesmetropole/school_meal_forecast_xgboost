#!/usr/bin/python3
# -----------------------------------------------------------
# Define project related exceptions
# -----------------------------------------------------------

class OverlappingColumns(Exception):
    """
    Exception for overlapping columns of two dataframes
    """
    def __init__(self, common_columns):
        message = f"Columns of dataframes to cross join overlap: {str(common_columns)}"
        super().__init__(message)


class InconsistentDates(Exception):
    """
    Exception for dates incoherency
    """
    def __init__(self, error_details):
        message = f"Dates are inconsistent: {str(error_details)}"
        super().__init__(message)


class EmptyTrainingSet(Exception):
    """
    Exception empty training set
    """
    def __init__(self, error_details):
        message = f"Training set is empty, \
                    please check your training dates regarding to your data files {str(error_details)}"
        super().__init__(message)


class MissingDataForPrediction(Exception):
    """
    Exception for missing data when trying to build up features for prediction
    """
    def __init__(self, error_details):
        msg = f"Prediction set is empty, \
                please check your prediction dates regarding to your data files {str(error_details)}"
        super().__init__(msg)
