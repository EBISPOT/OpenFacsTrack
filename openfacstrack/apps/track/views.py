from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponseRedirect
from openfacstrack.apps.track.models import (
    Panel,
    ProcessedSample,
    NumericParameter,
    Parameter,
)
import json

from openfacstrack.apps.track.utils import ClinicalSampleFile


def index(request):
    return HttpResponseRedirect("/track/home/")


def home(request):
    return render(request, "track/index.html")


@login_required(login_url="/track/login/")
def upload(request):
    if request.method == "POST":
        file_name = request.FILES["file"].name
        file_contents = request.FILES.get("file")
        clinical_sample_file = ClinicalSampleFile(file_name, file_contents)
        validation_errors = clinical_sample_file.validate()
        if validation_errors:
            print("Validation errors, aborting upload:")
            print(validation_errors)
        else:
            try:
                upload_report = clinical_sample_file.upload(commit_with_issues=True)
                print("Uploaded file. Report: ")
                print(upload_report)
            except Exception as e:
                print("File not uploaded:")
                print(str(e))
        return HttpResponseRedirect("/track/upload/")
    return render(request, "track/upload.html")


@login_required(login_url="/track/login/")
def panels_view(request):
    panels = Panel.objects.all().order_by("name")
    return render(request, "track/panels.html", {"panels": panels})


@login_required(login_url="/track/login/")
def samples_view(request):
    samples = ProcessedSample.objects.all().order_by("date_acquired")
    return render(request, "track/clinical_samples.html", {"samples": samples})


@login_required(login_url="/track/login/")
def observations_view(request):
    parameters = Parameter.objects.all().order_by("panel__name")
    if request.GET.get("parameter") is None:
        return render(
            request,
            "track/observations.html",
            {"parameters": parameters, "selected": None, "numeric": []},
        )
    else:
        numeric = NumericParameter.objects.filter(
            parameter=request.GET.get("parameter")
        )
        return render(
            request,
            "track/observations.html",
            {
                "parameters": parameters,
                "selected": Parameter.objects.get(id=request.GET.get("parameter")),
                "numeric": numeric,
            },
        )


def login(request):
    return render(request, "track/login.html")
