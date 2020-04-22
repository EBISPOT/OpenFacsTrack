from django.db import models
from openfacstrack.apps.core.models import TimeStampedModel

# OpenFacsTrack Models

# Note: Django will automatically ad a primary key field named id to all
# models unless overridden


class ClinicalSample(TimeStampedModel):

    covid_patient_id = models.TextField()

    def __str__(self):
        return "CovidID:" + self.covid_patient_id

class ClinicalSampleMetadataDict(TimeStampedModel):

    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    notes = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return ", ".join(
            [
                "Metadata Key:" + self.name,
                "Description:" + self.description,
                "notes:" + self.notes,
            ]
        )


class ClinicalSampleMetadata(TimeStampedModel):

    clinical_sample = models.ForeignKey(ClinicalSample, on_delete=models.CASCADE)
    metadata_key = models.ForeignKey(ClinicalSampleMetadataDict, on_delete=models.CASCADE)
    metadata_value = models.CharField(max_length=255)

    def __str__(self):
        return ", ".join(
            [
                "Clinical sample ID:" + self.clinical_sample.covid_patient_id,
                "Metadata Key:" + self.metadata_key.name,
                "Metadata value:" + self.metadata_value,
            ]
        )


class ProcessedSample(TimeStampedModel):

    clinical_sample = models.ForeignKey(ClinicalSample, on_delete=models.CASCADE)

    date_acquired = models.DateField()
    biobank_id = models.CharField(max_length=12)
    n_heparin_tubes = models.IntegerField(blank=True, null=True)
    n_paxgene_tubes = models.IntegerField(blank=True, null=True)
    bleed_time = models.TimeField(blank=True, null=True)
    processed_time = models.TimeField(blank=True, null=True)
    blood_vol = models.FloatField(blank=True, null=True)
    lymph_conc_as_MLNmL = models.FloatField(blank=True, null=True)
    total_lymph = models.FloatField(blank=True, null=True)
    vol_frozen_mL = models.FloatField(blank=True, null=True)
    freeze_time = models.TimeField(blank=True, null=True)
    operator1 = models.CharField(max_length=255)
    operator2 = models.CharField(max_length=255)
    comments = models.TextField()
    real_pbmc_frozen_stock_conc_MLNmL = models.FloatField(blank=True, null=True)

    def __str__(self):
        return ", ".join(
            [
                "Clinical sample ID:" + self.clinical_sample.covid_patient_id,
                "Biobank ID:" + self.biobank_id,
                "Date acquired:" + str(self.date_acquired),
            ]
        )


class StoredSample(TimeStampedModel):

    processed_sample = models.ForeignKey(ProcessedSample, on_delete=models.CASCADE)

    stored_sample_id = models.CharField(max_length=10)
    location = models.CharField(max_length=255)
    type_of_stored_material = models.CharField(max_length=255)
    from_which_tube_type = models.CharField(max_length=255)
    freezer = models.CharField(max_length=255)
    box = models.IntegerField()
    row = models.IntegerField()
    position = models.IntegerField()
    comments = models.TextField()

    def __str__(self):
        return ", ".join(
            [
                "Clinical sample ID:" + self.processed_sample.clinical_sample.covid_patient_id,
                "Biobank ID:" + self.processed_sample.biobank_id,
                "Date acquired:" + self.date_acquired,
                "Stored Sample ID" + self.stored_sample_id,
            ]
        )


class Panel(TimeStampedModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return "Panel name: " + self.name


class PanelMetadata(TimeStampedModel):

    panel = models.ForeignKey(Panel, on_delete=models.CASCADE)
    key = models.CharField(max_length=255)
    value =models.CharField(max_length=255)

    def __str__(self):
        return ", ".join(["Panel name:" + self.panel.name, "Metadata:" + self.name])


class Parameter(TimeStampedModel):

    DATA_TYPE = [("Numeric", "Numeric"), ("Text", "Text")]

    panel = models.ForeignKey(Panel, on_delete=models.CASCADE)

    data_type = models.CharField(max_length=10, choices=DATA_TYPE)
    internal_name = models.CharField(max_length=255)
    public_name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    excel_column_name = models.CharField(max_length=255)
    description = models.TextField()
    is_reference_parameter = models.BooleanField(blank=True, null=True)
    gating_hierarchy = models.TextField()
    unit = models.CharField(max_length=255)

    def __str__(self):
        return ", ".join(
            [
                "Panel name:" + self.panel.name,
                "Parameter:" + self.display_name,
                "Type: " + self.data_type,
                "Internal name:" + self.internal_name,
                "Excel column name:" + self.excel_column_name,
            ]
        )


class DataProcessing(TimeStampedModel):
    processed_sample = models.ForeignKey(ProcessedSample, on_delete=models.CASCADE)
    panel = models.ForeignKey(Panel, on_delete=models.CASCADE)

    fcs_file_name = models.CharField(max_length=255)
    fcs_file_location = models.CharField(max_length=255)
    is_in_FlowRepository = models.BooleanField(blank=True, null=True)
    is_automated_gating_done = models.BooleanField(blank=True, null=True)

    def __str__(self):
        return ", ".join(
            [
                "Clinical sample ID:" + self.processed_sample.clinical_sample.covid_patient_id,
                "Panel name:" + self.panel.name,
                "FCS file:"
                + self.fcs_file_name
                + "(location: "
                + self.fcs_file_location
                + ")",
            ]
        )


class NumericParameter(TimeStampedModel):
    processed_sample = models.ForeignKey(ProcessedSample, on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    value = models.FloatField()

    def __str__(self):
        return ", ".join(
            [
                "Clinical sample ID:" + self.processed_sample.clinical_sample.covid_patient_id,
                "Parameter:" + self.parameter.gating_hierarchy,
                #"Parameter:" + self.parameter.display_name,
                "Value:" + str(self.value),
            ]
        )


class TextParameter(TimeStampedModel):
    processed_sample = models.ForeignKey(ProcessedSample, on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    value = models.TextField()

    def __str__(self):
        return ", ".join(
            [
                "Clinical sample ID:" + self.processed_sample.clinical_sample.covid_patient_id,
                "Parameter:" + self.parameter.display_name,
                "Value:" + self.value,
            ]
        )
