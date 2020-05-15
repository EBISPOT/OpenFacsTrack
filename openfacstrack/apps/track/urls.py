"""
track app URL Configuration
"""
from django.conf.urls import url
from django.urls import path, include
from . import views

urlpatterns = [
    path("", views.index, name="home"),
    path("home/", views.home, name="home"),
    path("upload/", views.upload, name="upload"),
    path("samples/", views.samples_view, name="samples"),
    path("observations/", views.observations_view, name="observations"),
    path("panels/", views.panels_view, name="panels"),
    path("login/", views.login, name="login"),
    path("export/", views.export_view, name="export"),
    url(r"^oidc/", include("mozilla_django_oidc.urls")),
]
