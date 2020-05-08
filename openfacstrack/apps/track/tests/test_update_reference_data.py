import os

from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth.models import User

from openfacstrack.apps.track.models import Parameter, Panel

# Create your tests here.

class UpdateReferenceDataTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Get the base directory
        cls.base_dir = os.path.dirname(os.path.realpath(__file__)) 

        # Populate reference data table
        fpath = os.path.join(cls.base_dir, 'test_data','test_reference_data.xlsx')
        call_command('update_panel_parameter_reference_data', fpath)

    def setUp(self):
        pass

    def test_all_panels_created(self):
        """Have we created all the panels in the file?"""

        # Total number of panels
        n_panels = Panel.objects.all().count()
        self.assertEqual(n_panels,3)

        # Test expected panels are present (get_or_create returns
        # false if objects exist already)
        self.assertFalse(Panel.objects.get_or_create(name="P1")[1])
        self.assertFalse(Panel.objects.get_or_create(name="P2")[1])
        self.assertFalse(Panel.objects.get_or_create(name="P6")[1])

    def test_exact_number_of_parameters_present(self):
        """Do we have the expected number of parameters?"""

        # We have should have 19 params in all:
        #   3 panels with 5 pseudo parameters per panel
        #   4 gating heirarchy parameters
        n_parameters = Parameter.objects.all().count()
        self.assertEqual(n_parameters, 19)

    def test_all_parameters_loaded(self):
        """Have we loaded all the parameters in the file?"""

        self._test_all_parameters_loaded(self._get_expected_parameters())


    def test_all_pseudo_parameters_created(self):
        """Have we created all the pseudo parameters for each panel?"""

        pseudo_parameters = {
            "batch": {
                "data_type": "SampleNumeric",
                "description": "Batch panel processed under",
            },
            "date_processed": {
                "data_type": "Date",
                "description": "Date panel processed",
            },
            "operator_1": {
                "data_type": "SampleNumeric",
                "description": "Code for primary operator during processing",
            },
            "operator_2": {
                "data_type": "SampleNumeric",
                "description": "Code for second operator during processing",
            },
            "comments": {
                "data_type": "Text",
                "description": "Comments associated with processing the panel",
            },
        }

        
        for panel in Panel.objects.all():
            for param_name, param_values in pseudo_parameters.items():
                gating_hierarchy = f"{panel.name}_{param_name}"
                parameter, created = Parameter.objects.get_or_create(
                    gating_hierarchy=gating_hierarchy,
                    panel=panel
                )
                # Check parameter already exists
                self.assertFalse(created)

                # Check values of parameter
                self.assertEqual(param_values['data_type'], parameter.data_type)
                self.assertEqual(param_values['description'], parameter.description)

    def test_rerun_updates_not_duplicates(self):
        """On another run of updating parameters no duplicates created"""
        self.setUpTestData()
        self.test_all_panels_created()
        self.test_exact_number_of_parameters_present()
        self.test_all_parameters_loaded()
        self.test_all_pseudo_parameters_created()
        

    def test_new_parameters_added_on_rerun(self):
        """On another run only new parameters are added"""
        
        # Populate reference data table with new file
        fpath = os.path.join(self.base_dir, 'test_data','test_reference_data_overwrite.xlsx')
        call_command('update_panel_parameter_reference_data', fpath)
        
        # Test panels as expected
        n_panels = Panel.objects.all().count()
        self.assertEqual(n_panels,5)

        # Test expected panels are present (get_or_create returns
        # false if objects exist already)
        self.assertFalse(Panel.objects.get_or_create(name="P1")[1])
        self.assertFalse(Panel.objects.get_or_create(name="P2")[1])
        self.assertFalse(Panel.objects.get_or_create(name="P6")[1])
        self.assertFalse(Panel.objects.get_or_create(name="P3")[1])
        self.assertFalse(Panel.objects.get_or_create(name="P5")[1])

        # We have should have 19 params in all:
        #   5 panels with 5 pseudo parameters per panel
        #   7 gating heirarchy parameters
        n_parameters = Parameter.objects.all().count()
        self.assertEqual(n_parameters, 32)

        self._test_all_parameters_loaded(self._get_additional_parameters())
        self.test_all_pseudo_parameters_created()


    def _test_all_parameters_loaded(self, expected_parameters):
        """Private function to do actual test"""
        for gating_hierarchy, expected_parameter in expected_parameters.items():
            parameter, created = Parameter.objects.get_or_create(gating_hierarchy=gating_hierarchy)
            for field, value in expected_parameter.items():
                expected_value = f"{field}:{value}"
                default_value = f"value for {field} not found"
                actual_value = getattr(parameter, field, default_value)
                if field == "panel":
                    actual_value = f"panel:{actual_value.name}"
                elif len(actual_value) == 0:
                    actual_value = f"{field}:"
                else:
                    actual_value = f"{field}:{actual_value}"
                self.assertEqual(expected_value, actual_value)


    def _get_expected_parameters(self):
        """Return parameters expected from loading reference file"""

        return {
            "Time_06/Cells_06/Singlets1_06/Singlets2_06/CD45p_06 | Count":
            {
                "panel": "P6",
                "internal_name": "CD45+",
                "public_name": "CD45_cells",
                "unit": "fraction, counts per ml of blood",
                "ancestral_population": "Time_06/Cells_06/Singlets1_06/Singlets2_06 | Count",
                "population_for_counts": "nan",
                "data_type": "PanelNumeric",
            },
            "Time_01/Cells_01/Singlets1_01/Singlets2_01/Live_01/CD45_01/B_01/Niv_B_01 | Count":
            {
                "panel": "P1",
                "internal_name": "CD45+CD19+CD27-",
                "public_name": "naïve_B_cells",
                "unit": "fraction, counts per ml of blood",
                "ancestral_population": "Time_01/Cells_01/Singlets1_01/Singlets2_01/Live_01/CD45_01/B_01 | Count",
                "population_for_counts": "Time_06/Cells_06/Singlets1_06/Singlets2_06/CD45p_06/Lymphocytes_06 | Count",
                "data_type": "PanelNumeric",
            },
            "Time_02/Cells_02/Singlets1_02/Singlets2_02/Live_02/CD45p_02/T_02/CD8_02/CD8_CD25p_02 | Median (CD25)":
            {
                "panel": "P2",
                "internal_name": "CD45+CD3+CD4-CD8+CD25+MFI",
                "public_name": "CD25_MFI_CD8_cells",
                "unit": "median intensity",
                "ancestral_population": "nan",
                "population_for_counts": "nan",
                "data_type": "PanelNumeric",
            },
            "Time_02/Cells_02/Singlets1_02/Singlets2_02/Live_02/CD45p_02/T_02/CD8_02/CD8_CD45RAn_CCR7p_02 | Count":
            {
                "panel": "P2",
                "internal_name": "CD45+CD3+CD4-CD8+CD45RA-CCR7+",
                "public_name": "central_memory_CD8_cells",
                "unit": "fraction, counts per ml of blood",
                "ancestral_population": "Time_02/Cells_02/Singlets1_02/Singlets2_02/Live_02/CD45p_02/T_02/CD8_02 | Count",
                "population_for_counts": "nan",
                "data_type": "PanelNumeric",
            },

        }

    def _get_additional_parameters(self):
        """Return additional parameters to test appending to existing data"""
        expected_parameters = self._get_expected_parameters()
        expected_parameters["Cells_5/Time_5/Live_5/Live_cells_5/CD3p_5/No_Doublets_5/ab_5/Foxp3n_5/CD8p_5/CD8_CD45RAp_CCR7p_5/S_G2_M_5 | Count"] = {
                "panel": "P5",
                "internal_name": "CD3+No doubletsFoxp3-TCRgd-CD8+CD45RA+CCR7+Ki67+Hoechst+",
                "public_name": "naïve_CD8_S_G2_M_cells",
                "unit": "fraction",
                "ancestral_population": "Cells_5/Time_5/Live_5/Live_cells_5/CD3p_5/No_Doublets_5/ab_5/Foxp3n_5/CD8p_5/CD8_CD45RAp_CCR7p_5 | Count",
                "population_for_counts": "nan",
                "data_type": "PanelNumeric",
        }
        expected_parameters["Time_03/Cells_03/Singlets1_03/Singlets2_03/Live_03 | Count"] = {
                "panel": "P3",
                "internal_name": "Live cells",
                "public_name": "live_cells",
                "unit": "fraction, counts per ml of blood",
                "ancestral_population": "nan",
                "population_for_counts": "nan",
                "data_type": "PanelNumeric",
        }
        expected_parameters["Time_03/Cells_03/Singlets1_03/Singlets2_03/Live_03/CD45p_03 | Count"] = {
                "panel": "P3",
                "internal_name": "CD45+",
                "public_name": "CD45pos_cells",
                "unit": "fraction, counts per ml of blood",
                "ancestral_population": "Time_03/Cells_03/Singlets1_03/Singlets2_03/Live_03 | Count",
                "population_for_counts": "nan",
                "data_type": "PanelNumeric",
        }
        return expected_parameters
