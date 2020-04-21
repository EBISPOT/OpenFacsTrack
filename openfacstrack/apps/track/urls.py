"""
track app URL Configuration
"""
from django.conf.urls import url
from django.urls import path, include
from . import views

urlpatterns = [
    path("/", views.index, name="home"),
    path("", views.index, name="home"),
    path("home/", views.home, name="home"),
    path("upload/", views.upload, name="upload"),
    path("panels/", views.panels_view, name="panels"),
    path("login/", views.login, name="login"),
    url(r"^oidc/", include("mozilla_django_oidc.urls")),
]
