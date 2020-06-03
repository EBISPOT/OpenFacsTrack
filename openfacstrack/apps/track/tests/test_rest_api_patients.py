import os, json
from collections import OrderedDict
from django.core.management import call_command
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework import status

from openfacstrack.apps.track.utils import ClinicalSampleFile, PatientFile
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
from openfacstrack.apps.track.serializers import (
    PatientSerializer,
    ProcessedSampleSerializer,
    ResultSerializer,
)

# Test functionality associated with REST API


class PatientTest(TestCase):
    """Test REST API access to patient model"""

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

        # Initialize the APIClient app
        cls.client = Client()

        # Get the base directory
        cls.base_dir = os.path.dirname(os.path.realpath(__file__))

        # Populate reference data table
        fpath = os.path.join(
            cls.base_dir, "test_data", "population_names_20200413.xlsx"
        )
        call_command("update_panel_parameter_reference_data", fpath)

        # Upload test patients
        fname = "test_patient_data.csv"
        fpath = os.path.join(cls.base_dir, "test_data", fname)
        with open(fpath, "rb") as infile:
            uploaded_file = SimpleUploadedFile(
                fpath, infile.read(), content_type="text/csv"
            )
        patient_file = PatientFile(
            file_name=fname, file_contents=uploaded_file, user=cls.user,
        )
        upload_report = patient_file.upload()

        # Upload sample patient data
        fname = "test_panel_data_complete.csv"
        uploaded_file = cls._get_uploaded_file(cls, fname)
        clinical_sample_file = ClinicalSampleFile(
            file_name=fname,
            file_contents=uploaded_file,
            user=cls.user,
            gating_strategy=cls.gating_strategy,
        )

        validation_report = clinical_sample_file.validate()
        upload_report = clinical_sample_file.upload()

    def test_get_all_patients(self):
        response = self.client.get(reverse("get_patients"))

        patients = Patient.objects.all()
        serializer = PatientSerializer(patients, many=True)
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_single_patient(self):
        """
        Here we explicitly test against expected data - independent of the
        serializer
        """
        patient_id = "p005"
        response = self.client.get(reverse("get_patients", kwargs={"pk": patient_id}))

        patient = Patient.objects.get(patient_id=patient_id)

        # Load expected details from json file (have to change created and
        # modified times)
        fname = "test_api_expected_response.json"
        fname = os.path.join(self.base_dir, "test_data", fname)
        with open(fname) as fid:
            expected_json = json.loads(fid.read())
        expected_json = expected_json[0]
        time_format = "%Y-%m-%dT%H:%M:%S.%fZ"
        expected_json["modified"] = patient.modified.strftime(time_format)
        expected_json["created"] = patient.created.strftime(time_format)
        expected_json.pop("samples")
        # Convert the patient metadata into an ordered list
        patient_metadata = expected_json.pop("patient_metadata")
        ordered_patient_metadata = []
        patient_metadata.reverse()
        for item in patient_metadata:
            ordered_patient_metadata.append(OrderedDict(item))
        expected_json["patient_metadata"] = ordered_patient_metadata

        self.assertEqual(response.data, expected_json)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_all_samples(self):
        response = self.client.get(reverse("get_samples"))

        samples = ProcessedSample.objects.all()
        serializer = ProcessedSampleSerializer(samples, many=True)
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_all_observations(self):
        response = self.client.get(reverse("get_observations"))

        results = Result.objects.all()
        serializer = ResultSerializer(results, many=True)
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

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
