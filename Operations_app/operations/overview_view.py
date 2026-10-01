from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from .excel_import import import_operations_excel
from .overview_service import build_operations_overview


class OperationsOverviewView(LoginRequiredMixin, TemplateView):
    template_name = "operations/overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_operations_overview(self.request))
        return context


class OperationsUploadView(LoginRequiredMixin, View):
    def post(self, request):
        raw_date = (request.POST.get("effective_date") or "").strip()
        try:
            effective_date = datetime.strptime(raw_date, "%Y-%m-%d").date() if raw_date else timezone.now().date()
        except ValueError:
            effective_date = timezone.now().date()
        uploaded = request.FILES.get("excel_file")
        if not uploaded:
            messages.error(request, "Choose an Excel file first.")
        else:
            ok, message = import_operations_excel(uploaded, effective_date=effective_date)
            if ok:
                messages.success(request, message)
            else:
                messages.error(request, message)
        url = reverse("operations:overview")
        return redirect(f"{url}?day={effective_date.isoformat()}")
