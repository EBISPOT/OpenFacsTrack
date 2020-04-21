from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt


def index(request):
    return render(request, "track/index.html")


@login_required(login_url="/track/login/")
def upload(request):
    if request.method == "POST":
        print(request.FILES)
        return HttpResponseRedirect("/track/upload/")
    return render(request, "track/upload.html")


def login(request):
    return render(request, "track/login.html")
