from django.urls import path

from administration.views import (
    DashboardView,
    AdminEditDataView,
    AddAdminDataView,
    UploadAdminDataView,
    SaveUploadedAdminDataView,
)

app_name = "administration"

urlpatterns = [
    path("admin_dashboard/", DashboardView.as_view(), name="admin_dashboard"),
    path("data-entry/", AdminEditDataView.as_view(), name="data_entry"),
    path("add-admin-data/", AddAdminDataView.as_view(), name="add_admin_data"),
    path("admin/edit/", AdminEditDataView.as_view(), name="admin_edit"),
    path("upload/", UploadAdminDataView.as_view(), name="upload_admin_data"),
    path("save/", SaveUploadedAdminDataView.as_view(), name="save_uploaded_admin_data"),
]
