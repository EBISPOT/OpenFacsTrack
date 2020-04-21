from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponseRedirect
from openfacstrack.apps.track.models import Panel


def index(request):
    return HttpResponseRedirect("/track/home/")


def home(request):
    return render(request, "track/index.html")


@login_required(login_url="/track/login/")
def upload(request):
    if request.method == "POST":
        print(request.FILES)
        return HttpResponseRedirect("/track/upload/")
    return render(request, "track/upload.html")


@login_required(login_url="/track/login/")
def panels_view(request):
    panels = Panel.objects.all()
    print(panels)
    return render(request, "track/panels.html", {"panels": panels})


def login(request):
    return render(request, "track/login.html")
