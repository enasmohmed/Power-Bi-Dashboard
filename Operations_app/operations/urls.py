from django.urls import path

from .overview_view import OperationsOverviewView, OperationsUploadView

app_name = "operations"

urlpatterns = [
    path("", OperationsOverviewView.as_view(), name="overview"),
    path("upload/", OperationsUploadView.as_view(), name="upload"),
]
