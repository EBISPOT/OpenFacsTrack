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
    Parameter,
    NumericValue,
    TextValue,
    DateValue,
    UploadedFile,
)

# Test functionality associated with REST API


class GetAllDataTest(TestCase):
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

        # Upload sample patient data
        fname = "test_panel_data_complete.csv"
        uploaded_file = self._get_uploaded_file(fname)
        clinical_sample_file = ClinicalSampleFile(
            file_name=fname,
            file_contents=uploaded_file,
            user=self.user,
            gating_strategy=self.gating_strategy,
        )

        validation_report = clinical_sample_file.validate()
        upload_report = clinical_sample_file.upload()

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
