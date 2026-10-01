"""Import the Operations overview sheet (Da-tamer / Sheet1)."""
from datetime import datetime, timedelta, timezone as dt_utc

import pandas as pd
from django.utils import timezone

from .models import CapacityVolume, WarehouseAccountOverview, WarehouseImportLog


def _day_range(target_date):
    start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=dt_utc.utc)
    return start, start + timedelta(days=1)


def _excel_metric(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, str):
        text = val.strip()
        if not text or text in ("-", "—", "nan", "NaN"):
            return None
        if text.lower() in ("no data", "nodata", "n/a", "na", "#n/a"):
            return None
        try:
            return int(float(text.replace(",", "")))
        except (ValueError, TypeError):
            return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _excel_raw(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    text = str(val).strip()
    if not text or text.lower() in ("nan", "none", "<nan>"):
        return None
    return text


def import_operations_excel(uploaded_file, effective_date=None, sheet_name=None):
    """Replace one day's warehouse rows from an Excel file. Returns (ok, message)."""
    name = getattr(uploaded_file, "name", "") or ""
    if not name.lower().endswith((".xlsx", ".xls")):
        return False, "Please upload an Excel file (.xlsx or .xls) only."

    if effective_date is None:
        effective_date = timezone.now().date()

    try:
        workbook = pd.ExcelFile(uploaded_file, engine="openpyxl")
        sheet_names = workbook.sheet_names
    except Exception as exc:
        return False, f"Could not read file: {exc}"

    chosen = (sheet_name or "").strip() or None
    if not chosen:
        folded = {sheet.lower(): sheet for sheet in sheet_names}
        chosen = folded.get("da-tamer") or folded.get("sheet1") or (sheet_names[0] if sheet_names else None)
    if not chosen or chosen not in sheet_names:
        available = ", ".join(sheet_names)
        return False, f"Sheet «{chosen or '(not set)'}» not found. Available sheets: {available}"

    frame = pd.read_excel(workbook, sheet_name=chosen)
    if frame.empty or len(frame) < 1:
        return False, "The selected sheet is empty or has no data."

    frame.columns = [str(column).strip() for column in frame.columns]
    columns = {}
    for column in frame.columns:
        key = column.lower().strip().replace(" ", "_").replace("-", "_")
        if not columns.get("warehouse") and (
            key in ("warehouse", "whs", "wh") or "warehouse" in key
        ):
            columns["warehouse"] = column
        elif key == "account" or (not columns.get("account") and "account" in key):
            columns["account"] = column
        elif not columns.get("inbound") and "inbound" in key:
            columns["inbound"] = column
        elif not columns.get("outbound") and "outbound" in key:
            columns["outbound"] = column
        elif not columns.get("clearance") and ("clearance" in key or "clear" in key or key == "cleamce"):
            columns["clearance"] = column
        elif not columns.get("capacity") and "capacity" in key:
            columns["capacity"] = column
        elif not columns.get("occupied_location") and (
            "occupied" in key or "location" in key or "occupled" in key
        ):
            columns["occupied_location"] = column
        elif not columns.get("transportation") and ("transport" in key or key == "transportaion"):
            columns["transportation"] = column
        elif not columns.get("pods") and key in ("pods", "pod"):
            columns["pods"] = column

    if "warehouse" not in columns or "account" not in columns:
        return False, "The sheet must contain at least two columns: Warehouse (or WHs) and Account."

    warehouse_column = columns["warehouse"]
    frame[warehouse_column] = frame[warehouse_column].replace("", None).ffill().fillna("")
    capacity_column = columns.get("capacity")
    if capacity_column and capacity_column in frame.columns:
        frame[capacity_column] = frame[capacity_column].replace("", None).replace("-", None).ffill()

    start, end = _day_range(effective_date)
    WarehouseAccountOverview.objects.filter(created_at__gte=start, created_at__lt=end).delete()
    effective_datetime = datetime.combine(effective_date, datetime.min.time()).replace(tzinfo=dt_utc.utc)

    created = 0
    for _, row in frame.iterrows():
        warehouse = str(row.get(columns["warehouse"], "") or "").strip()
        account = str(row.get(columns["account"], "") or "").strip()
        if not warehouse and not account:
            continue
        if account.lower() == "account" or warehouse.lower() in ("whs", "warehouse", "account"):
            continue
        WarehouseAccountOverview.objects.create(
            warehouse=warehouse or "—",
            account=account or "—",
            capacity=_excel_metric(row.get(columns.get("capacity"))),
            capacity_raw=_excel_raw(row.get(columns.get("capacity"))),
            clearance=_excel_metric(row.get(columns.get("clearance"))),
            clearance_raw=_excel_raw(row.get(columns.get("clearance"))),
            inbound=_excel_metric(row.get(columns.get("inbound"))),
            inbound_raw=_excel_raw(row.get(columns.get("inbound"))),
            outbound=_excel_metric(row.get(columns.get("outbound"))),
            outbound_raw=_excel_raw(row.get(columns.get("outbound"))),
            transportation=_excel_metric(row.get(columns.get("transportation"))),
            transportation_raw=_excel_raw(row.get(columns.get("transportation"))),
            pods=_excel_metric(row.get(columns.get("pods"))),
            pods_raw=_excel_raw(row.get(columns.get("pods"))),
            occupied_location=_excel_metric(row.get(columns.get("occupied_location"))),
            occupied_location_raw=_excel_raw(row.get(columns.get("occupied_location"))),
            created_at=effective_datetime,
        )
        created += 1

    parts = [f"Imported {created} row(s) from sheet «{chosen}»."]
    if "Capacity-volume" in sheet_names:
        capacity_frame = pd.read_excel(workbook, sheet_name="Capacity-volume")
        capacity_frame.columns = [str(column).strip() for column in capacity_frame.columns]
        warehouse_col = None
        capacity_col = None
        for column in capacity_frame.columns:
            key = column.lower().strip().replace(" ", "_").replace("-", "_")
            if warehouse_col is None and (key in ("warehouse", "whs", "wh") or "warehouse" in key):
                warehouse_col = column
            if capacity_col is None and "capacity" in key:
                capacity_col = column
        if warehouse_col and capacity_col:
            CapacityVolume.objects.all().delete()
            capacity_count = 0
            for _, row in capacity_frame.iterrows():
                warehouse = str(row.get(warehouse_col, "") or "").strip()
                if not warehouse:
                    continue
                capacity = _excel_metric(row.get(capacity_col)) or 0
                CapacityVolume.objects.create(warehouse=warehouse, capacity=capacity)
                capacity_count += 1
            parts.append(f"Imported {capacity_count} capacity row(s).")

    WarehouseImportLog.objects.create(effective_date=effective_date)
    return True, " ".join(parts)
