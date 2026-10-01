"""Build the Operations overview page from admin-imported warehouse rows."""
from datetime import datetime, timedelta

from django.db.models import Sum
from django.utils import timezone

from .models import WarehouseAccountOverview, WarehouseImportLog


def _to_number(val):
    if val is None:
        return 0.0
    if isinstance(val, bool):
        return float(val)
    if isinstance(val, (int, float)):
        try:
            number = float(val)
        except (TypeError, ValueError):
            return 0.0
        if number != number or number in (float("inf"), float("-inf")):
            return 0.0
        return number
    try:
        text = str(val).strip()
        if not text or text.lower() in ("nan", "none", "<nan>"):
            return 0.0
        return float(text.replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _as_int(val):
    if val is None:
        return None
    try:
        return int(round(float(val)))
    except (TypeError, ValueError):
        return None


def _is_bad_float(val):
    if isinstance(val, float) and val != val:
        return True
    if isinstance(val, str) and val.strip().lower() == "nan":
        return True
    return False


def _display_metric(row, raw_field, num_field):
    raw_val = row.get(raw_field)
    if raw_val is not None and str(raw_val).strip() != "":
        return str(raw_val)
    return row.get(num_field)


def _display_pods(row):
    raw_val = row.get("pods_raw")
    if raw_val is not None and str(raw_val).strip() != "":
        text = str(raw_val).strip().replace(",", "")
        try:
            return int(round(float(text)))
        except (TypeError, ValueError):
            return str(raw_val).strip()
    return _as_int(row.get("pods"))


def build_operations_overview(request):
    wh_filter = (request.GET.get("wh") or request.GET.get("warehouse") or "").strip()
    selected_warehouse = wh_filter or None
    acc_filter = (request.GET.get("acc") or request.GET.get("account") or "").strip()
    selected_account = acc_filter or None

    today = timezone.now().date()
    available_dates = list(
        WarehouseAccountOverview.objects.dates("created_at", "day", order="DESC")
    )
    available_dates_set = set(available_dates)
    last_import = WarehouseImportLog.objects.order_by("-imported_at").first()
    last_import_date = last_import.effective_date if last_import else None
    last_data_date = (
        last_import_date
        if last_import_date and last_import_date in available_dates_set
        else None
    ) or (available_dates[0] if available_dates else today)

    raw_day = (request.GET.get("day") or "").strip()
    raw_day_lower = raw_day.lower()
    date_filter = None
    selected_day_value = raw_day
    if raw_day_lower == "today":
        date_filter = today
        selected_day_value = raw_day_lower
    elif raw_day_lower == "yesterday":
        date_filter = today - timedelta(days=1)
        selected_day_value = raw_day_lower
    elif raw_day_lower == "day_before_yesterday":
        date_filter = today - timedelta(days=2)
        selected_day_value = raw_day_lower
    elif raw_day:
        try:
            date_filter = datetime.strptime(raw_day, "%Y-%m-%d").date()
            selected_day_value = raw_day
        except ValueError:
            date_filter = None
    if date_filter is None:
        date_filter = last_data_date
        selected_day_value = last_data_date.strftime("%Y-%m-%d")
    if date_filter not in available_dates_set and available_dates:
        date_filter = last_data_date
        selected_day_value = last_data_date.strftime("%Y-%m-%d")

    base_qs = WarehouseAccountOverview.objects.filter(created_at__date=date_filter)
    if selected_warehouse:
        base_qs = base_qs.filter(warehouse=selected_warehouse)
    all_account_names = list(
        base_qs.order_by("account").values_list("account", flat=True).distinct()
    )

    qs = base_qs
    if selected_account:
        qs = qs.filter(account=selected_account)
    raw_rows = list(
        qs.values(
            "warehouse",
            "account",
            "capacity",
            "clearance",
            "inbound",
            "outbound",
            "transportation",
            "pods",
            "occupied_location",
            "capacity_raw",
            "clearance_raw",
            "inbound_raw",
            "outbound_raw",
            "transportation_raw",
            "pods_raw",
            "occupied_location_raw",
        )
    )
    rows = []
    for row in raw_rows:
        if _is_bad_float(row.get("capacity")) or _is_bad_float(row.get("occupied_location")):
            continue
        warehouse_name = str(row.get("warehouse") or "").strip()
        account_name = str(row.get("account") or "").strip()
        if not warehouse_name and not account_name:
            continue
        rows.append(row)

    totals_agg = qs.aggregate(
        total_inbound=Sum("inbound"),
        total_outbound=Sum("outbound"),
        total_clearance=Sum("clearance"),
        total_transportation=Sum("transportation"),
        total_pods=Sum("pods"),
    )
    totals = {
        "total_inbound": _as_int(totals_agg["total_inbound"]),
        "total_outbound": _as_int(totals_agg["total_outbound"]),
        "total_clearance": _as_int(totals_agg["total_clearance"]),
        "total_transportation": _as_int(totals_agg["total_transportation"]),
        "total_pods": _as_int(totals_agg["total_pods"]),
    }

    warehouse_names = []
    seen_warehouses = set()
    account_names = []
    seen_accounts = set()
    for row in rows:
        warehouse_name = str(row.get("warehouse") or "").strip()
        account_name = str(row.get("account") or "").strip()
        if warehouse_name and warehouse_name not in seen_warehouses:
            seen_warehouses.add(warehouse_name)
            warehouse_names.append(warehouse_name)
        if account_name and account_name not in seen_accounts:
            seen_accounts.add(account_name)
            account_names.append(account_name)

    by_warehouse = {}
    by_account = {}
    for row in rows:
        warehouse_name = str(row.get("warehouse") or "").strip()
        account_name = str(row.get("account") or "").strip()
        by_warehouse.setdefault(
            warehouse_name,
            {"inbound": 0.0, "outbound": 0.0, "clearance": 0.0, "transportation": 0.0, "pods": 0.0},
        )
        by_account.setdefault(
            account_name,
            {"inbound": 0.0, "outbound": 0.0, "clearance": 0.0, "transportation": 0.0, "pods": 0.0},
        )
        for metric in ("inbound", "outbound", "clearance", "transportation", "pods"):
            by_warehouse[warehouse_name][metric] += _to_number(row.get(metric))
            by_account[account_name][metric] += _to_number(row.get(metric))

    def pick_lowest_positive(items):
        positive = [item for item in items if _to_number(item[1]) > 0]
        if not positive:
            return None, None
        positive.sort(key=lambda item: (_to_number(item[1]), item[0]))
        return positive[0]

    def high_low(bucket, metric):
        items = [(name, bucket[name][metric]) for name in bucket if str(name).strip()]
        if not items:
            return None, None, None, None
        items.sort(key=lambda item: (_to_number(item[1]), item[0]), reverse=True)
        high_name, high_value = items[0]
        low_name, low_value = pick_lowest_positive(items)
        return high_name, high_value, low_name, low_value

    def merge_metric(metric):
        high_wh, high_wh_value, low_wh, low_wh_value = high_low(by_warehouse, metric)
        high_acc, high_acc_value, low_acc, low_acc_value = high_low(by_account, metric)
        return {
            "high_warehouse": high_wh,
            "high_warehouse_value": _as_int(high_wh_value) or 0,
            "low_warehouse": low_wh,
            "low_warehouse_value": _as_int(low_wh_value),
            "high_account": high_acc,
            "high_account_value": _as_int(high_acc_value) or 0,
            "low_account": low_acc,
            "low_account_value": _as_int(low_acc_value),
        }

    card_high_low = {
        metric: merge_metric(metric)
        for metric in ("clearance", "inbound", "outbound", "transportation", "pods")
    }

    table_rows = []
    previous_warehouse = None
    group_count = 0
    row_bg = "light"
    account_badges = {}
    badge_index = 0
    for row in rows:
        item = dict(row)
        account_name = str(item.get("account") or "").strip()
        if account_name not in account_badges:
            account_badges[account_name] = "pink" if badge_index % 2 == 0 else "gray"
            badge_index += 1
        item["account_badge"] = account_badges[account_name]
        warehouse_name = item.get("warehouse") or ""
        if warehouse_name != previous_warehouse:
            if group_count:
                _close_group(table_rows, group_count, previous_warehouse)
            if previous_warehouse is not None:
                row_bg = "white" if row_bg == "light" else "light"
            previous_warehouse = warehouse_name
            group_count = 1
        else:
            group_count += 1
        item["row_bg"] = row_bg
        item["capacity_display"] = _display_metric(item, "capacity_raw", "capacity")
        item["clearance_display"] = _display_metric(item, "clearance_raw", "clearance")
        item["inbound_display"] = _display_metric(item, "inbound_raw", "inbound")
        item["outbound_display"] = _display_metric(item, "outbound_raw", "outbound")
        item["transportation_display"] = _display_metric(item, "transportation_raw", "transportation")
        item["pods_display"] = _display_pods(item)
        item["occupied_location_display"] = _display_metric(
            item, "occupied_location_raw", "occupied_location"
        )
        capacity = item.get("capacity")
        occupied = item.get("occupied_location")
        if capacity is not None and capacity > 0 and occupied is not None:
            item["utilization_pct"] = round(occupied / capacity * 100, 1)
        else:
            item["utilization_pct"] = None
        table_rows.append(item)
    if group_count:
        _close_group(table_rows, group_count, previous_warehouse)

    all_warehouse_names = []
    seen_all = set()
    for warehouse_name in WarehouseAccountOverview.objects.values_list("warehouse", flat=True):
        name = (warehouse_name or "").strip()
        if name and name not in seen_all:
            seen_all.add(name)
            all_warehouse_names.append(name)

    trend_base_date = date_filter or today
    yesterday_date = trend_base_date - timedelta(days=1)
    day_before_date = trend_base_date - timedelta(days=2)

    rows_by_warehouse = {}
    for row in rows:
        warehouse_name = str(row.get("warehouse") or "").strip()
        rows_by_warehouse.setdefault(warehouse_name, []).append(row)

    warehouse_capacity_cards = []
    for warehouse_name in warehouse_names:
        group = rows_by_warehouse.get(warehouse_name) or []
        if not group:
            continue
        capacity = group[0].get("capacity")
        occupied_values = [
            item.get("occupied_location")
            for item in group
            if item.get("occupied_location") is not None
        ]
        if capacity is not None and capacity > 0 and occupied_values:
            utilization = int(round(sum(occupied_values) / capacity * 100))
        else:
            utilization = 0
        ranked = sorted(
            [item for item in group if item.get("occupied_location") is not None],
            key=lambda item: item.get("occupied_location") or 0,
            reverse=True,
        )
        highest = ranked[0] if ranked else {}
        positive = [item for item in group if (item.get("occupied_location") or 0) > 0]
        lowest = min(positive, key=lambda item: item.get("occupied_location") or 0) if positive else {}
        util_today = _utilization_for_date(warehouse_name, trend_base_date)
        util_yesterday = _utilization_for_date(warehouse_name, yesterday_date)
        util_before = _utilization_for_date(warehouse_name, day_before_date)
        warehouse_capacity_cards.append(
            {
                "warehouse": warehouse_name,
                "utilization_pct": utilization,
                "highest_account_name": str(highest.get("account") or "").strip() or "—",
                "highest_account_count": highest.get("occupied_location") or 0,
                "lowest_account_name": str(lowest.get("account") or "").strip() or "—",
                "lowest_account_count": (lowest.get("occupied_location") or 0) if lowest else None,
                "trend_util": _trend_points(util_today, util_yesterday, util_before),
            }
        )

    trend_totals = {
        metric: _trend_metric(*_metric_series(metric, selected_warehouse, selected_account, trend_base_date, yesterday_date, day_before_date))
        for metric in ("clearance", "inbound", "outbound", "transportation", "pods")
    }

    return {
        "page": "operations",
        "totals": totals,
        "trend_totals": trend_totals,
        "table_rows": table_rows,
        "warehouse_names": warehouse_names,
        "account_names": account_names,
        "selected_warehouse": selected_warehouse,
        "selected_account": selected_account,
        "all_warehouse_names": all_warehouse_names,
        "all_account_names": all_account_names,
        "selected_day": selected_day_value,
        "selected_date": date_filter,
        "available_dates": available_dates,
        "today_date": trend_base_date,
        "yesterday_date": yesterday_date,
        "day_before_yesterday_date": day_before_date,
        "card_high_low": card_high_low,
        "warehouse_capacity_cards": warehouse_capacity_cards,
    }


def _close_group(table_rows, group_count, warehouse_name):
    first = len(table_rows) - group_count
    group_capacity = table_rows[first].get("capacity_display")
    for index in range(first, len(table_rows)):
        if index == first:
            table_rows[index]["warehouse_rowspan"] = group_count
            table_rows[index]["warehouse_value"] = warehouse_name
            table_rows[index]["capacity_rowspan"] = group_count
            table_rows[index]["capacity_value"] = group_capacity
        else:
            table_rows[index]["warehouse_rowspan"] = 0
            table_rows[index]["capacity_rowspan"] = 0


def _utilization_for_date(warehouse_name, day):
    group = list(
        WarehouseAccountOverview.objects.filter(
            warehouse=warehouse_name, created_at__date=day
        ).values("capacity", "occupied_location")
    )
    if not group:
        return 0
    capacity = group[0].get("capacity")
    occupied_values = [
        item.get("occupied_location")
        for item in group
        if item.get("occupied_location") is not None
    ]
    if capacity is not None and capacity > 0 and occupied_values:
        return int(round(sum(occupied_values) / capacity * 100))
    return 0


def _metric_series(metric, warehouse, account, today, yesterday, day_before):
    def total_for(day):
        query = WarehouseAccountOverview.objects.filter(created_at__date=day)
        if warehouse:
            query = query.filter(warehouse=warehouse)
        if account:
            query = query.filter(account=account)
        return _as_int(query.aggregate(total=Sum(metric))["total"])

    return total_for(today), total_for(yesterday), total_for(day_before)


def _trend_points(today, yesterday, day_before):
    def y_pos(value):
        return 35 - int(30 * min(100, max(0, value or 0)) / 100)

    return {
        "today": today,
        "yesterday": yesterday,
        "day_before": day_before,
        "y_today": y_pos(today),
        "y_yesterday": y_pos(yesterday),
        "y_day_before": y_pos(day_before),
    }


def _trend_metric(today, yesterday, day_before):
    def axis(value):
        return 0 if value is None else int(value)

    today_n, yesterday_n, before_n = axis(today), axis(yesterday), axis(day_before)
    maximum = max(today_n, yesterday_n, before_n) or 1

    def y_pos(value):
        return 35 - int(30 * (value / maximum))

    return {
        "today": today,
        "yesterday": yesterday,
        "day_before": day_before,
        "max": maximum,
        "y_today": y_pos(today_n),
        "y_yesterday": y_pos(yesterday_n),
        "y_day_before": y_pos(before_n),
    }
