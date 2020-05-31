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

    url(r"^api/v1/patients/(?P<pk>[Pp][0-9]+)?$", views.get_patients, name="get_patients"),
    url(r"^api/v1/samples/(?P<pk>[Pp][0-9]+)?$", views.get_samples, name="get_samples"),
    url(r"^api/v1/samples/(?P<pk>[Pp][0-9]+n[0-9]+)$", views.get_samples, name="get_samples_by_clinical_sample_id"),
    url(r"^api/v1/observations/(?P<pk>[Pp][0-9]+)?$", views.get_observations, name="get_observations"),
    url(r"^api/v1/observations/(?P<pk>[Pp][0-9]+n[0-9]+)$", views.get_observations, name="get_observations_by_clinical_sample_id"),
]
