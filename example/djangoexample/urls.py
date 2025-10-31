"""
URL configuration for djangoexample project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index),
    path("/with-extra-args", views.with_extra_args),
    path("/missing-specific-args/<str:missing>/<int:in_url>", views.missing_specific_args),
    path("/wrong-type/<int:should_be_int>", views.wrong_type),
    path("/incorrect-view/<int:should_be_int>", views.IncorrectView.as_view()),
    path("/correct-view/<str:should_be_str>", views.CorrectView.as_view()),
]
