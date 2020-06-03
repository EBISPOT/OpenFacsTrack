from rest_framework import serializers
from .models import (
    Patient,
    ProcessedSample,
    Result,
    NumericValue,
    TextValue,
    DateValue,
)


class PatientSerializer(serializers.ModelSerializer):
    patient_metadata = serializers.StringRelatedField(many=True)

    class Meta:
        model = Patient
        fields = ("patient_id", "created", "modified", "patient_metadata")


class ProcessedSampleSerializer(serializers.ModelSerializer):
    patient_id = serializers.CharField(source="patient.patient_id", read_only=True)

    class Meta:
        model = ProcessedSample
        # fields = "__all__"
        exclude = (
            "patient",
            "id",
        )


class NumericValueSerializer(serializers.ModelSerializer):
    # parameter = serializers.CharField(source="parameter.gating_hierarchy", read_only=True)
    parameter = serializers.CharField(source="parameter.public_name", read_only=True)
    parameter_type = serializers.CharField(source="parameter.data_type", read_only=True)

    class Meta:
        model = NumericValue
        fields = (
            "parameter",
            "parameter_type",
            "value",
        )


class TextValueSerializer(serializers.ModelSerializer):
    # parameter = serializers.CharField(source="parameter.gating_hierarchy", read_only=True)
    parameter = serializers.CharField(source="parameter.public_name", read_only=True)

    class Meta:
        model = TextValue
        fields = (
            "parameter",
            "value",
        )


class DateValueSerializer(serializers.ModelSerializer):
    # parameter = serializers.CharField(source="parameter.gating_hierarchy", read_only=True)
    parameter = serializers.CharField(source="parameter.public_name", read_only=True)

    class Meta:
        model = DateValue
        fields = (
            "parameter",
            "value",
        )


class ObservationSerializer(serializers.ModelSerializer):
    patient_id = serializers.CharField(
        source="processed_sample.patient.patient_id", read_only=True
    )
    clinical_sample_id = serializers.CharField(
        source="processed_sample.clinical_sample_id", read_only=True
    )
    uploaded_file = serializers.CharField(source="uploaded_file.name", read_only=True)
    panel = serializers.CharField(source="panel.name", read_only=True)
    gating_strategy = serializers.CharField(
        source="gating_strategy.strategy", read_only=True
    )
    fcs_file_name = serializers.CharField(
        source="data_processing.fcs_file_name", read_only=True
    )
    numeric_values = serializers.SerializerMethodField("get_numeric_values")
    date_values = serializers.SerializerMethodField("get_date_values")
    text_values = serializers.SerializerMethodField("get_text_values")

    def get_numeric_values(self, result):
        numeric_values = NumericValue.objects.filter(result=result)
        return NumericValueSerializer(numeric_values, many=True).data

    def get_text_values(self, result):
        text_values = TextValue.objects.filter(result=result)
        return TextValueSerializer(text_values, many=True).data

    def get_date_values(self, result):
        date_values = DateValue.objects.filter(result=result)
        return DateValueSerializer(date_values, many=True).data

    class Meta:
        model = Result
        fields = (
            "patient_id",
            "clinical_sample_id",
            "uploaded_file",
            "panel",
            "gating_strategy",
            "fcs_file_name",
            "created",
            "modified",
            "numeric_values",
            "text_values",
            "date_values",
        )

        # exclude = ("id", "processed_sample", "data_processing",)


class SampleObservationSerializer(ProcessedSampleSerializer):
    results = ObservationSerializer(many=True, read_only=True)

    class Meta:
        model = ProcessedSample
        fields = (
            "clinical_sample_id",
            "date_acquired",
            "biobank_id",
            "n_heparin_tubes",
            "n_paxgene_tubes",
            "bleed_time",
            "processed_time",
            "blood_vol",
            "lymph_conc_as_MLNmL",
            "total_lymph",
            "vol_frozen_mL",
            "freeze_time",
            "comments",
            "real_pbmc_frozen_stock_conc_MLNmL",
            "created",
            "modified",
            "results",
        )
        # exclude = ('id', 'patient',)


class AllDataSerializer(PatientSerializer):
    samples = SampleObservationSerializer(many=True, read_only=True)

    class Meta:
        model = Patient
        fields = (
            "patient_id",
            "created",
            "modified",
            "patient_metadata",
            "samples",
        )
