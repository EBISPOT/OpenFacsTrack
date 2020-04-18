"""
track app URL Configuration
"""
from django.conf.urls import url
from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("upload/", views.upload, name="upload"),
    path("login/", views.index, name="index"),
    url(r"^oidc/", include("mozilla_django_oidc.urls")),
]
