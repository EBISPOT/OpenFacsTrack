from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import get_template


def index(request):
    return render(request, "track/login.html")


@login_required(login_url="/track/login/")
def upload(request):
    return render(request, "track/upload.html")
