import numbers
from django.db import transaction

import pandas as pd
import numpy as np

from openfacstrack.apps.track.models import (
    PanelMetadata,
    Parameter,
    ProcessedSample,
    DataProcessing,
    ClinicalSample,
    ClinicalSampleMetadataDict,
    ClinicalSampleMetadata,
    Panel,
    NumericParameter,
    TextParameter,
)


class ClinicalSampleFile:
    """
    Uploads a file with results from clinical samples.
    """

    def __init__(self, filepath):
        """load contents of file into a data frame and set other attribs.

        Parameters
        ----------
        filepath : string
            path to file (csv) to read

        Returns
        -------
        None
        """
        self.filepath = filepath
        self.df = pd.read_csv(filepath, parse_dates=["Date"])

        # List of columns always expected
        # ToDo: Find out if any of these columns are 'required' - if so
        #       cannot continue without them.
        self.static_columns = [
            "batch",
            "X1",
            "Operator name",
            "Comments",
            "Date",
            "Panel",
            "Clinical_sample",
        ]

        # Compute names of parameters present. These are all the other
        # columns in the file that are not in the static_columns list
        parameter_columns = set(self.df.columns) - set(self.static_columns)
        self.parameter_columns = list(parameter_columns)

        # Store the unique panels in the data
        # ToDo: I think there should be only one unique panel - check.
        self.panels = self.df["Panel"].unique().tolist()

    def validate(self):
        """Validate file for completeness of reference data
        
        Parameters
        ----------
        None

        Returns
        -------
        validation_error : dict
            keys are types of errors, values are descriptions. Empty dict
            is returned if there are no errors
        """

        # Start validation writing errors into dictionary/or json string?
        validation_errors = {}

        # Check we have the expected number of columns.
        static_columns_missing = []
        for static_column in self.static_columns:
            if static_column not in self.df.columns:
                static_columns_missing.append(static_column)
        if len(static_columns_missing) > 0:
            validation_errors["static_columns_missing"] = static_columns_missing

        # Check that all the info is for the same panel
        if "Panel" in self.df.columns:
            panels_in_data = self.df["Panel"].unique().tolist()
            n_unique_panels_in_data = len(panels_in_data)
            if n_unique_panels_in_data != 1:
                validation_errors["unique_panel_error"] = (
                    f"Expected 1 unique value for panels in each record"
                    + f". Got {n_unique_panels_in_data}: {panels_in_data}"
                )

            # Check if the panel(s) are present in the Panel table
            panels_in_data_pk = []
            unknown_panels = []
            for panel in panels_in_data:
                try:
                    panels_in_data_pk.append(Panel.objects.get(name=panel.upper()).id)
                except Panel.DoesNotExist as e:
                    unknown_panels.append(panel)
            if len(unknown_panels) > 0:
                validation_errors["unknown_panel_error"] = (
                    "The following panels are not in Panel table: "
                    + f"{unknown_panels}"
                )

        else:
            # ToDo: Can we continue without unique panels?
            panels_in_data = []
            panels_in_data_pk = []

        # For other columns these should be present in the
        # parameter_metadata table. If they are not need to agree whether
        # to add dynamically or flag as errors
        unregistered_parameters = []

        for parameter_column in self.parameter_columns:
            try:
                parameter_object = Parameter.objects.get(
                    gating_hierarchy=parameter_column, panel__in=panels_in_data_pk
                )
            except Parameter.DoesNotExist:
                unregistered_parameters.append(parameter_column)

        if len(unregistered_parameters) > 0:
            validation_errors["unregistered_parameters"] = unregistered_parameters

        # Check all fields needed for processed_sample table present

        # Check all clinical samples present in clinical_sample table

        # Enter values into clinical_sample, processed_sample,
        # numeric_parameter and text_parameter

        # Print out list of validation errors
        # print("Validation errors:")
        # for key, value in validation_errors.items():
        #    print(f"{key}: {value}")

        return validation_errors

    def upload(self):
        """Upload file to respective tables

        Upload data in clinical sample results for panel into the database.
        We assume that all the results here are based on one panel (ToDo: 
        need to confirm whether to throw error during validation if more
        than one panel). The upload is carried out in an atomic transaction
        and if there are any errors nothing is written to the database.
        
        Workflow:
            1 - covid patient IDs loaded into ClinicalSample table
                create if they do not exist
            2 - For each row sample metadata into ProcessedSample table
            3 - FCS file metadata into DataProcessing table
            4 - Parameters and counts for each sample into NumericParameter
        
        Parameters
        ----------
        None

        Returns
        -------
        upload_issues : dict
            keys are types of issue, values are descriptions with row in 
            sheet where issue occured. Empty dict is returned if there are
            no issues
        """

        # Assume all checks done - will stop and terminate upload if
        # any errors encountered
        upload_issues = {}
        with transaction.atomic():

            # Ensure all sample numbers are in clinical_sample table
            clinical_samples = self.df["Clinical_sample"].unique().tolist()
            clinical_samples_pk = {}
            for sample in clinical_samples:
                clinical_sample = ClinicalSample.objects.get_or_create(
                    covid_patient_id=sample
                )[0]
                clinical_samples_pk[sample] = clinical_sample.pk

            # Get the panel(s) pks
            panels_pk = {}
            for panel in self.panels:
                panels_pk[panel] = Panel.objects.get(name=panel.upper()).id

            # Store first panel primary key for obtaining parameters for
            # this panel
            panel_pk = panels_pk[self.panels[0]]

            parameters_pk = {}
            for parameter in self.parameter_columns:
                # ToDo add panel to query! we want parameter for this panel
                parameters_pk[parameter] = Parameter.objects.get(
                    gating_hierarchy=parameter, panel=panel_pk
                ).id

            # Store details in relevant tables
            for index, row in self.df.iterrows():

                # Processed sample details
                processed_sample = ProcessedSample(
                    clinical_sample_id=clinical_samples_pk[row["Clinical_sample"]],
                    date_acquired=row["Date"],
                    operator1=row["Operator name"],
                    comments=row["Comments"]
                    # ToDo: batch=row['batch']
                )
                processed_sample.save()

                # Data processing details
                data_processing = DataProcessing(
                    processed_sample_id=processed_sample.id,
                    fcs_file_name=row["X1"],
                    panel_id=panels_pk[row["Panel"]],
                )
                data_processing.save()

                # Store data for parameters
                # Currently assuming all parameters are numeric
                for parameter, parameter_pk in parameters_pk.items():
                    if isinstance(row[parameter], numbers.Number) and not np.isnan(
                        row[parameter]
                    ):
                        numeric_parameter = NumericParameter(
                            processed_sample_id=processed_sample.id,
                            parameter_id=parameters_pk[parameter],
                            value=row[parameter],
                        )
                        numeric_parameter.save()
                    # DEBUG
                    else:
                        key = f"row:{index} parameter:{parameter}"
                        message = (
                            f"Value ({row[parameter]}) not a "
                            + "number - not uploaded to NumericParameter"
                            + " table"
                        )
                        upload_issues[key] = message
        return upload_issues
