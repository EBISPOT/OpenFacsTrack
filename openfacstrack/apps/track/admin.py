from django.contrib import admin

# Register your models here.
from openfacstrack.apps.track.models import (
    PanelMetadata,
    Parameter,
    ProcessedSample,
    ClinicalSample,
    ClinicalSampleMetadataDict,
    ClinicalSampleMetadata,
    StoredSample,
    Panel,
    DataProcessing,
    NumericParameter,
    TextParameter,
    UploadedFile,
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
    inlines = [
        ParameterInline,
    ]


class ProcessedSampleInline(admin.TabularInline):
    model = ProcessedSample


class ClinicalSampleMetadataDictInline(admin.TabularInline):
    model = ClinicalSampleMetadataDict


class ClinicalSampleMetadataInline(admin.TabularInline):
    model = ClinicalSampleMetadata


class ClinicalSampleMetadataDictAdmin(admin.ModelAdmin):
    model = ClinicalSampleMetadataDict


class ClinicalSampleMetadataAdmin(admin.ModelAdmin):
    model = ClinicalSampleMetadata


#    inlines = [ClinicalSampleMetadataInline,]
#    #inlines = [ClinicalSampleMetadataInline, ClinicalSampleMetadataDictInline]


class NumericParameterAdmin(admin.ModelAdmin):
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parameter":
            kwargs["queryset"] = Parameter.objects.filter(data_type__exact="Numeric")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class TextParameterAdmin(admin.ModelAdmin):
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "parameter":
            kwargs["queryset"] = Parameter.objects.filter(data_type__exact="Text")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(ClinicalSample)
admin.site.register(ClinicalSampleMetadataDict, ClinicalSampleMetadataDictAdmin)
# admin.site.register(ClinicalSampleMetadata, ClinicalSampleMetadataAdmin)
admin.site.register(ClinicalSampleMetadata, ClinicalSampleMetadataAdmin)
admin.site.register(ProcessedSample)
admin.site.register(StoredSample)
admin.site.register(Panel, PanelAdmin)
admin.site.register(PanelMetadata)
admin.site.register(Parameter, ParameterAdmin)
admin.site.register(DataProcessing)
admin.site.register(NumericParameter, NumericParameterAdmin)
admin.site.register(TextParameter, TextParameterAdmin)
admin.site.register(UploadedFile)
