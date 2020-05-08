import numbers
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

import pandas as pd

from openfacstrack.apps.track.models import Parameter, Panel


class Command(BaseCommand):
    help = "Update the Panel and Parameter reference tables from file"

    def add_arguments(self, parser):
        parser.add_argument("filename")
        # parser.add_argument('skiprows')

    def handle(self, *args, **options):
        filename = options["filename"]
        # skiprows = options['skiprows']
        try:
            df_panels = pd.read_excel(filename, skiprows=1)
        except Exception as e:
            print(f"There was a problem loading {filename}. Error was: ")
            raise CommandError(str(e))

        with transaction.atomic():
            # Store panel names in Panel table
            panel_names = [p.upper() for p in df_panels.panel.unique().tolist()]
            panel_names.sort()

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
            for panel_name in panel_names:
                panel, created = Panel.objects.get_or_create(name=panel_name)

                # Create the pseudoparameters for panel
                for param_name, param_values in pseudo_parameters.items():
                    # Name of the pseudoparameter is stored in gating hierarchy
                    gating_hierarchy = f"{panel_name}_{param_name}"
                    parameter, created = Parameter.objects.get_or_create(
                        gating_hierarchy=gating_hierarchy,
                        panel=panel
                    )
                    if created:
                        parameter.data_type = param_values['data_type']
                        parameter.description = param_values['description']
                    parameter.save()

            # Store parameter details
            for index, row in df_panels.iterrows():
                panel = Panel.objects.get(name=row["panel"].upper())
                parameter = Parameter.objects.get_or_create(
                    gating_hierarchy=row["gating hierarchy"], panel=panel
                )[0]

                parameter.internal_name = row["marker string"]
                parameter.public_name = row["public_population_name"]
                # parameter.display_name = row['presented on webpage as'] - unit?
                # parameter.excel_column_name = ???
                # parameter.description = ???
                parameter.is_reference_parameter = False  # Where do we get this ???
                parameter.unit = row["presented on webpage as"]

                parameter.ancestral_population = row["ancestral population"]
                parameter.population_for_counts = row["population for counts"]

                # Datatype is PanelNumeric - numeric from panel results
                parameter.data_type = "PanelNumeric"
                # What is 'ancestral population when preseneted as fraction' ?
                parameter.save()
                #print(parameter)

    def _valid(self, value):
        """Check if a value is valid - not empty, nan or NA"""
        if type(value) != str:
            return False

        value = value.strip().upper()
        if len(value) == 0:
            return False
        elif value == "NA":
            return False

        return True
