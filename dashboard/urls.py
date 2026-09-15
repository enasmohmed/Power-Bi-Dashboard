from django.urls import path

from .views import HomeView, workbook_api, workbook_edit_api

app_name = "dashboard"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("api/workbook/", workbook_api, name="workbook_api"),
    path("api/workbook/edit/", workbook_edit_api, name="workbook_edit"),
]
