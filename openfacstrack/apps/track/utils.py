import os
import numbers
import base64

from django.contrib.auth.models import User
from django.db import transaction
import io
import pandas as pd
import numpy as np

from openfacstrack.apps.track.models import (
    PanelMetadata,
    Parameter,
    ProcessedSample,
    DataProcessing,
    Patient,
    PatientMetadataDict,
    PatientMetadata,
    Panel,
    NumericValue,
    TextValue,
    UploadedFile,
    ValidationEntry,
)


class ClinicalSampleFile:
    """
    Uploads a file with results from clinical samples.
    """

    def __init__(
        self,
        file_name=None,
        file_contents=None,
        uploaded_file: UploadedFile = None,
        user: User = None,
    ):
        """load contents of file into a data frame and set other attribs.

        Parameters
        ----------
        filepath : string
            path to file (csv) to read

        Returns
        -------
        None
        """
        if uploaded_file:
            self.upload_file = uploaded_file
            file_name = uploaded_file.name
            file_contents = uploaded_file.content
            #print(file_contents)
        self.content = file_contents
        self.file_name = file_name
        self.df = pd.read_csv(self.content, parse_dates=["Date"])

        # List of columns always expected
        # ToDo: Find out if any of these columns are 'required' - if so
        #       cannot continue without them.
        self.static_columns = [
            "batch",
            "filename",
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
        if not uploaded_file:
            self.upload_file = UploadedFile(
                name=self.file_name,
                user=user,
                description="Panel results",
                row_number=self.nrows,
                content=self.content,
                notes="",
            )
            self.upload_file.save()

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
        validation_errors = []

        # Check we have the expected number of columns.
        static_columns_missing = []
        for static_column in self.static_columns:
            if static_column not in self.df.columns:
                static_columns_missing.append(static_column)
        if len(static_columns_missing) > 0:
            error = ValidationEntry(
                subject_file=self.upload_file,
                key="static_columns_missing",
                value=static_columns_missing,
                entry_type="ERROR",
                validation_type="SYNTAX",
            )
            error.save()
            validation_errors.append(error)
            self.upload_file.valid_syntax = False
            self.upload_file.save()

        # Check that all the info is for the same panel
        if "Panel" in self.df.columns:
            panels_in_data = self.df["Panel"].unique().tolist()
            n_unique_panels_in_data = len(panels_in_data)
            if n_unique_panels_in_data != 1:
                error = ValidationEntry(
                    subject_file=self.upload_file,
                    key="unique_panel_error",
                    value=f"Expected 1 unique value for panels in each record"
                    + f". Got {n_unique_panels_in_data}: {panels_in_data}",
                    entry_type="ERROR",
                    validation_type="SYNTAX",
                )
                error.save()
                validation_errors.append(error)
                self.upload_file.valid_syntax = False
                self.upload_file.save()

            # Check if the panel(s) are present in the Panel table
            panels_in_data_pk = []
            unknown_panels = []
            for panel in panels_in_data:
                try:
                    panels_in_data_pk.append(Panel.objects.get(name=panel.upper()).id)
                except Panel.DoesNotExist as e:
                    unknown_panels.append(panel)
            if len(unknown_panels) > 0:
                error = ValidationEntry(
                    subject_file=self.upload_file,
                    key="unknown_panel_error",
                    value=f"The following panels are not in Panel table: {unknown_panels}",
                    entry_type="WARN",
                    validation_type="SYNTAX",
                )
                error.save()
                validation_errors.append(error)

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
        self.parameter_columns = [
            column
            for column in self.parameter_columns
            if column not in unregistered_parameters
        ]
        if len(unregistered_parameters) > 0:
            error = ValidationEntry(
                subject_file=self.upload_file,
                key="unregistered_parameters",
                value=unregistered_parameters,
                entry_type="WARN",
                validation_type="SYNTAX",
            )
            error.save()
            validation_errors.append(error)

        # Check all fields needed for processed_sample table present

        # Check all clinical samples present in clinical_sample table

        # Enter values into clinical_sample, processed_sample,
        # numeric_value and text_parameter

        # Print out list of validation errors
        # print("Validation errors:")
        return validation_errors

    def upload(self, dry_run=False):
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
            5 - Parameters and counts for each sample into NumericValue
        
        Parameters
        ----------
        dry_run : boolean
            Indicates it's going to attempt to do the upload without committing the changes.

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
        upload_issues = []
        rows_with_issues = set()
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
                    comments=row["Comments"],
                    batch=row["batch"],
                    uploaded_file_id=self.upload_file.id,
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
                        numeric_value = NumericValue(
                            processed_sample_id=processed_sample.id,
                            parameter_id=parameters_pk[parameter],
                            value=row[parameter],
                        )
                        numeric_value.save()
                    # DEBUG
                    else:
                        validation_entry = ValidationEntry(
                            subject_file=self.upload_file,
                            key=f"row:{index} parameter:{parameter}",
                            value=f"Value ({row[parameter]}) not a "
                            + "number - not uploaded to NumericValue"
                            + " table",
                            entry_type="WARN",
                            validation_type="MODEL",
                        )
                        upload_issues.append(validation_entry)
                        rows_with_issues.add(index)

            upload_report = {
                "rows_processed": self.nrows,
                "rows_with_issues": len(rows_with_issues),
                "validation": upload_issues,
            }
            if dry_run:
                transaction.set_rollback(True)
        if upload_issues:
            for issue in upload_issues:
                issue.save()
        else:
            self.upload_file.valid_model = True
            self.upload_file.save()
        return upload_report
