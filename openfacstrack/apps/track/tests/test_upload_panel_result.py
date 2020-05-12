import os
from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth.models import User

from django.core.files.uploadedfile import SimpleUploadedFile

from openfacstrack.apps.track.utils import ClinicalSampleFile
from openfacstrack.apps.track.models import (
    GatingStrategy,
    Patient,
    ProcessedSample,
    Result,
    DataProcessing,
    NumericValue,
    TextValue,
    DateValue,
    UploadedFile,
)

# Test functionality associated with uploading panel results


class UploadPanelResultTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create gating strategy
        gating_strategy = GatingStrategy(strategy="Automatically Gated")
        gating_strategy.save()
        cls.gating_strategy = gating_strategy

        # Create user needed for tests
        user = User.objects.create_user(
            username="test", email="test@test.com", password="test"
        )
        user.save()
        cls.user = user

        # Get the base directory
        cls.base_dir = os.path.dirname(os.path.realpath(__file__))

        # Populate reference data table
        fpath = os.path.join(
            cls.base_dir, "test_data", "population_names_20200413.xlsx"
        )
        call_command("update_panel_parameter_reference_data", fpath)

        # Populate reference data table
        # call_command('update_panel_parameter_reference_data',
        #            'sample_data/population_names_20200413.xlsx')

    def setUp(self):
        pass

    def test_all_expected_columns_present(self):
        """If static column missing or unexpected columns present, entry is made in validation errors"""

        fpath = os.path.join(self.base_dir, "test_data", "test_panel_data_complete.csv")
        with open(fpath, "rb") as infile:
            uploaded_file = SimpleUploadedFile(
                fpath, infile.read(), content_type="text/csv"
            )
        clinical_sample_file = ClinicalSampleFile(
            file_name="test_panel_data_complete.csv",
            file_contents=uploaded_file,
            user=self.user,
            gating_strategy=self.gating_strategy,
        )

        validation_report = clinical_sample_file.validate()
        length_of_validation_report = len(validation_report)
        # If no validation errors the validation report should be empty.
        if length_of_validation_report > 0:
            print("There were validation errors:")
            print(validation_report)
        self.assertEqual(length_of_validation_report, 0)

    def test_fatal_error_on_missing_required_column(self):
        """A missing required column should give rise to a fatal error"""

        file_name = "test_panel_data_missing_required_column.csv"
        fpath = os.path.join(self.base_dir, "test_data", file_name)
        with open(fpath, "rb") as infile:
            uploaded_file = SimpleUploadedFile(
                fpath, infile.read(), content_type="text/csv"
            )
        clinical_sample_file = ClinicalSampleFile(
            file_name=file_name,
            file_contents=uploaded_file,
            user=self.user,
            gating_strategy=self.gating_strategy,
        )

        validation_report = clinical_sample_file.validate()
        length_of_validation_report = len(validation_report)
        # There should be an entry in validation errors .
        self.assertEquals(length_of_validation_report, 1)

        # The first entry should have key: required_columns_missing
        # type FATAL and value Clinical_sample
        validation_entry = validation_report[0]
        self.assertEquals(validation_entry.key, "required_columns_missing")
        self.assertEquals(validation_entry.entry_type, "FATAL")
        self.assertEquals(validation_entry.value, ["Clinical_sample"])

    def test_error_on_missing_static_column(self):
        """A missing static column should give rise to a non fatal error - but upload can proceed"""

        file_name = "test_panel_data_missing_static_column.csv"
        fpath = os.path.join(self.base_dir, "test_data", file_name)
        with open(fpath, "rb") as infile:
            uploaded_file = SimpleUploadedFile(
                fpath, infile.read(), content_type="text/csv"
            )
        clinical_sample_file = ClinicalSampleFile(
            file_name=file_name,
            file_contents=uploaded_file,
            user=self.user,
            gating_strategy=self.gating_strategy,
        )

        validation_report = clinical_sample_file.validate()
        length_of_validation_report = len(validation_report)
        # There should be an entry in validation errors .
        self.assertEquals(length_of_validation_report, 1)

        # The first entry should have key: required_columns_missing
        # type FATAL and value Clinical_sample
        validation_entry = validation_report[0]
        self.assertEquals(validation_entry.key, "static_columns_missing")
        self.assertEquals(validation_entry.entry_type, "ERROR")
        self.assertEquals(validation_entry.value, ["Comments"])

        # Upload should occur with warning about date field missing
        # ToDo: Test upload works for missing static data
        # upload_report = clinical_sample_file.upload(dry_run=False)
        # print(upload_report)

    def test_patient_id_created(self):
        """Test patient ID created during upload"""

        fname = "test_panel_data_complete.csv"
        uploaded_file = self._get_uploaded_file(fname)
        clinical_sample_file = ClinicalSampleFile(
            file_name=fname,
            file_contents=uploaded_file,
            user=self.user,
            gating_strategy=self.gating_strategy,
        )

        upload_report = clinical_sample_file.upload()
        self.assertTrue(len(upload_report), 0)

        n_patients_created = Patient.objects.count()
        self.assertEqual(n_patients_created, 2)

    def test_complete_file_uploaded(self):
        """Test basic functionality works - all entries uploaded from sample file"""

        fname = "test_panel_data_complete.csv"
        uploaded_file = self._get_uploaded_file(fname)
        clinical_sample_file = ClinicalSampleFile(
            file_name=fname,
            file_contents=uploaded_file,
            user=self.user,
            gating_strategy=self.gating_strategy,
        )

        upload_report = clinical_sample_file.upload()
        self.assertTrue(len(upload_report), 0)

        # Check we have expected entries
        expected_results = self._get_expected_panel_results()

        # Patients
        self.assertTrue(Patient.objects.count(), 2)
        for expected_result in expected_results:
            patient_id = expected_result["patient_id"]
            self.assertEqual(Patient.objects.filter(patient_id=patient_id).count(), 1)

        # Samples
        self.assertTrue(ProcessedSample.objects.count(), 2)
        for expected_result in expected_results:
            sample_id = expected_result["sample_id"]
            self.assertEqual(
                ProcessedSample.objects.filter(clinical_sample_id=sample_id).count(), 1
            )

        # Results
        self.assertTrue(Result.objects.count(), 3)
        for expected_result, result in zip(expected_results, Result.objects.all()):
            self.assertEqual(
                expected_result["sample_id"], result.processed_sample.clinical_sample_id
            )
            self.assertEqual(
                expected_result["filename"], result.data_processing.fcs_file_name
            )
            self.assertEqual(expected_result["panel"].upper(), result.panel.name)
            self.assertEqual(self.gating_strategy, result.gating_strategy)
            self.assertEqual(fname, result.uploaded_file.name)

        # Numeric values
        # ToDo: Test actual values
        self.assertEqual(NumericValue.objects.count(), 9)

        # Date values
        # ToDo: Test actual values
        self.assertEqual(DateValue.objects.count(), 2)

        # Text values
        # ToDo: Test actual values
        self.assertEqual(TextValue.objects.count(), 1)

    #        validation_report_contains="Key:static_columns_missing, Value:['X1']"
    # We only expect one error here - missing X1 column
    # validation_report = clinical_sample_file.validate()
    # self.assertEqual(length_of_validation_report,len(validation_report))
    #
    ## Check missing X1 column is identified
    # validation_entry = validation_report[0]
    # self.assertEquals(validation_entry.key,"static_columns_missing")
    # self.assertEquals(validation_entry.value,['X1'])

    def _get_uploaded_file(self, fname):
        """Return django object representing an uploaded file"""

        fpath = os.path.join(self.base_dir, "test_data", fname)
        with open(fpath, "rb") as infile:
            uploaded_file = SimpleUploadedFile(
                fpath, infile.read(), content_type="text/csv"
            )
        return uploaded_file

    def _get_expected_panel_results(self):
        """Return the results we expect (in the expected order)"""

        expected_results = [
            {
                "batch": 1,
                "filename": "20200327p5_p005n01_020.fcs",
                "numeric_parameters": {
                    "Cells_5/Time_5/Live_5/Live_cells_5/CD3p_5/No_Doublets_5/ab_5/Foxp3n_5/CD8p_5/CD8_CD45RAn_CCR7n_5 | Count": 3128,
                    "Cells_5/Time_5/Live_5/Live_cells_5/CD3p_5/No_Doublets_5/ab_5/Foxp3n_5/CD8p_5/CD8_CD45RAn_CCR7p_5/S_G2_M_5 | Count": 0,
                },
                "operator_1": 3,
                "comments": "",
                "date_processed": "20200327",
                "panel": "p5",
                "sample_id": "p005n01",
                "patient_id": "p005",
            },
            {
                "batch": 6,
                "filename": "20200407p5_p033n01_003.fcs",
                "numeric_parameters": {
                    "Cells_5/Time_5/Live_5/Live_cells_5/CD3p_5/No_Doublets_5/ab_5/Foxp3n_5/CD8p_5/CD8_CD45RAn_CCR7n_5 | Count": 7244,
                    "Cells_5/Time_5/Live_5/Live_cells_5/CD3p_5/No_Doublets_5/ab_5/Foxp3n_5/CD8p_5/CD8_CD45RAn_CCR7p_5/S_G2_M_5 | Count": 25,
                },
                "operator_1": "",
                "comments": "Test comments xxx",
                "date_processed": "",
                "panel": "p5",
                "sample_id": "p033n01",
                "patient_id": "p033",
            },
            {
                "batch": 6,
                "filename": "20200410p5_p033n01_002.fcs",
                "numeric_parameters": {
                    "Cells_5/Time_5/Live_5/Live_cells_5/CD3p_5/No_Doublets_5/ab_5/Foxp3n_5/CD8p_5/CD8_CD45RAn_CCR7p_5/S_G2_M_5 | Count": 5,
                },
                "operator_1": "nan",
                "comments": "",
                "date_processed": "20200410",
                "panel": "p5",
                "sample_id": "p033n01",
                "patient_id": "p033",
            },
        ]
        return expected_results

    @classmethod
    def tearDownClass(cls):
        """Remove all files uploaded during tests - test_panel*"""

        fpath = os.path.join(cls.base_dir, "..", "..", "..", "..", "uploads")
        command = f'find {fpath} -type f -name "test_panel*.csv" -exec rm {{}} \\;'
        retval = os.system(command)
        if retval != 0:
            message = (
                "Test files uploaded have not been deleted. "
                + "Please manually delete. They are located in "
                + "a subdirectory of the 'uploads' directory"
            )
            print("\n\n" + message)

        super().tearDownClass()
