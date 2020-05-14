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
    Result,
    DataProcessing,
    Patient,
    PatientMetadataDict,
    PatientMetadata,
    Panel,
    NumericValue,
    TextValue,
    DateValue,
    UploadedFile,
    ValidationEntry,
    GatingStrategy,
)


class ClinicalSampleFile:
    """
    Validates and uploads a file with results from clinical samples.
    """

    def __init__(
        self,
        file_name=None,
        file_contents=None,
        uploaded_file: UploadedFile = None,
        user: User = None,
        gating_strategy: GatingStrategy = None,
    ):
        """load contents of file into a data frame and set other attribs.

        Parameters
        ----------
        file_name : string
            name of file
        file_contents : InMemoryUploadedFile
            Django object with binary contents of uploaded file
        uploaded_file : UploadedFile
            custom object to store details of uploaded file
        user : User
            Django object representing user making upload
        gating_strategy : GatingStrategy
            Custom object representing the GatingStrategy for this upload

        Returns
        -------
        None
        """
        if uploaded_file:
            self.upload_file = uploaded_file
            file_name = uploaded_file.name
            file_contents = uploaded_file.content
            # print(file_contents)
        self.content = file_contents
        self.file_name = file_name
        self.gating_strategy = gating_strategy
        self.df = pd.read_csv(self.content, parse_dates=["Date"])

        # List of columns always expected
        # ToDo: Find out if any of these columns are 'required' - if so
        #       cannot continue without them.

        # Use variables to store static_column names in case they change
        # in future
        self.sc_panel = "Panel"
        self.sc_clinical_sample = "Clinical_sample"
        self.sc_filename = "filename"
        self.sc_operator1 = "Operator name"
        self.sc_comments = "Comments"
        self.sc_batch = "batch"
        self.sc_date = "Date"
        self.required_columns = [
            self.sc_filename,
            self.sc_panel,
            self.sc_clinical_sample,
        ]

        self.static_columns = [
            self.sc_batch,
            self.sc_operator1,
            self.sc_comments,
            self.sc_date,
        ]

        # Store the unique panels in the data
        # ToDo: I think there should be only one unique panel - check.
        self.panels = self.df["Panel"].unique().tolist()
        self.panel_name = self.panels[0].upper()

        # Compute names of parameters present. These are all the other
        # columns in the file that are not in the static_columns list
        # and are not unregistered_derived_parameters
        parameter_columns = set(self.df.columns) - set(self.static_columns)
        parameter_columns -= set(self.required_columns)
        self.parameter_columns = list(parameter_columns)

        # Store unregistered parameters. Derived ones will be dynamically
        # added to the Parameter table before upload
        self.unregistered_derived_parameters = []
        self.unregistered_parameters = []
        for parameter_column in self.parameter_columns:
            try:
                parameter_object = Parameter.objects.get(
                    gating_hierarchy=parameter_column
                )
            except Parameter.DoesNotExist:
                if parameter_column.endswith("Count_back") or parameter_column.endswith(
                    "freq"
                ):
                    self.unregistered_derived_parameters.append(parameter_column)
                else:
                    self.unregistered_parameters.append(parameter_column)
        self.parameter_columns = [
            column
            for column in self.parameter_columns
            if column not in self.unregistered_parameters
            and column not in self.unregistered_derived_parameters
        ]

        # Names for pseudo parameters (parameters computed from data)
        self.pseudo_parameters_numeric = []
        if self.sc_batch in self.df.columns:
            self.pseudo_parameters_numeric.append(
                (self.sc_batch, f"{self.panel_name}_batch")
            )
        if self.sc_operator1 in self.df.columns:
            self.pseudo_parameters_numeric.append(
                (self.sc_operator1, f"{self.panel_name}_operator_1")
            )

        self.pseudo_parameters_date = []
        if self.sc_date in self.df.columns:
            self.pseudo_parameters_date.append(
                (self.sc_date, f"{self.panel_name}_date_processed")
            )

        self.pseudo_parameters_text = []
        if self.sc_comments in self.df.columns:
            self.pseudo_parameters_text.append(
                (self.sc_comments, f"{self.panel_name}_comments")
            )

        # Number of rows to process
        self.nrows = len(self.df)

        # Default uploaded file
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
        validation_error : list
            list of validation errors. Each entry in the list is a 
            ValidationEntry object - basically a dict 
            whose keys are types of errors and values are descriptions. 
            Empty list is returned if there are no errors
        """

        # Start validation writing errors into dictionary/or json string?
        validation_errors = []

        # Check we have the required columns needed for upload to proceed.
        required_columns_missing = []
        for required_column in self.required_columns:
            if required_column not in self.df.columns:
                required_columns_missing.append(required_column)
        if len(required_columns_missing) > 0:
            error = ValidationEntry(
                subject_file=self.upload_file,
                key="required_columns_missing",
                value=required_columns_missing,
                entry_type="FATAL",
                validation_type="SYNTAX",
            )
            error.save()
            validation_errors.append(error)
            self.upload_file.valid_syntax = False
            self.upload_file.save()

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
        # It is dangerous to proceed otherwise as we will
        # mainly because of the parameters we dynamically
        # compose from the panel name.
        if "Panel" in self.df.columns:
            panels_in_data = self.df["Panel"].unique().tolist()
            n_unique_panels_in_data = len(panels_in_data)
            if n_unique_panels_in_data != 1:
                error = ValidationEntry(
                    subject_file=self.upload_file,
                    key="unique_panel_error",
                    value=f"Expected 1 unique value for panels in each record"
                    + f". Got {n_unique_panels_in_data}: {panels_in_data}",
                    entry_type="FATAL",
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

        if len(self.unregistered_parameters) > 0:
            error = ValidationEntry(
                subject_file=self.upload_file,
                key="unregistered_parameters",
                value=self.unregistered_parameters,
                entry_type="WARN",
                validation_type="SYNTAX",
            )
            error.save()
            validation_errors.append(error)

        if len(self.unregistered_derived_parameters) > 0:
            error = ValidationEntry(
                subject_file=self.upload_file,
                key="unregistered_derived_parameters - will be added during upload",
                value=self.unregistered_derived_parameters,
                entry_type="INFO",
                validation_type="SYNTAX",
            )
            error.save()
            validation_errors.append(error)

        # Check all fields needed for processed_sample table present

        # Check all clinical samples present in processed_sample table

        # Enter values into processed_sample, processed_sample,
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
        the dry_run parameter is False nothing is written to the database.
        This is useful to get details of any records that have issues that
        would otherwise be missed when writing to the database.
        
        Workflow:
            1 - Details of the file being uploaded are written to the 
                UploadedFile table - the ID of this file is saved so that
                it can be stored with each record in the Result table
            2 - covid patient IDs loaded into Patient table
                create if they do not exist
            3 - For each row create unique record in Result table if it
                    does not already exist. Uniqueness is by
                    (panel, fcs_file_name, gating_strategy) then store:
                (a) patient_id in Patient table
                (b) sample_id (and any other sample metadata in 
                    ProcessedSample table
                (c) FCS file metadata into DataProcessing table
                (d) Parameters and values for each sample into 
                    NumericValue, DateValue and TextValue tables

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
            # Ensure all sample numbers are in processed_sample table
            # and respective records for patients exist
            sample_ids = self.df[self.sc_clinical_sample].unique().tolist()
            patient_ids = [str(s_id).split("n")[0] for s_id in sample_ids]
            processed_sample_pks = {}
            for patient_id, sample_id in zip(patient_ids, sample_ids):
                patient = Patient.objects.get_or_create(patient_id=patient_id)[0]
                processed_sample = ProcessedSample.objects.get_or_create(
                    clinical_sample_id=sample_id, patient=patient
                )[0]
                processed_sample_pks[sample_id] = processed_sample.pk

            # Get the panel(s) pks
            panels_pk = {}
            for panel in self.panels:
                panels_pk[panel] = Panel.objects.get(name=panel.upper()).id

            # Store first panel primary key for use later
            panel_pk = panels_pk[self.panels[0]]

            # Append any unregistered derived parameters to parameter table
            for parameter_to_add in self.unregistered_derived_parameters:
                parameter, created = Parameter.objects.get_or_create(
                    gating_hierarchy=parameter_to_add, panel_id=panel_pk
                )
                parameter.internal_name = parameter_to_add
                parameter.public_name = parameter_to_add
                parameter.is_reference_parameter = False
                if parameter_to_add.endswith("freq"):
                    parameter.unit = "Derived frequency"
                else:
                    parameter.unit = "Derived count"
                parameter.data_type = "PanelNumeric"
                parameter.description = parameter.unit
                parameter.save()

                self.parameter_columns.append(parameter_to_add)

            # Get parameter_ids for NumericParameters
            parameters_pk = {}
            for parameter in self.parameter_columns:
                parameters_pk[parameter] = Parameter.objects.get(
                    gating_hierarchy=parameter
                ).id

            # Ditto for pseudo parameters (date, text, numeric)
            pseudo_parameters_pk = {}
            for column, parameter in self.pseudo_parameters_numeric:
                pseudo_parameters_pk[parameter] = Parameter.objects.get(
                    gating_hierarchy=parameter
                ).id

            for column, parameter in self.pseudo_parameters_date:
                pseudo_parameters_pk[parameter] = Parameter.objects.get(
                    gating_hierarchy=parameter
                ).id

            for column, parameter in self.pseudo_parameters_text:
                pseudo_parameters_pk[parameter] = Parameter.objects.get(
                    gating_hierarchy=parameter
                ).id

            # Store details in relevant tables
            for index, row in self.df.iterrows():

                # Only proceed if sample_id is valid
                sample_id = str(row[self.sc_clinical_sample])
                if not sample_id.upper().startswith("P") or len(sample_id) < 4:
                    validation_entry = ValidationEntry(
                        subject_file=self.upload_file,
                        key=f"row:{index} field:Clinical_sample",
                        value=f"Value ({sample_id}) not a valid "
                        + "clinical sample id. Expected pxxxnxx. "
                        + "All entries for this row not loaded.",
                        entry_type="WARN",
                        validation_type="MODEL",
                    )
                    upload_issues.append(validation_entry)
                    rows_with_issues.add(index)
                    continue

                # Data processing details
                fcs_file_name = row[self.sc_filename]
                if type(fcs_file_name) == str and fcs_file_name.find(sample_id) >= 0:
                    data_processing, created = DataProcessing.objects.get_or_create(
                        fcs_file_name=fcs_file_name, panel_id=panels_pk[row["Panel"]],
                    )
                else:
                    validation_entry = ValidationEntry(
                        subject_file=self.upload_file,
                        key=f"row:{index} field:{self.sc_filename}",
                        value=f"Value {fcs_file_name} does not contain the"
                        + f" sample ID ({sample_id}) - row not loaded",
                        entry_type="WARN",
                        validation_type="MODEL",
                    )
                    upload_issues.append(validation_entry)
                    rows_with_issues.add(index)
                    continue

                # Create an entry in the results table
                result = Result.objects.get_or_create(
                    processed_sample_id=processed_sample_pks[sample_id],
                    gating_strategy=self.gating_strategy,
                    panel_id=panel_pk,
                    data_processing=data_processing,
                )[0]
                result.uploaded_file = self.upload_file
                result.save()

                # Store data for parameters
                for parameter, parameter_pk in parameters_pk.items():
                    if isinstance(row[parameter], numbers.Number) and not np.isnan(
                        row[parameter]
                    ):
                        numeric_value, created = NumericValue.objects.get_or_create(
                            result_id=result.id, parameter_id=parameters_pk[parameter],
                        )
                        numeric_value.value = row[parameter]
                        numeric_value.save()
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

                # Store numeric pseudo parameters
                for column, parameter in self.pseudo_parameters_numeric:
                    value = row[column]
                    if isinstance(value, numbers.Number) and not np.isnan(value):
                        numeric_value, created = NumericValue.objects.get_or_create(
                            result_id=result.id,
                            parameter_id=pseudo_parameters_pk[parameter],
                        )
                        numeric_value.value = value
                        numeric_value.save()
                    else:
                        validation_entry = ValidationEntry(
                            subject_file=self.upload_file,
                            key=f"row:{index} parameter:{parameter}",
                            value=f"Value ({value}) not a "
                            + "number - not uploaded to NumericValue"
                            + " table",
                            entry_type="WARN",
                            validation_type="MODEL",
                        )
                        upload_issues.append(validation_entry)
                        rows_with_issues.add(index)

                # Stdate pseudo parameters
                for column, parameter in self.pseudo_parameters_date:
                    value = row[column]
                    if isinstance(value, pd.Timestamp) and not pd.isnull(value):
                        date_value, created = DateValue.objects.get_or_create(
                            result_id=result.id,
                            parameter_id=pseudo_parameters_pk[parameter],
                        )
                        date_value.value = value
                        date_value.save()
                    else:
                        validation_entry = ValidationEntry(
                            subject_file=self.upload_file,
                            key=f"row:{index} parameter:{parameter}",
                            value=f"Value ({value}) not a "
                            + "Date - not uploaded to DateValue"
                            + " table",
                            entry_type="WARN",
                            validation_type="MODEL",
                        )
                        upload_issues.append(validation_entry)
                        rows_with_issues.add(index)

                # Store text pseudo parameters
                for column, parameter in self.pseudo_parameters_text:
                    value = str(row[column]).strip()
                    if len(value) > 0 and value != "nan":
                        text_value, created = TextValue.objects.get_or_create(
                            result_id=result.id,
                            parameter_id=pseudo_parameters_pk[parameter],
                        )
                        text_value.value = value
                        text_value.save()

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


class PatientFile:
    """Uploads a file with anonymised patient details."""

    def __init__(
        self,
        file_name=None,
        file_contents=None,
        uploaded_file: UploadedFile = None,
        user: User = None,
    ):
        if uploaded_file:
            self.upload_file = uploaded_file
            file_name = uploaded_file.name
            file_contents = uploaded_file.content
        self.content = file_contents
        self.file_name = file_name
        self.df = pd.read_csv(self.content)
        self.nrows = len(self.df)

        # Default uploaded file
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

        self.patient_ids = self.df["patient"].unique().tolist()

    def upload(self, dry_run=False):
        """Upload data to relevant tables"""

        upload_issues = []
        rows_with_issues = []

        with transaction.atomic():

            # Create metadata dict entries if necessary
            columns = self.df.columns.tolist()
            columns.remove("patient")
            metadata_dicts = {}
            for column in columns:
                column_lc = column.lower()
                metadata_dict, created = PatientMetadataDict.objects.get_or_create(
                    name=column_lc
                )
                if created:
                    metadata_dict.description = f"{column}"
                    metadata_dict.notes = "Dynamically added"
                    metadata_dict.save()
                metadata_dicts[column] = metadata_dict

            # Enter details for all patients
            for index, row in self.df.iterrows():
                patient_id = str(row["patient"])
                # Create patients if necessary
                if not patient_id.upper().startswith("P"):
                    validation_entry = ValidationEntry(
                        subject_file=self.upload_file,
                        key=f"row:{index} field:patient",
                        value=f"Value ({patient_id}) not valid. "
                        + "Expected pxxx. Entries for this id not loaded.",
                        entry_type="WARN",
                        validation_type="MODEL",
                    )
                    upload_issues.append(validation_entry)
                    rows_with_issues.append(index)
                    continue
                patient = Patient.objects.get_or_create(patient_id=patient_id)[0]

                # Store metadata associated with patient
                for column, metadata_dict in metadata_dicts.items():
                    value = row[column]
                    patient_metadata = PatientMetadata.objects.get_or_create(
                        patient=patient, metadata_key=metadata_dict
                    )[0]
                    patient_metadata.metadata_value = value
                    patient_metadata.save()

            if upload_issues:
                for issue in upload_issues:
                    issue.save()
            else:
                self.upload_file.valid_model = True

            if dry_run:
                transaction.set_rollback(True)
            else:
                # Put this here as I think uploaded file is also saved to disk. Can this be rolled back?
                self.upload_file.save()

        upload_report = {
            "rows_processed": self.nrows,
            "rows_with_issues": len(rows_with_issues),
            "upload_issues": upload_issues,
        }
        return upload_report
