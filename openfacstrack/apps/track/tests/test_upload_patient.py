import os
from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth.models import User

from django.core.files.uploadedfile import SimpleUploadedFile

from openfacstrack.apps.track.utils import PatientFile
from openfacstrack.apps.track.models import (
    Patient,
    UploadedFile,
    PatientMetadataDict,
    PatientMetadata,
)

# Test functionality associated with uploading panel results


class UploadPatientTest(TestCase):
    @classmethod
    def setUpTestData(cls):

        # Create user needed for tests
        user = User.objects.create_user(
            username="test", email="test@test.com", password="test"
        )
        user.save()
        cls.user = user

        # Get the base directory
        cls.base_dir = os.path.dirname(os.path.realpath(__file__))

    def setUp(self):
        pass

    def test_upload(self):
        """Test upload succeeded"""

        fname = "test_patient_data.csv"
        fpath = os.path.join(self.base_dir, "test_data", fname)
        with open(fpath, "rb") as infile:
            uploaded_file = SimpleUploadedFile(
                fpath, infile.read(), content_type="text/csv"
            )
        patient_file = PatientFile(
            file_name=fname, file_contents=uploaded_file, user=self.user,
        )

        upload_report = patient_file.upload()

        # Upload proceeded with no issues
        upload_issues = upload_report["upload_issues"]
        length_of_upload_issues = len(upload_issues)
        self.assertEqual(length_of_upload_issues, 0)

        # All expected patients created
        self.assertEqual(Patient.objects.count(), 3)

        # All expected metadata dict entries created
        self.assertEqual(PatientMetadataDict.objects.count(), 11)

        # All expected metadata stored
        # Patient p005 - 4 NA, p025 - 2 NA, p033 - 2 NA, 2 blank
        # Therefore expect (3x11)-(4+2+2+2) = 33-10 = 23 metadata objects
        self.assertEqual(PatientMetadata.objects.count(), 23)

        # Uploaded file details stored

    @classmethod
    def tearDownClass(cls):
        """Remove all files uploaded during tests - test_patient*"""

        fpath = os.path.join(cls.base_dir, "..", "..", "..", "..", "uploads")
        command = f'find {fpath} -type f -name "test_patient*.csv" -exec rm {{}} \\;'
        retval = os.system(command)
        if retval != 0:
            message = (
                "Test files uploaded have not been deleted. "
                + "Please manually delete. They are located in "
                + "a subdirectory of the 'uploads' directory"
            )
            print("\n\n" + message)

        super().tearDownClass()
