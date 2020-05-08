from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth.models import User

from openfacstrack.apps.track.utils import ClinicalSampleFile

# Create your tests here.

class ClinicalSampleFileTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create user needed for tests
        user = User.objects.create_user(username='test',
                                        email='test@test.com',
                                        password='test')
        user.save()
        cls.user = user

        # Populate reference data table
        call_command('update_panel_parameter_reference_data', 
                    'sample_data/population_names_20200413.xlsx')

    def setUp(self):
        pass

    def test_all_static_columns_present(self):
        """If static column missing entry is made in validation errors"""

        
        clinical_sample_file = ClinicalSampleFile(file_name='test_panel_data_complete.csv',
            file_contents='sample_data/test_panel_data_static_column_x1_missing.csv',
            user=self.user)
        
        length_of_validation_report = 1
        validation_report_contains="Key:static_columns_missing, Value:['X1']"
        # We only expect one error here - missing X1 column
        validation_report = clinical_sample_file.validate()
        self.assertEqual(length_of_validation_report,len(validation_report))
        
        # Check missing X1 column is identified
        validation_entry = validation_report[0]
        self.assertEquals(validation_entry.key,"static_columns_missing")
        self.assertEquals(validation_entry.value,['X1'])

    def test_false_is_true(self):
        print("Method: test_false_is_true.")
        self.assertTrue(False)

    def test_one_plus_one_equals_two(self):
        print("Method: test_one_plus_one_equals_two.")
        self.assertEqual(1 + 1, 2)
