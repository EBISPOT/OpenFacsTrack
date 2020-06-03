from django.contrib.auth.models import User
from django.db import models
from openfacstrack.apps.core.models import TimeStampedModel

# OpenFacsTrack Models

# Note: Django will automatically ad a primary key field named id to all
# models unless overridden


class Patient(TimeStampedModel):

    patient_id = models.CharField(max_length=10, unique=True)

    class Meta:
        ordering = ['patient_id']

    def __str__(self):
        return "PatientID:" + self.patient_id


class PatientMetadataDict(TimeStampedModel):

    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, null=True)
    notes = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return ", ".join(
            [
                "Metadata Key:" + self.name,
                "Description:" + self.description,
                "notes:" + self.notes,
            ]
        )


class PatientMetadata(TimeStampedModel):
    class Meta:
        unique_together = (("patient", "metadata_key"),)

    patient = models.ForeignKey(Patient, related_name='patient_metadata', on_delete=models.CASCADE)
    metadata_key = models.ForeignKey(PatientMetadataDict, on_delete=models.CASCADE)
    metadata_value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.metadata_key.name}: {self.metadata_value}"


def user_directory_path(instance, filename):
    return "uploads/user_{0}/{1}".format(instance.user.id, filename)


class UploadedFile(TimeStampedModel):
    CONTENT_TYPE = [
        ("PANEL_RESULTS", "Panel results"),
        ("PATIENT_DATA", "Patient data"),
        ("OTHER", "Other"),
    ]
    name = models.CharField(max_length=255)
    user = models.ForeignKey(User, blank=True, on_delete=models.DO_NOTHING)
    description = models.CharField(max_length=255)
    row_number = models.IntegerField(default=0)
    content = models.FileField(blank=True, upload_to=user_directory_path)
    valid_syntax = models.BooleanField(default=True)
    valid_model = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default=None)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE)

    def __str__(self):
        return ", ".join(
            [
                "File name:" + self.name,
                "Uploaded:" + str(self.created),
                "Description:" + self.description,
            ]
        )


class ValidationEntry(TimeStampedModel):
    ENTRY_TYPE = [
        ("INFO", "INFO"),
        ("ERROR", "ERROR"),
        ("WARN", "WARN"),
        ("FATAL", "FATAL"),
    ]
    VALIDATION_TYPE = [("SYNTAX", "SYNTAX"), ("MODEL", "MODEL")]
    subject_file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE)
    entry_type = models.CharField(max_length=12, choices=ENTRY_TYPE, default="INFO")
    validation_type = models.CharField(
        max_length=12, choices=VALIDATION_TYPE, default="SYNTAX"
    )
    key = models.CharField(max_length=240)
    value = models.TextField()

    def __str__(self):
        return ", ".join(
            [
                "File ID:" + str(self.subject_file.id),
                "Key:" + str(self.key),
                "Value:" + str(self.value),
            ]
        )


class ProcessedSample(TimeStampedModel):

    clinical_sample_id = models.CharField(max_length=12, unique=True)
    patient = models.ForeignKey(Patient, related_name='samples', on_delete=models.CASCADE)

    # This is meant to store the date a physical sample was acquired - not
    # the date some of it was processed in a panel. That is stored in the
    # date_values table against the particular panel.
    date_acquired = models.DateField(blank=True, null=True)
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
    # This is to store comments about the sample - not about panel results!
    comments = models.TextField()
    real_pbmc_frozen_stock_conc_MLNmL = models.FloatField(blank=True, null=True)

    class Meta:
        ordering = ['patient__patient_id', 'clinical_sample_id',]

    def __str__(self):
        return ", ".join(
            [
                "Clinical sample ID:" + self.clinical_sample_id,
                "Biobank ID:" + self.biobank_id,
                "Date acquired:" + str(self.date_acquired),
            ]
        )


class StoredSample(TimeStampedModel):

    processed_sample = models.ForeignKey(ProcessedSample, on_delete=models.CASCADE)

    stored_sample_id = models.CharField(max_length=10, unique=True)
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
                "Clinical sample ID:" + self.processed_sample.clinical_sample_id,
                "Biobank ID:" + self.processed_sample.biobank_id,
                "Date acquired:" + self.date_acquired,
                "Stored Sample ID" + self.stored_sample_id,
            ]
        )


class Result(TimeStampedModel):
    class Meta:
        unique_together = (
            "processed_sample",
            "panel",
            "gating_strategy",
            "data_processing",
        )

    processed_sample = models.ForeignKey(ProcessedSample, related_name='results', on_delete=models.CASCADE)
    uploaded_file = models.ForeignKey(
        UploadedFile, related_name='results', on_delete=models.DO_NOTHING, null=True, blank=True
    )
    panel = models.ForeignKey("Panel", related_name='results', on_delete=models.CASCADE)
    gating_strategy = models.ForeignKey(
        "GatingStrategy", related_name='results', blank=True, on_delete=models.DO_NOTHING
    )
    data_processing = models.OneToOneField("DataProcessing", related_name='results', on_delete=models.CASCADE)

    class Meta:
        ordering = [
            'processed_sample__clinical_sample_id', 'panel__name',
            'gating_strategy__strategy',
        ]

    def __str__(self):
        return ", ".join(
            [
                "Clinical sample ID:" + self.processed_sample.clinical_sample_id,
                "Panel:" + self.panel.name,
                "Gating strategy:" + self.gating_strategy.strategy,
                "FCS file name:" + self.data_processing.fcs_file_name,
            ]
        )


class Panel(TimeStampedModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return "Panel name: " + self.name


class PanelMetadata(TimeStampedModel):

    panel = models.ForeignKey(Panel, on_delete=models.CASCADE)
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=255)

    def __str__(self):
        return ", ".join(["Panel name:" + self.panel.name, "Metadata:" + self.name])


class Parameter(TimeStampedModel):

    DATA_TYPE = [
        ("PanelNumeric", "Numeric parameter from panel"),
        ("SampleNumeric", "Numeric metadata from sample"),
        ("DerivedNumeric", "Numeric derived parameter from panel"),
        ("Text", "Text"),
        ("Date", "Date"),
        ("Derived", "Derived"),
        ("Other", "Other"),
    ]

    panel = models.ForeignKey(Panel, on_delete=models.CASCADE)

    data_type = models.CharField(max_length=20, choices=DATA_TYPE)
    internal_name = models.CharField(max_length=255)
    public_name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    excel_column_name = models.CharField(max_length=255)
    description = models.TextField()
    is_reference_parameter = models.BooleanField(blank=True, null=True)
    gating_hierarchy = models.TextField(unique=True)
    unit = models.CharField(max_length=255)
    ancestral_population = models.CharField(max_length=255)
    population_for_counts = models.CharField(max_length=255)

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

    panel = models.ForeignKey(Panel, on_delete=models.CASCADE)

    fcs_file_name = models.CharField(max_length=255, unique=True)
    fcs_file_location = models.CharField(max_length=255)
    is_in_FlowRepository = models.BooleanField(blank=True, null=True)
    # is_automated_gating_done = models.BooleanField(blank=True, null=True)

    def __str__(self):
        return ", ".join(
            [
                "Panel name:" + self.panel.name,
                "FCS file:"
                + self.fcs_file_name
                + "(location: "
                + self.fcs_file_location
                + ")",
            ]
        )


class NumericValue(TimeStampedModel):
    class Meta:
        unique_together = ("result", "parameter")
        ordering = ['parameter__data_type', 'parameter__public_name',]

    result = models.ForeignKey(Result, on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    value = models.FloatField(null=True)

    def __str__(self):
        return ", ".join(
            [
                "Clinical sample ID:" + self.result.processed_sample.clinical_sample_id,
                "Parameter:" + self.parameter.gating_hierarchy,
                # "Parameter:" + self.parameter.display_name,
                "Value:" + str(self.value),
            ]
        )


class TextValue(TimeStampedModel):
    class Meta:
        unique_together = ("result", "parameter")
        ordering = ['parameter__public_name',]

    result = models.ForeignKey(Result, on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    value = models.TextField(null=True)

    def __str__(self):
        return ", ".join(
            [
                "Clinical sample ID:" + self.result.processed_sample.clinical_sample_id,
                "Parameter:" + self.parameter.display_name,
                "Value:" + self.value,
            ]
        )


class DateValue(TimeStampedModel):
    class Meta:
        unique_together = ("result", "parameter")
        ordering = ['parameter__public_name',]

    result = models.ForeignKey(Result, on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    value = models.DateField(null=True)

    def __str__(self):
        return ", ".join(
            [
                "Clinical sample ID:" + self.result.processed_sample.clinical_sample_id,
                "Parameter:" + self.parameter.display_name,
                "Value:" + self.value.strftime("%d/%m/%Y"),
            ]
        )


class GatingStrategy(TimeStampedModel):
    strategy = models.CharField(max_length=100)
