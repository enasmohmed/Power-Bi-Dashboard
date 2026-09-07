from django.urls import path

from customer import views
from customer.views import CustomerDashboardView, CustomerEditDataView, AddCustomerDataView, SaveUploadedDataView, \
    UploadCustomerDataView

app_name = "customer"

urlpatterns = [
    path('customer_dashboard/', CustomerDashboardView.as_view(), name='customer_dashboard'),
    path('data-entry/', CustomerEditDataView.as_view(), name='data_entry'),

    path('add-customer-data/', AddCustomerDataView.as_view(), name='add_customer_data'),

    path("edit-customer-data/", CustomerEditDataView.as_view(), name="edit_customer_data"),


    # path("upload-data/", UploadCustomerDataView.as_view(), name="upload_customer_data"),
    path("save/", SaveUploadedDataView.as_view(), name="save_uploaded_data"),

    path("upload/", UploadCustomerDataView.as_view(), name="upload_customer_data"),


]
