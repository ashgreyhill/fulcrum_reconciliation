import requests
from .fulcrum_variables import FulcrumVariables
import json
import os
import pandas as pd
import datetime
import exceptions as exc


class AutoReconciler(object):
    """
    Wraps methods for removing bad data points from the Fulcrum completes list

    :attr list_surveys_url: (str) address for the api endpoint that returns a list of survey objects with a status
    :attribute reconcile_survey_url: (str) api endpoint that updates the completes associated with a survey
    :good_ids_list: (list) List of respondent IDs (RIDS) that are supposed to remain in the final sample
    """

    production_url = "https://api.samplicio.us/ "
    sandbox_url = "https://sandbox.techops.engineering/"

    base_url = None
    list_surveys_url = "{}Demand/v1/Surveys/BySurveyStatus".format(base_url)
    reconcile_survey_url = "{}Demand/v1/Surveys/Reconcile".format(base_url)
    good_ids_list = None
    data_check_path = "S:/Python/Data Check"
    completed_surveys = None

    def __init__(self, api_key: str, app_type: str):
        """

        :param api_key:
        """
        self.api_key = api_key

        if app_type.lower() == "production":
            self.base_url = self.production_url
        elif app_type.lower() == 'sandbox':
            self.sandbox_url = self.sandbox_url
        else:
            raise exc.InvalidAppTypeError(app_type)

    def list_completed_surveys(self):
        """
        Queries Fulcrum API for the list of completed surveys

        :return:
        """

        request_header = {FulcrumVariables.authorization: self.api_key}
        response = requests.get("{}/{}".format(self.list_surveys_url, FulcrumVariables.completed_survey_code),
                                headers=request_header)
        response_data = response.json()
        all_surveys = response_data.get(FulcrumVariables.survey_list_name)
        self.completed_surveys = [survey for survey in all_surveys if survey.get(
            'SurveyStatusCode') == FulcrumVariables.completed_survey_code]
        if len(self.completed_surveys) == 0:
            raise exc.NoCompleteSurveysError

    def reconcile_survey(self, survey_number):
        """
        Sends json with list of good ids for a survey to the reconciliation endpoint at the Fulcrum API

        :param survey_number: unique ID of the survey to be reconciled
        :return:
        """

        # Check that the ids list has been set
        if self.good_ids_list is None:
            raise exc.NoGoodIDsError

        # Create data from ids
        request_params = {FulcrumVariables.response_ids: self.good_ids_list}
        request_data = json.dumps(request_params)

        # Create headers
        request_headers = {
            'Content-type': 'application/json',
            FulcrumVariables.authorization: self.api_key,
            'Accept': 'text/plain'
        }

        # create request url
        request_url = "{}/{}".format(self.reconcile_survey_url, survey_number)

        # send reconciliation POST
        response = requests.post(request_url, data=request_data, headers=request_headers)

        # Raise an exception if the response status code is not valid
        if response.status_code not in FulcrumVariables.reconciliation_response_code:
            raise exc.ReconciliationResponseError(response.status_code)

    def configure_good_ids_list(self):

        date_list = os.listdir(self.data_check_path)
        today = datetime.datetime.today()
        date_str = "{}-{}".format(today.year, str(today.month).zfill(2))
        date_series = pd.Series(date_list)
        this_month_series = date_series[date_series.str.contains(date_str)]
        ids = []
        for i in this_month_series.tolist():
            try:
                data_check = pd.read_excel("{}/{}".format(self.data_check_path, i))
                good_data = data_check[data_check.loc[:, 'BadData'] != 1]
                fulcrum_data = good_data[good_data.loc[:, 'VENDOR'] == 'FU']
                ids += (fulcrum_data.loc[:, 'ID'].tolist())
            except PermissionError:
                print("{} open somewhere".format(i))

        return ids

    def reconcile_completed_surveys(self):
        for survey in self.completed_surveys:
            self.reconcile_survey(survey.get('survey_number'))