from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt

from openfacstrack.apps.track.utils import ClinicalSampleFile

def index(request):
    return render(request, "track/index.html")


@login_required(login_url="/track/login/")
def upload(request):
    if request.method == "POST":
        filepath = request.FILES.get('file')
        clinical_sample_file = ClinicalSampleFile(filepath)
        validation_errors = clinical_sample_file.validate()
        if validation_errors:
            print("Validation errors, aborting upload:")
            print(validation_errors)
        else:
            try:
                upload_issues = clinical_sample_file.upload()
                print("Uploaded file. Issues: ")
                print(upload_issues)
            except Exception as e:
                print("File not uploaded:")
                print(str(e))
        return HttpResponseRedirect("/track/upload/")
    return render(request, "track/upload.html")


def login(request):
    return render(request, "track/login.html")
