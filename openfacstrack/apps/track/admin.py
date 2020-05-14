from django.contrib import admin

# Register your models here.
from openfacstrack.apps.track.models import (
    PanelMetadata,
    Parameter,
    ProcessedSample,
    Patient,
    PatientMetadataDict,
    PatientMetadata,
    StoredSample,
    Panel,
    DataProcessing,
    NumericValue,
    TextValue,
    DateValue,
    UploadedFile,
    ValidationEntry,
)


class PanelMetadataInline(admin.TabularInline):
    model = PanelMetadata


class ParameterInline(admin.TabularInline):
    model = Parameter


class ParameterAdmin(admin.ModelAdmin):
    model = Parameter
    radio_fields = dict([("panel", admin.VERTICAL)])


class PanelAdmin(admin.ModelAdmin):
    # inlines = [PanelMetadataInline, ParameterInline]
    inlines = [ParameterInline]


class ProcessedSampleInline(admin.TabularInline):
    model = ProcessedSample


class PatientMetadataDictInline(admin.TabularInline):
    model = PatientMetadataDict


class PatientMetadataInline(admin.TabularInline):
    model = PatientMetadata


class PatientMetadataDictAdmin(admin.ModelAdmin):
    model = PatientMetadataDict


class PatientMetadataAdmin(admin.ModelAdmin):
    model = PatientMetadata


#    inlines = [PatientMetadataInline,]
#    #inlines = [PatientMetadataInline, PatientMetadataDictInline]


class NumericValueAdmin(admin.ModelAdmin):
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parameter":
            kwargs["queryset"] = Parameter.objects.filter(data_type__exact="Numeric")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class TextValueAdmin(admin.ModelAdmin):
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parameter":
            kwargs["queryset"] = Parameter.objects.filter(data_type__exact="Text")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class DateValueAdmin(admin.ModelAdmin):
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parameter":
            kwargs["queryset"] = Parameter.objects.filter(data_type__exact="Date")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(Patient)
admin.site.register(PatientMetadataDict, PatientMetadataDictAdmin)
# admin.site.register(PatientMetadata, PatientMetadataAdmin)
admin.site.register(PatientMetadata, PatientMetadataAdmin)
admin.site.register(ProcessedSample)
admin.site.register(StoredSample)
admin.site.register(Panel, PanelAdmin)
admin.site.register(PanelMetadata)
admin.site.register(Parameter, ParameterAdmin)
admin.site.register(DataProcessing)
admin.site.register(NumericValue, NumericValueAdmin)
admin.site.register(TextValue, TextValueAdmin)
admin.site.register(DateValue, DateValueAdmin)
admin.site.register(UploadedFile)
admin.site.register(ValidationEntry)
