from django.contrib.auth.decorators import login_required
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import F
from django.shortcuts import render, get_object_or_404, get_list_or_404
from django.http import HttpResponseRedirect, HttpResponse

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from openfacstrack.apps.track.forms import ConfirmFileForm
from openfacstrack.apps.track.models import (
    Panel,
    ProcessedSample,
    NumericValue,
    TextValue,
    DateValue,
    Parameter,
    UploadedFile,
    Result,
    GatingStrategy,
    Patient,
    PatientMetadata,
)
from openfacstrack.apps.track.serializers import (
    PatientSerializer,
    ProcessedSampleSerializer,
    ResultSerializer,
)

import json

from openfacstrack.apps.track.utils import ClinicalSampleFile, PatientFile


def index(request):
    return HttpResponseRedirect("/track/home/")


def home(request):
    return render(request, "track/index.html")


@login_required(login_url="/track/login/")
def upload(request):
    if request.method == "POST":
        file_type = None
        if request.FILES.get("observationsFile"):
            file_type = "observationsFile"
        elif request.FILES.get("patientsFile"):
            file_type = "patientsFile"
        if file_type:
            gating_strategy = GatingStrategy.objects.get_or_create(strategy="manual")[0]
            gating_strategy.save()
            print(f"Gating strategy id = {gating_strategy.id}")
            file_name = request.FILES[file_type].name
            file_contents = request.FILES.get(file_type)
            if file_type == "observationsFile":
                uploaded_file = ClinicalSampleFile(
                    file_name,
                    file_contents,
                    user=request.user,
                    gating_strategy=gating_strategy,
                )
            else:
                uploaded_file = PatientFile(file_name, file_contents, user=request.user)
            validation_errors = uploaded_file.validate()
            if validation_errors:
                validation_report = {
                    "info": [
                        error
                        for error in validation_errors
                        if error.entry_type == "INFO"
                    ],
                    "warn": [
                        error
                        for error in validation_errors
                        if error.entry_type == "WARN"
                    ],
                    "error": [
                        error
                        for error in validation_errors
                        if error.entry_type == "ERROR"
                    ],
                }
            else:
                validation_report = {}
            upload_report = {}
            if not uploaded_file.upload_file.valid_syntax:
                print("Validation errors, aborting upload:")
                print(validation_errors)
            else:
                print("trying upload")
                try:
                    upload_report = uploaded_file.upload(dry_run=True)
                    upload_errors = {
                        "info": [
                            error
                            for error in upload_report["validation"]
                            if error.entry_type == "INFO"
                        ],
                        "warn": [
                            error
                            for error in upload_report["validation"]
                            if error.entry_type == "WARN"
                        ],
                        "error": [
                            error
                            for error in upload_report["validation"]
                            if error.entry_type == "ERROR"
                        ],
                    }
                    upload_report["validation"] = upload_errors
                except Exception as e:
                    print("upload failed")
                    upload_report["status"] = "failed"
            confirm_file_form = ConfirmFileForm(
                initial={"file_id": uploaded_file.upload_file.id}
            )
            return render(
                request,
                "track/upload.html",
                {
                    "uploaded": True,
                    "syntax_report": validation_report,
                    "model_report": upload_report,
                    "form": confirm_file_form,
                },
            )
        elif ConfirmFileForm(request.POST).data.get("file_id"):
            gating_strategy = GatingStrategy.objects.get_or_create(strategy="manual")[0]
            uploaded_file = UploadedFile.objects.get(
                pk=ConfirmFileForm(request.POST).data.get("file_id")
            )
            if uploaded_file.content_type == "PANEL_RESULTS":
                uploaded_file = ClinicalSampleFile(
                    user=request.user,
                    uploaded_file=uploaded_file,
                    gating_strategy=gating_strategy,
                )
            else:
                uploaded_file = PatientFile(
                    user=request.user, uploaded_file=uploaded_file
                )
            uploaded_file.validate()
            uploaded_file.upload()
            return render(request, "track/upload.html", {"upload_status": "success"})
    return render(request, "track/upload.html")


@login_required(login_url="/track/login/")
def panels_view(request):
    panels = Panel.objects.all().order_by("name")
    return render(request, "track/panels.html", {"panels": panels})


@login_required(login_url="/track/login/")
def samples_view(request):
    samples = (
        ProcessedSample.objects.all()
        .annotate(patient_covid_id=F("patient__patient_id"))
        .distinct("patient_covid_id")
        .order_by("patient_covid_id")
        .values()
    )
    for sample in samples:
        panels_by_sample = Result.objects.filter(processed_sample=sample["id"]).values(
            "panel__name", "created"
        )
        for panel in panels_by_sample:
            sample[panel["panel__name"]] = panel["created"]
    panel_names = [
        panel["name"] for panel in Panel.objects.values("name").order_by("name")
    ]
    table_json = json.dumps(
        list(samples), sort_keys=True, indent=1, cls=DjangoJSONEncoder
    )
    return render(
        request,
        "track/clinical_samples.html",
        {"panels": panel_names, "table_json": table_json},
    )


@login_required(login_url="/track/login/")
def observations_view(request):
    patients = Patient.objects.all().order_by("patient_id")
    if request.GET.get("patient") is None:
        return render(
            request,
            "track/observations.html",
            {"patients": patients, "selected": None, "numeric": []},
        )
    else:
        patient_id = request.GET.get("patient")
        numeric = (
            NumericValue.objects.all()
            .annotate(patient_id=F("result__processed_sample__patient__id"))
            .annotate(panel_name=F("result__panel__name"))
            .filter(patient_id=patient_id)
        )
        return render(
            request,
            "track/observations.html",
            {
                "patients": patients,
                "selected": Patient.objects.get(id=patient_id),
                "numeric": numeric,
            },
        )


def export_view(request):
    patients = list(Patient.objects.all().values("id", "patient_id"))
    for patient in patients:
        patient_id = patient["id"]
        patient_metadata = (
            PatientMetadata.objects.filter(patient=patient_id)
            .annotate(column_name=F("metadata_key__name"))
            .all()
            .values()
        )
        for metadata_item in list(patient_metadata):
            patient[metadata_item["column_name"]] = metadata_item["metadata_value"]

        patient["samples"] = list(
            ProcessedSample.objects.filter(patient=patient_id).values()
        )

        for sample in patient["samples"]:
            sample_id = sample["id"]
            sample_results = (
                Result.objects.filter(processed_sample=sample_id)
                .annotate(panel_name=F("panel__name"))
                .annotate(gating_strategy_name=F("gating_strategy__strategy"))
                .values()
            )
            sample["panels"] = list(sample_results)
            for result in sample["panels"]:
                result_id = result["id"]
                result["observations"] = list(
                    NumericValue.objects.filter(result=result_id)
                    .annotate(parameter_name=F("parameter__public_name"))
                    .values()
                )
                result["observations"] += list(
                    TextValue.objects.filter(result=result_id)
                    .annotate(parameter_name=F("parameter__public_name"))
                    .values()
                )
                result["observations"] += list(
                    DateValue.objects.filter(result=result_id)
                    .annotate(parameter_name=F("parameter__public_name"))
                    .values()
                )

    return HttpResponse(
        json.dumps(patients, indent=1, cls=DjangoJSONEncoder),
        content_type="application/json",
    )


def login(request):
    return render(request, "track/login.html")

@api_view(['GET',])
def get_patients(request, pk=None):
    """Get details of all patients or specified patient"""
    
    if pk is None:
        patients = Patient.objects.all()
        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data)
    else:
        patient = get_object_or_404(Patient, patient_id=pk)    
        serializer = PatientSerializer(patient)
        return Response(serializer.data)

@api_view(['GET',])
def get_samples(request, pk=None):
    """Get details of all samples (excluding results) or specified sample"""
    
    if pk is None:
        samples = ProcessedSample.objects.all()
        serializer = ProcessedSampleSerializer(samples, many=True)
    elif pk.find('n') >= 0:
        sample = get_object_or_404(ProcessedSample, clinical_sample_id=pk)    
        serializer = ProcessedSampleSerializer(sample)

    else:
        samples = get_list_or_404(ProcessedSample, patient__patient_id=pk)    
        serializer = ProcessedSampleSerializer(samples, many=True)
    return Response(serializer.data)

@api_view(['GET',])
def get_observations(request, pk=None):
    """Get all results or specific results by patient_id or clinical_sample_id"""

    if pk is None:
        results = Result.objects.all()
        serializer = ResultSerializer(results, many=True)
    elif pk.find('n') >= 0:
        results = get_list_or_404(Result, processed_sample__clinical_sample_id=pk)
        serializer = ResultSerializer(results, many=True)
    else:
        results = get_list_or_404(Result, processed_sample__patient__patient_id=pk)
        serializer = ResultSerializer(results, many=True)
    return Response(serializer.data)
