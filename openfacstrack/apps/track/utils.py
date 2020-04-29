import os
import numbers
import base64
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
    UploadedFile,
)


class ClinicalSampleFile:
    """
    Uploads a file with results from clinical samples.
    """

    def __init__(self, file_name, file_contents):
        """load contents of file into a data frame and set other attribs.

        Parameters
        ----------
        filepath : string
            path to file (csv) to read

        Returns
        -------
        None
        """
        self.content = file_contents
        self.file_name = file_name
        self.df = pd.read_csv(file_contents, parse_dates=["Date"])

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

        # Number of rows to process
        self.nrows = len(self.df)

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

    def upload(self, commit_with_issues=False):
        """Upload file to respective tables

        Upload data in clinical sample results for panel into the database.
        We assume that all the results here are based on one panel (ToDo: 
        need to confirm whether to throw error during validation if more
        than one panel). The upload is carried out in an atomic transaction
        and if there are any errors nothing is written to the database. If
        the commit parameter is False nothing is written to the database.
        This is useful to get details of any records that have issues that
        would otherwise be missed when writing to the database.
        
        Workflow:
            1 - Details of the file being uploaded are written to the 
                UploadedFile table - the ID of this file is saved so that
                it can be stored with each record in the ProcessedSample
                table
            2 - covid patient IDs loaded into ClinicalSample table
                create if they do not exist
            3 - For each row store sample metadata in ProcessedSample 
                table along with ID of file being uploaded (see step 1)
            4 - FCS file metadata into DataProcessing table
            5 - Parameters and counts for each sample into NumericParameter
        
        Parameters
        ----------
        commit_with_issues : boolean
            Forces write to database even if there are upload issues.

        Returns
        -------
        upload_report : dict
            Details of how upload proceeded. Keys are:
                success : boolean - whether upload was successful
                rows_processed : int - No. of rows from csv file
                rows_with_issues : int - No. of rows that had issues
                upload_issues : dict - keys are types of issue, values are 
                                descriptions with row in sheet where issue
                                occured. Empty dict is returned if there 
                                are no issues
        """

        # Assume all checks done - will stop and terminate upload if
        # any errors encountered
        upload_issues = {}
        rows_with_issues = set()
        with transaction.atomic():

            # ToDo: Save details of this file to database
            uploaded_file = self._create_uploaded_file()
            uploaded_file.save()

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
                    # ToDo: uploaded_file_id=self.uploaded_file_id
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
                        rows_with_issues.add(index)

            upload_report = {
                "rows_processed": self.nrows,
                "rows_with_issues": len(rows_with_issues),
                "upload_issues": upload_issues,
            }
            if upload_issues:
                uploaded_file.notes = f"{upload_issues}"
                uploaded_file.save()
                if commit_with_issues == False:
                    transaction.set_rollback(True)
                    upload_report["success"] = False
            else:
                upload_report["success"] = True

        return upload_report

    def _create_uploaded_file(self):
        """Create an instance of UploadedFile for this class' data

        Parameters
        ----------
        None

        Returns
        -------
        uploaded_file : object
            Instance of UploadedFile with file for this clinical sample
        """
        return UploadedFile(
            name=self.file_name,
            description="Panel results",
            content=base64.b64encode(self.content.read()),
            notes="",
        )
