# Generated by Django 3.0.3 on 2020-06-03 16:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("track", "0003_auto_20200603_0949"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="patientmetadata", options={"ordering": ["metadata_key__name"]},
        ),
    ]