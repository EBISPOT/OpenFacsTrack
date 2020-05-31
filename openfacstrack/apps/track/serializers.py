from rest_framework import serializers
from .models import (
    Patient,
    PatientMetadata,
    ProcessedSample,
    Result,
    NumericValue,
    TextValue,
    DateValue,
)

class PatientMetadataSerializer(serializers.ModelSerializer):
    #metadata_key_name = serializers.RelatedField(source="metadata_key.name", read_only=True)
    metadata_key_name = serializers.CharField(source="metadata_key.name", read_only=True)
    class Meta:
        model = PatientMetadata
        fields = ("metadata_key_name", "metadata_value",)

class PatientSerializer(serializers.ModelSerializer):
    patient_metadata = serializers.SerializerMethodField('get_metadata')
    def get_metadata(self, patient):
        patientmetadata = PatientMetadata.objects.filter(patient=patient)
        return PatientMetadataSerializer(patientmetadata, many=True).data

    class Meta:
        model = Patient
        fields = ("id", "created", "modified", "patient_id", "patient_metadata")


class ProcessedSampleSerializer(serializers.ModelSerializer):
    patient_id = serializers.CharField(source="patient.patient_id", read_only=True)
    class Meta:
        model = ProcessedSample
        fields = "__all__"

class NumericValueSerializer(serializers.ModelSerializer):
    parameter = serializers.CharField(source="parameter.gating_hierarchy", read_only=True)
    parameter_type = serializers.CharField(source="parameter.data_type", read_only=True)
    class Meta:
        model = NumericValue
        fields = ("parameter", "parameter_type", "value",)

class TextValueSerializer(serializers.ModelSerializer):
    parameter = serializers.CharField(source="parameter.gating_hierarchy", read_only=True)
    class Meta:
        model = TextValue
        fields = ("parameter", "value",)

class DateValueSerializer(serializers.ModelSerializer):
    parameter = serializers.CharField(source="parameter.gating_hierarchy", read_only=True)
    class Meta:
        model = DateValue
        fields = ("parameter", "value",)

class ResultSerializer(serializers.ModelSerializer):
    patient_id = serializers.CharField(source="processed_sample.patient.patient_id", read_only=True)
    clinical_sample_id = serializers.CharField(source="processed_sample.clinical_sample_id", read_only=True)
    uploaded_file = serializers.CharField(source="uploaded_file.name", read_only=True)
    panel = serializers.CharField(source="panel.name", read_only=True)
    gating_strategy = serializers.CharField(source="gating_strategy.strategy", read_only=True)
    fcs_file_name = serializers.CharField(source="data_processing.fcs_file_name", read_only=True)
    numeric_values = serializers.SerializerMethodField('get_numeric_values')
    date_values = serializers.SerializerMethodField('get_date_values')
    text_values = serializers.SerializerMethodField('get_text_values')

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
        #fields = (
        #   "created", "modified", "patient_id", "clinical_sample_id",
        #   "uploaded_file_name", "panel_name", "gating_strategy_name",
        #   "fcs_file_name",
        #)
        exclude = ("id", "processed_sample", "data_processing",)
