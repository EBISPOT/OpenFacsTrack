import numbers
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

import pandas as pd

from openfacstrack.apps.track.models import (
    Parameter,
    Panel,
)

class Command(BaseCommand):
    help = 'Update the Panel and Parameter reference tables from file'

    def add_arguments(self, parser):
        parser.add_argument('filename')
        #parser.add_argument('skiprows')

    def handle(self, *args, **options):
        filename = options['filename']
        #skiprows = options['skiprows']
        try:
            df_panels = pd.read_excel(filename, skiprows=1)
        except Exception  as e:
            print(f"There was a problem loading {filename}. Error was: ")
            raise CommandError(str(e))
        
        with transaction.atomic():
            # Store panel names in Panel table
            panel_names = [p.upper() for p in df_panels.panel.unique().tolist()]
            panel_names.sort()

            for panel_name in panel_names:
                panel = Panel.objects.get_or_create(name=panel_name)

            # Store parameter details
            for index, row in df_panels.iterrows():
                panel = Panel.objects.get(name=row["panel"].upper())
                parameter = Parameter.objects.get_or_create(
                    gating_hierarchy=row['gating hierarchy'],
                    panel=panel)[0]

                parameter.internal_name = row["marker string"]
                parameter.public_name = row["public_population_name"]
                # parameter.display_name = row['presented on webpage as'] - unit?
                # parameter.excel_column_name = ???
                # parameter.description = ???
                parameter.is_reference_parameter = False  # Where do we get this ???
                parameter.unit = row["presented on webpage as"]
                # What is 'ancestral population when preseneted as fraction' ?
                parameter.save()
                print(parameter)

