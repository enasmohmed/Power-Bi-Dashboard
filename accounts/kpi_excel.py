import re
from pathlib import Path

import pandas as pd
from django.conf import settings

from . import dummy_data
from . import sla_settings

EXCEL_NAME = "Data_Power_Bi.xlsx"
LOCAL_SLA_H = 48
REMOTE_SLA_H = 72
INBOUND_SLA_H = 24
ARAMCO_LOCAL_CITIES = {
    "jeddah", "jiddah", "jedda", "jeddah city", "جدة",
}

IFFCO_DOT = "#e53935"
ARAMCO_DOT = "#43a047"
COMPANY_DOTS = {
    "iffco": IFFCO_DOT,
    "aramco": ARAMCO_DOT,
    "nespresso": "#6f4e37",
    "saas": "#1565c0",
}
COMPANY_LABELS = {
    "iffco": "IFFCO",
    "aramco": "ARAMCO",
    "nespresso": "Nespresso",
    "saas": "SAAS",
}
PREFERRED_COMPANIES = ("iffco", "aramco", "nespresso", "saas")

SHEET_ALIASES = {
    "orderheader": ("orderheader", "order header", "orders", "order hdr"),
    "ibshipments": ("ibshipments", "ib shipments", "inbound", "ib shipment"),
    "oblpn": ("oblpn", "ob lpn", "outbound lpn"),
    "iblpn": ("iblpn", "ib lpn", "inventory", "iblpns"),
    "dashboard": ("dashboard", "dash board", "dash-board"),
}

NEEDED_SHEETS = ("orderheader", "ibshipments", "oblpn", "iblpn")
HIT_VALUES = {"hit", "1", "1.0", "true", "yes", "y", "h", "on time", "ontime", "perfect"}
MISS_VALUES = {"miss", "0", "0.0", "false", "no", "n", "m", "late", "missed"}
LOCAL_VALUES = {"local", "l", "inside", "inside city", "in city"}
REMOTE_VALUES = {"remote", "r", "outside", "outside city", "out city"}


def excel_candidates():
    roots = [
        Path(getattr(settings, "MEDIA_ROOT", settings.BASE_DIR / "media")) / "kpi" / EXCEL_NAME,
        settings.BASE_DIR / "data" / EXCEL_NAME,
        settings.BASE_DIR / EXCEL_NAME,
    ]
    return roots


def find_excel_path():
    for path in excel_candidates():
        if path.exists() and path.is_file():
            return path
    return None


def storage_path():
    dest = Path(getattr(settings, "MEDIA_ROOT", settings.BASE_DIR / "media")) / "kpi" / EXCEL_NAME
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


def _norm(value):
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def _sheet_key(name):
    n = _norm(name)
    for key, aliases in SHEET_ALIASES.items():
        if n in {_norm(a) for a in aliases} or any(_norm(a) in n for a in aliases):
            return key
    return n


def _find_col(df, *candidates):
    if df is None:
        return None
    mapping = {}
    for col in df.columns:
        raw = str(col)
        if raw.startswith("_") or raw.lower().startswith("unnamed"):
            continue
        mapping[_norm(col)] = col
    wanted = [_norm(c) for c in candidates]
    for key in wanted:
        if key in mapping:
            return mapping[key]
    for key in wanted:
        if len(key) < 5:
            continue
        for actual, original in mapping.items():
            if key in actual:
                return original
    return None


def _series(df, *candidates):
    col = _find_col(df, *candidates)
    if col is None:
        return pd.Series([pd.NA] * len(df), index=df.index)
    return df[col]


def _company_col(df):
    col = _find_col(df, "Company Code", "Company", "CompanyName", "Client")
    if col:
        return col
    if df is None or df.empty:
        return None
    first = df.columns[0]
    if _norm(first).startswith("unnamed"):
        sample = df[first].dropna().astype(str).str.upper()
        if sample.str.contains("IFFCO|ARAMCO|NESPRESSO|NESSPRESSO|SAAS|IFC", regex=True, na=False).any():
            return first
    return None


def _is_iffco(value):
    text = str(value).strip().upper()
    return text in {"IFFCO", "IFC"} or "IFFCO" in text


def _is_aramco(value):
    text = str(value).strip().upper()
    return "ARAMCO" in text


def _company_key(value):
    if _is_iffco(value):
        return "iffco"
    if _is_aramco(value):
        return "aramco"
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "-"}:
        return ""
    n = _norm(text)
    if n in {"nespresso", "nesspresso", "nespreso"}:
        return "nespresso"
    if n == "saas":
        return "saas"
    return n or "unknown"


def _company_label(value):
    key = _company_key(value)
    if key in COMPANY_LABELS:
        return COMPANY_LABELS[key]
    return str(value).strip()


def _dot_color(key):
    return COMPANY_DOTS.get(key, "#1565c0")


def _filter_company(df, kind):
    if df is None or df.empty:
        return df.iloc[0:0] if df is not None else pd.DataFrame()
    if kind in (None, "", "all"):
        return df
    if "_company_key" in df.columns:
        return df[df["_company_key"] == kind]
    col = _company_col(df)
    return df[df[col].map(_company_key) == kind]


def _add_company_key(df):
    col = _company_col(df)
    if not col:
        df["_company_key"] = ""
        return df
    upper = df[col].astype(str).str.strip().str.upper()
    key = pd.Series("", index=df.index, dtype="object")
    iffco = upper.eq("IFFCO") | upper.eq("IFC") | upper.str.contains("IFFCO", na=False)
    aramco = upper.str.contains("ARAMCO", na=False)
    nespresso = upper.isin({"NESPRESSO", "NESSPRESSO", "NESPRESO"}) | upper.str.contains(
        "NESPRESSO|NESSPRESSO", regex=True, na=False
    )
    saas = upper.eq("SAAS")
    invalid = upper.isin({"NAN", "NONE", "-", "NAT", ""})
    key = (
        key.mask(iffco, "iffco")
        .mask(aramco, "aramco")
        .mask(nespresso, "nespresso")
        .mask(saas, "saas")
    )
    other = ~(iffco | aramco | nespresso | saas | invalid)
    if other.any():
        key = key.mask(other, df.loc[other, col].astype(str).map(_norm))
    df["_company_key"] = key
    return df


def _memo(sheets, key, factory):
    store = sheets.setdefault("_prep", {})
    if key not in store:
        store[key] = factory()
    return store[key]


def discover_companies(sheets):
    found = {}
    for name in ("orderheader", "oblpn", "ibshipments", "iblpn"):
        df = sheets.get(name)
        if df is None or df.empty:
            continue
        col = _company_col(df)
        if col is None:
            continue
        if "_company_key" not in df.columns:
            df = _add_company_key(df.copy())
        labels = (
            df.loc[df["_company_key"] != "", [col, "_company_key"]]
            .dropna()
            .drop_duplicates(subset=["_company_key"])
        )
        for _, row in labels.iterrows():
            key = str(row["_company_key"]).strip()
            if not key or key in found:
                continue
            found[key] = COMPANY_LABELS.get(key) or str(row[col]).strip() or key.upper()
    order = []
    for preferred in PREFERRED_COMPANIES:
        if preferred in found:
            order.append({"key": preferred, "name": found.pop(preferred)})
    for key, name in sorted(found.items(), key=lambda item: item[1].lower()):
        order.append({"key": key, "name": name})
    return order


def discover_warehouses(sheets, company_key="all"):
    names = []
    for sheet_name in ("orderheader", "oblpn"):
        df = sheets.get(sheet_name)
        if df is None or df.empty:
            continue
        df = _filter_company(df, company_key)
        col = _wh_col(df)
        if not col:
            continue
        vals = df[col].dropna().astype(str).str.strip()
        vals = vals[~vals.str.lower().isin({"nan", "none", "-", ""})]
        names.extend(vals.unique().tolist())
    return sorted(set(names), key=str.lower)


def _is_hit(value):
    return str(value).strip().lower() in HIT_VALUES


def _is_miss(value):
    return str(value).strip().lower() in MISS_VALUES


def _is_local(value):
    return str(value).strip().lower() in LOCAL_VALUES


def _is_remote(value):
    return str(value).strip().lower() in REMOTE_VALUES


def _city_is_local(city):
    return _norm(city) in {_norm(c) for c in ARAMCO_LOCAL_CITIES} or "jeddah" in _norm(city)


def _to_dt(series):
    if series is None:
        return pd.Series(dtype="datetime64[ns]")
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce")
    parsed = pd.to_datetime(series, errors="coerce")
    if parsed.notna().any() and float(parsed.isna().mean()) < 0.5:
        return parsed
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().any():
        return pd.to_datetime(numeric, unit="d", origin="1899-12-30", errors="coerce")
    return parsed


def _as_order_key(series):
    text = series.astype(str).str.strip()
    return text.str.replace(r"\.0$", "", regex=True)


def _hours(start, end):
    delta = _to_dt(end) - _to_dt(start)
    return delta.dt.total_seconds() / 3600.0


def _pct(hit, total, digits=1):
    if not total:
        return None
    value = 100.0 * hit / total
    if abs(value - 100) < 0.05:
        return 100 if digits == 0 else 100.0
    return round(value, digits)


def _fmt_pct(value):
    if value is None:
        return "—"
    if value == 100 or value == 100.0:
        return "100%"
    return f"{value:.1f}%"


def _tone(value, miss=False):
    if miss:
        return "bad" if value else "ok"
    if value is None:
        return "info"
    if value >= 95:
        return "ok"
    if value >= 90:
        return "warn"
    return "bad"


def _dot(value):
    if value is None:
        return "#9ca3af"
    if value >= 100:
        return "#22c55e"
    if value >= 90:
        return "#f59e0b"
    return "#dc2626"


def _status(score):
    if score is None:
        return "Watch", "warn"
    if score >= 99.5:
        return "Excellent", "ok"
    if score >= 95:
        return "Good", "ok"
    if score >= 90:
        return "Watch", "warn"
    return "Needs Attn", "bad"


def _city_status(score):
    if score is None:
        return "Watch"
    if score >= 99.5:
        return "Perfect"
    if score >= 95:
        return "Hit"
    return "Watch"


def _city_match_mask(city_l, name):
    aliases = {
        "jeddah": ("jeddah", "jiddah", "jedda", "جدة", "ط¬ط¯ط©"),
        "madinah": ("madinah", "madina", "medina", "المدينة", "ط§ظ„ظ…ط¯ظٹظ†ط©"),
        "riyadh": ("riyadh", "riyad", "الرياض", "ط§ظ„ط±ظٹط§ط¶"),
        "dammam": ("dammam", "damman"),
        "makkah": ("makkah", "mecca", "makka", "مكة", "ظ…ظƒط©"),
        "tabuk": ("tabuk",),
        "yanbu": ("yanbu", "yanbo"),
    }
    keys = aliases.get(name.lower(), (name.lower(),))
    mask = False
    for key in keys:
        mask = mask | city_l.str.contains(key, na=False)
    return mask


def _risk(rate):
    if rate == 0:
        return "Perfect"
    if rate >= 10:
        return "High"
    return "Watch"


def _period(series, orders=None):
    dates = _to_dt(series).dropna()
    if dates.empty:
        return {"note": "", "short": "", "year_range": "2025 - 2026"}
    month = dates.dt.to_period("M").mode().iloc[0]
    years = sorted(set(dates.dt.year.astype(int)))
    year_range = f"{years[0]} - {years[-1]}" if len(years) > 1 else str(years[0])
    note = month.strftime("%B %Y")
    if orders:
        note = f"{note} · {orders:,} Orders"
    return {"note": note, "short": month.strftime("%b %Y"), "year_range": year_range, "long": month.strftime("%B %Y")}


def _int(value):
    try:
        if pd.isna(value):
            return 0
        return int(value)
    except (TypeError, ValueError):
        return 0


def _excel_engine():
    try:
        import python_calamine  # noqa: F401
        return "calamine"
    except ImportError:
        return "openpyxl"


def _read_with_engine(path, engine, only=None):
    xl = pd.ExcelFile(path, engine=engine)
    try:
        selected = {}
        wanted = set(only or NEEDED_SHEETS)
        for name in xl.sheet_names:
            key = _sheet_key(name)
            if key in wanted and key not in selected:
                selected[key] = name
        if not selected:
            return {}
        raw = pd.read_excel(xl, sheet_name=list(selected.values()))
    finally:
        close = getattr(xl, "close", None)
        if callable(close):
            close()
    if not isinstance(raw, dict):
        raw = {list(selected.values())[0]: raw}
    name_to_key = {name: key for key, name in selected.items()}
    sheets = {}
    for name, df in raw.items():
        if df is None or df.empty:
            continue
        df = df.dropna(how="all")
        df.columns = [str(c).strip() for c in df.columns]
        sheets[name_to_key.get(name, _sheet_key(name))] = _add_company_key(df)
    return sheets


def _read_workbook(path, only=None):
    engines = [_excel_engine()]
    if engines[0] != "openpyxl":
        engines.append("openpyxl")
    last_error = None
    for engine in engines:
        try:
            return _read_with_engine(path, engine, only=only)
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error
    return {}


def workbook_has_kpi_sheets(path=None):
    path = path or find_excel_path()
    if not path:
        return False
    xl = pd.ExcelFile(path, engine=_excel_engine())
    try:
        keys = {_sheet_key(name) for name in xl.sheet_names}
    finally:
        close = getattr(xl, "close", None)
        if callable(close):
            close()
    return bool(keys.intersection(NEEDED_SHEETS))


def _order_nbr(df):
    return _find_col(df, "Order Nbr", "Order Number", "OrderNbr", "Order No")


def _packed_col(df):
    return _find_col(df, "Packed Timestamp", "Packed TS", "Packed Date", "Ship Date", "Shipped Timestamp")


def _order_date_col(df):
    return _find_col(df, "Order Date", "OrderDate", "Created Date", "Order Ts")


def _loc_col(df):
    col = _find_col(
        df,
        "Remote/Local",
        "Remote Local",
        "Local Remote",
        "Lane",
        "Order Hdr - Custom Field 1",
        "Custom Field 1",
    )
    if not col or df is None or df.empty:
        return None
    sample = df[col].dropna().astype(str).str.strip().str.lower()
    if sample.empty:
        return None
    if sample.isin(LOCAL_VALUES | REMOTE_VALUES).any() or sample.str.contains(r"local|remote", regex=True, na=False).any():
        return col
    return None


def _kpi_col(df, kind="despatch"):
    if kind == "crd":
        return _find_col(df, "KPI CRD", "KPI CRD Status", "CRD", "Customer Receiving")
    return _find_col(df, "KPI Despatch", "KPI Dispatch", "Despatch KPI", "Dispatch KPI", "SLA Status")


def _wh_col(df):
    if df is None:
        return None
    if "_wh" in df.columns:
        return "_wh"
    return _find_col(df, "WH", "Warehouse", "Facility Code", "Facility", "Facility Name")


def _apply_warehouse(df, warehouse):
    if df is None or df.empty or not warehouse or warehouse == "all":
        return df
    col = _wh_col(df)
    if not col:
        return df
    return df[df[col].astype(str).str.strip() == str(warehouse).strip()].copy()


def _city_local_mask(series):
    text = series.astype(str).str.lower()
    return (
        text.str.contains("jeddah", na=False)
        | text.str.contains("jiddah", na=False)
        | text.str.contains("jedda", na=False)
        | text.str.contains("جدة", na=False)
        | text.str.contains("ط¬ط¯ط©", na=False)
    )


def _uses_timestamp_method(key, orders):
    if key == "aramco":
        return True
    if orders is None or getattr(orders, "empty", True):
        return key != "iffco"
    return _kpi_col(orders, "despatch") is None


def _ob_order_stats(sheets):
    def factory():
        ob = sheets.get("oblpn")
        if ob is None or ob.empty:
            return pd.DataFrame()
        order_col = _order_nbr(ob)
        if not order_col:
            return pd.DataFrame()
        packed_col = _packed_col(ob)
        city_col = _find_col(ob, "Customer City", "City", "Destination City", "Ship To City")
        fac_col = _find_col(ob, "Facility Code", "Facility", "WH", "Warehouse")
        qty_col = _find_col(ob, "Packed Qty", "Qty", "Current Qty")
        slim_cols = [c for c in (order_col, packed_col, city_col, fac_col, qty_col) if c]
        slim = ob.loc[:, slim_cols].copy()
        slim["_okey"] = _as_order_key(slim[order_col])
        if packed_col:
            slim[packed_col] = _to_dt(slim[packed_col])
        agg = {}
        if packed_col:
            agg[packed_col] = "max"
        if qty_col:
            agg[qty_col] = "sum"
        stats = slim.groupby("_okey", sort=False).agg(agg) if agg else slim.groupby("_okey", sort=False).size().to_frame("_n")
        rename = {}
        if packed_col:
            rename[packed_col] = "_packed"
        if qty_col:
            rename[qty_col] = "_ob_qty"
        stats = stats.rename(columns=rename)

        def first_non_empty(col, dest):
            if not col:
                return
            data = slim.loc[slim[col].notna(), ["_okey", col]].copy()
            data[col] = data[col].astype(str).str.strip()
            data = data[~data[col].str.lower().isin({"", "nan", "none", "nat"})]
            if data.empty:
                return
            stats[dest] = data.drop_duplicates("_okey", keep="first").set_index("_okey")[col]

        first_non_empty(city_col, "_ob_city")
        first_non_empty(fac_col, "_wh")
        return stats
    return _memo(sheets, "ob_stats", factory)


def _load_kpi_orders(sheets, key="iffco"):
    oh = sheets.get("orderheader")
    if oh is None:
        return pd.DataFrame()
    df = _filter_company(oh, key)
    if df.empty:
        return df
    df = df.copy()
    loc = _loc_col(df)
    if loc:
        lane = df[loc].astype(str).str.strip().str.lower()
        df["_lane"] = ""
        df.loc[lane.isin(LOCAL_VALUES), "_lane"] = "local"
        df.loc[lane.isin(REMOTE_VALUES), "_lane"] = "remote"
        if (df["_lane"] == "").all():
            city = _find_col(df, "Customer City", "Ship to City")
            if city:
                df["_lane"] = "remote"
                df.loc[_city_local_mask(df[city]), "_lane"] = "local"
            else:
                df["_lane"] = "local"
    else:
        city = _find_col(df, "Customer City", "Ship to City")
        if city:
            df["_lane"] = "remote"
            df.loc[_city_local_mask(df[city]), "_lane"] = "local"
        else:
            df["_lane"] = "local"
    despatch = _kpi_col(df, "despatch")
    crd = _kpi_col(df, "crd")
    df["_hit"] = df[despatch].astype(str).str.strip().str.lower().isin(HIT_VALUES) if despatch else False
    df["_miss"] = df[despatch].astype(str).str.strip().str.lower().isin(MISS_VALUES) if despatch else False
    df["_crd_hit"] = df[crd].astype(str).str.strip().str.lower().isin(HIT_VALUES) if crd else False
    df["_crd_miss"] = df[crd].astype(str).str.strip().str.lower().isin(MISS_VALUES) if crd else False
    stats = _ob_order_stats(sheets)
    order_col = _order_nbr(df)
    if order_col and stats is not None and not stats.empty:
        keys = _as_order_key(df[order_col])
        if "_wh" in stats and "_wh" not in df.columns:
            df["_wh"] = keys.map(stats["_wh"])
        if "_packed" in stats:
            df["_packed"] = keys.map(stats["_packed"])
    date_col = _order_date_col(df)
    if date_col and "_packed" in df.columns:
        df["_hours"] = _hours(df[date_col], df["_packed"])
    if "_city" not in df.columns:
        df["_city"] = ""
    return df


def _load_ts_orders(sheets, key="aramco"):
    oh = sheets.get("orderheader")
    if oh is None:
        return pd.DataFrame()
    orders = _filter_company(oh, key)
    if orders.empty:
        return orders
    orders = orders.copy()
    status_col = _find_col(orders, "Status", "Order Status")
    if status_col:
        status = orders[status_col].astype(str).str.lower()
        if key == "aramco":
            shipped = status.str.contains("ship", na=False)
            if shipped.any():
                orders = orders[shipped].copy()
            else:
                skip = status.str.contains(r"cancel|created|^allocat|partly", na=False, regex=True)
                orders = orders[~skip].copy()
        elif key == "iffco":
            skip = status.str.contains(r"cancel", na=False)
            if skip.any():
                orders = orders[~skip].copy()
        else:
            skip = status.str.contains(r"cancel|created|^allocat|partly", na=False, regex=True)
            if skip.any():
                orders = orders[~skip].copy()
        if orders.empty:
            return orders

    stats = _ob_order_stats(sheets)
    order_col = _order_nbr(orders)
    date_col = _order_date_col(orders)
    oh_city = _find_col(orders, "Customer City", "Ship to City", "City", "Destination City")

    if order_col and stats is not None and not stats.empty:
        keys = _as_order_key(orders[order_col])
        if "_packed" in stats:
            orders["_packed"] = keys.map(stats["_packed"])
        else:
            orders["_packed"] = pd.NaT
        if "_wh" in stats:
            orders["_wh"] = keys.map(stats["_wh"])
        if "_ob_city" in stats:
            orders["_ob_city"] = keys.map(stats["_ob_city"])
        if "_ob_qty" in stats:
            orders["_ob_qty"] = keys.map(stats["_ob_qty"])
    else:
        orders["_packed"] = pd.NaT

    if oh_city:
        city = orders[oh_city].fillna("").astype(str).str.strip()
        blank = city.str.lower().isin({"", "nan", "none", "nat"})
        if "_ob_city" in orders:
            city = city.mask(blank, orders["_ob_city"].fillna("").astype(str).str.strip())
            blank = city.str.lower().isin({"", "nan", "none", "nat"})
        addr = _find_col(orders, "Customer Address", "Address", "Ship to Address")
        if addr:
            city = city.mask(blank, orders[addr].fillna("").astype(str).str.strip())
        orders["_city"] = city
    elif "_ob_city" in orders:
        city = orders["_ob_city"].fillna("").astype(str)
        blank = city.str.lower().isin({"", "nan", "none", "nat"})
        addr = _find_col(orders, "Customer Address", "Address", "Ship to Address")
        if addr:
            city = city.mask(blank, orders[addr].fillna("").astype(str).str.strip())
        orders["_city"] = city
    else:
        addr = _find_col(orders, "Customer Address", "Address", "Ship to Address")
        orders["_city"] = orders[addr].fillna("").astype(str) if addr else ""

    orders["_lane"] = "remote"
    orders.loc[_city_local_mask(orders["_city"]), "_lane"] = "local"
    city = orders["_city"].astype(str)
    city = city.mask(_city_local_mask(city), "Jeddah")
    city_l = city.str.lower()
    city = city.mask(_city_match_mask(city_l, "Riyadh"), "Riyadh")
    city = city.mask(_city_match_mask(city_l, "Madinah"), "Madinah")
    city = city.mask(_city_match_mask(city_l, "Makkah"), "Makkah")
    city = city.mask(_city_match_mask(city_l, "Dammam"), "Dammam")
    city = city.mask(_city_match_mask(city_l, "Tabuk"), "Tabuk")
    city = city.mask(_city_match_mask(city_l, "Yanbu"), "Yanbu")
    orders["_city"] = city
    loc = _loc_col(orders)
    if loc:
        lane = orders[loc].astype(str).str.strip().str.lower()
        orders.loc[lane.isin(LOCAL_VALUES), "_lane"] = "local"
        orders.loc[lane.isin(REMOTE_VALUES), "_lane"] = "remote"

    cfg = sla_settings.get(key)
    orders["_crd_hit"] = False
    orders["_crd_miss"] = False
    if date_col:
        hours = _hours(orders[date_col], orders["_packed"])
        limit = orders["_lane"].map({"local": cfg["local_h"], "remote": cfg["remote_h"]})
        orders["_hours"] = hours
        orders["_hit"] = hours <= limit
        orders["_miss"] = hours > limit
        orders.loc[hours.isna(), ["_hit", "_miss"]] = False
        crd_hit = hours <= cfg["crd_h"]
        orders["_crd_hit"] = crd_hit
        orders["_crd_miss"] = hours > cfg["crd_h"]
        orders.loc[hours.isna(), ["_crd_hit", "_crd_miss"]] = False
    else:
        kpi = _kpi_col(orders, "despatch")
        orders["_hours"] = pd.NA
        orders["_hit"] = orders[kpi].astype(str).str.strip().str.lower().isin(HIT_VALUES) if kpi else False
        orders["_miss"] = orders[kpi].astype(str).str.strip().str.lower().isin(MISS_VALUES) if kpi else False
    return orders


def _orders_for(sheets, key):
    def factory():
        oh = sheets.get("orderheader")
        sample = _filter_company(oh, key) if oh is not None else pd.DataFrame()
        if _uses_timestamp_method(key, sample):
            return _load_ts_orders(sheets, key)
        return _load_kpi_orders(sheets, key)
    return _memo(sheets, f"orders:{key}", factory)


def _load_iffco_orders(sheets):
    return _orders_for(sheets, "iffco")


def _load_aramco_orders(sheets):
    return _orders_for(sheets, "aramco")


def _load_inbound(sheets, kind):
    def factory():
        ib = sheets.get("ibshipments")
        if ib is None:
            return pd.DataFrame()
        df = _filter_company(ib, kind)
        if df.empty:
            return df
        df = df.copy()
        status_col = _find_col(df, "Status", "Shipment Status")
        if status_col:
            skip = df[status_col].astype(str).str.lower().str.contains(
                r"cancel|in transit|created", na=False, regex=True
            )
            if skip.any():
                df = df[~skip].copy()
            if df.empty:
                return df
        arrival = _find_col(df, "Arrival Date", "Arrival TS", "Arrival")
        offload = _find_col(df, "Offloading Date", "Offload Date")
        first_rcv = _find_col(df, "First LPN Rcv TS", "First LPN Received", "First Receive", "Rcv TS")
        last_rcv = _find_col(df, "Last LPN Rcv TS", "Last LPN Received", "GRN Date", "Last Receive")
        start = None
        if arrival:
            start = _to_dt(df[arrival])
        if offload is not None:
            off = _to_dt(df[offload])
            start = off if start is None else start.fillna(off)
        if start is not None and first_rcv:
            limit = sla_settings.get(kind)["inbound_h"]
            df["_rcv_hours"] = _hours(start, df[first_rcv])
            df["_rcv_hit"] = df["_rcv_hours"] <= limit
            df["_rcv_miss"] = df["_rcv_hours"] > limit
            df.loc[df["_rcv_hours"].isna(), ["_rcv_hit", "_rcv_miss"]] = False
        else:
            df["_rcv_hours"] = pd.NA
            df["_rcv_hit"] = False
            df["_rcv_miss"] = False
        if start is not None and last_rcv:
            grn_limit = sla_settings.get(kind)["grn_h"]
            df["_grn_hours"] = _hours(start, df[last_rcv])
            df["_grn_hit"] = df["_grn_hours"] <= grn_limit
            df.loc[df["_grn_hours"].isna(), "_grn_hit"] = False
        else:
            df["_grn_hours"] = df.get("_rcv_hours", pd.NA)
            df["_grn_hit"] = df.get("_rcv_hit", False)
        return df
    return _memo(sheets, f"ib:{kind or 'all'}", factory)


def _count_hit_miss(df, lane=None, kind="despatch"):
    data = df if lane is None else df[df["_lane"] == lane]
    hit_col = "_crd_hit" if kind == "crd" else "_hit"
    miss_col = "_crd_miss" if kind == "crd" else "_miss"
    hit = int(data[hit_col].fillna(False).sum()) if hit_col in data else 0
    miss = int(data[miss_col].fillna(False).sum()) if miss_col in data else 0
    timestamp = "_hours" in getattr(data, "columns", [])
    if timestamp and hit_col in data and miss_col in data:
        scored = int((data[hit_col].fillna(False) | data[miss_col].fillna(False)).sum())
        total = scored if scored else len(data)
    else:
        total = len(data)
        if not miss:
            miss = max(total - hit, 0)
    return hit, miss, total, _pct(hit, total)


def _overview_company(sheets, key, name):
    df = _orders_for(sheets, key)
    if df is None or df.empty:
        return None
    ib = _load_inbound(sheets, key)
    local_hit, local_miss, local_total, local_pct = _count_hit_miss(df, "local")
    remote_hit, remote_miss, remote_total, remote_pct = _count_hit_miss(df, "remote")
    _, total_miss, _, overall = _count_hit_miss(df)
    total = len(df)
    if not local_total and not remote_total:
        local_total = total
        local_pct = overall
    ib_total = 0 if ib is None or ib.empty else len(ib)
    ib_hit = 0
    ib_miss = 0
    inbound = None
    if ib_total and "_rcv_hit" in ib:
        ib_hit = int(ib["_rcv_hit"].fillna(False).sum())
        ib_miss = int(ib["_rcv_miss"].fillna(False).sum()) if "_rcv_miss" in ib else 0
        scored = ib_hit + ib_miss
        inbound = _pct(ib_hit, scored or ib_total)
    date_col = _order_date_col(df)
    period = _period(df[date_col] if date_col else pd.Series(dtype="datetime64[ns]"), total)
    miss_city = ""
    if total_miss and "_city" in df:
        cities = df[df["_miss"].fillna(False)]["_city"].astype(str)
        if not cities.empty:
            miss_city = cities.mode().iloc[0]
    if miss_city:
        misses_note = f"Remote only - {miss_city}" if not local_miss else f"Local: {local_miss} - Remote: {remote_miss}"
    else:
        misses_note = f"Local: {local_miss} - Remote: {remote_miss}"
    inbound_note = "No inbound rows"
    if ib_total:
        if not (ib_hit + ib_miss):
            inbound_note = "No inbound timestamps"
        elif (inbound or 0) >= 99.5:
            inbound_note = "All within 24h"
        else:
            inbound_note = f"{ib_miss} shipments exceeded 24h"
    return {
        "key": key,
        "name": name,
        "subtitle": "3PL KPI — KSA Warehouses",
        "period_note": period["note"] or period["long"],
        "period": period["short"],
        "total_outbound": total,
        "local": local_total,
        "remote": remote_total,
        "overall_sla": overall or 0,
        "sla_note": "Strong — all warehouses" if (overall or 0) >= 95 else "Needs attention",
        "total_misses": total_miss,
        "misses_local": local_miss,
        "misses_remote": remote_miss,
        "misses_note": misses_note,
        "inbound_kpi": inbound or 0,
        "inbound_note": inbound_note,
        "local_sla": local_pct or 0,
        "remote_sla": remote_pct or 0,
        "inbound_sla": inbound or 0,
        "dot_color": _dot_color(key),
    }


def _overview(sheets):
    store = sheets.setdefault("_prep", {})
    if "overview" in store:
        return store["overview"]
    companies = []
    for item in discover_companies(sheets):
        block = _overview_company(sheets, item["key"], item["name"])
        if block:
            companies.append(block)
    result = {"year_range": _year_range(sheets), "companies": companies}
    store["overview"] = result
    return result


def _warehouse_rows(df):
    rows = []
    wh_col = _wh_col(df)
    if not wh_col:
        return rows
    for name, group in df.groupby(df[wh_col].astype(str)):
        label = str(name).strip() or "Unknown"
        if label.lower() in {"nan", "none"}:
            continue
        lh, lm, lt, lp = _count_hit_miss(group, "local")
        rh, rm, rt, rp = _count_hit_miss(group, "remote")
        rows.append({
            "name": label,
            "dot": _dot(lp if lt else rp),
            "local_hit": lh if lt else None,
            "local_miss": lm if lt else None,
            "local_pct": lp,
            "remote_hit": rh if rt else None,
            "remote_miss": rm if rt else None,
            "remote_pct": rp,
            "total": len(group),
        })
    rows.sort(key=lambda row: row["name"].lower())
    return rows


def _city_rows(df):
    featured = ["Jeddah", "Riyadh", "Madinah", "Dammam", "Makkah", "Tabuk", "Yanbu"]
    rows = []
    used = set()
    city_series = df["_city"].fillna("").astype(str)
    city_l = city_series.str.lower()
    for name in featured:
        mask = _city_match_mask(city_l, name)
        group = df[mask]
        if group.empty:
            continue
        used |= set(group.index)
        h, m, t, p = _count_hit_miss(group)
        rows.append({
            "name": name,
            "dot": _dot(p),
            "orders": t,
            "hit": h,
            "miss": m if m else None,
            "sla": p or 0,
            "status": _city_status(p),
        })
    other = df.loc[~df.index.isin(used)]
    if not other.empty:
        h, m, t, p = _count_hit_miss(other)
        rows.append({
            "name": "Other Cities",
            "dot": _dot(p),
            "orders": t,
            "hit": h,
            "miss": m if m else None,
            "sla": p or 0,
            "status": _city_status(p),
        })
    return rows


def _outbound_company(df, key, name, method, warehouse="all"):
    df = _apply_warehouse(df, warehouse)
    if df is None or df.empty:
        return None
    date_col = _order_date_col(df)
    period = _period(df[date_col] if date_col else pd.Series(dtype="datetime64[ns]"))
    if method == "timestamp":
        l_hit, l_miss, l_total, l_pct = _count_hit_miss(df, "local")
        r_hit, r_miss, r_total, r_pct = _count_hit_miss(df, "remote")
        hit, miss, total, overall = _count_hit_miss(df)
        miss_cities = df[df["_miss"].fillna(False)]["_city"].astype(str) if "_city" in df else pd.Series(dtype=str)
        miss_city = miss_cities.mode().iloc[0] if not miss_cities.empty else ""
        miss_note = f"{miss_city} late orders" if miss_city else f"{miss} late orders"
        warehouses = _warehouse_rows(df)
        payload = {
            "key": key,
            "name": name,
            "period": period["short"] or period["long"],
            "dot_color": _dot_color(key),
            "layout": "city",
            "table_title": "Hit / Miss by City",
            "sla_note": "Local 48h — Remote 72h",
            "kpis": [
                {"label": "Local Despatch (48h)", "value": _fmt_pct(l_pct), "sub": f"{l_hit}/{l_total} orders", "tone": _tone(l_pct)},
                {"label": "Remote Despatch (72h)", "value": _fmt_pct(r_pct), "sub": f"{r_hit}/{r_total} orders", "tone": _tone(r_pct)},
                {"label": "Total Misses", "value": str(miss), "sub": miss_note, "tone": _tone(miss, miss=True)},
                {"label": "Overall", "value": _fmt_pct(overall), "sub": f"{hit}/{total} orders", "tone": _tone(overall)},
            ],
            "warehouses": [row["name"] for row in warehouses],
        }
        payload["rows"] = _city_rows(df)
        payload["totals"] = {"orders": total, "hit": hit, "miss": miss, "sla": overall or 0, "status": _fmt_pct(overall)}
        return payload

    l_hit, l_miss, l_total, l_pct = _count_hit_miss(df, "local")
    r_hit, r_miss, r_total, r_pct = _count_hit_miss(df, "remote")
    crd_l_hit, crd_l_miss, _, crd_l_pct = _count_hit_miss(df, "local", "crd")
    crd_r_hit, crd_r_miss, _, crd_r_pct = _count_hit_miss(df, "remote", "crd")
    rows = _warehouse_rows(df)
    return {
        "key": key,
        "name": name,
        "period": period["long"] or period["short"],
        "dot_color": _dot_color(key),
        "layout": "warehouse",
        "table_title": "Hit / Miss by Warehouse",
        "sla_note": "Local 48h — Remote 72h",
        "kpis": [
            {"label": "Local Despatch", "value": _fmt_pct(l_pct), "sub": f"{l_hit:,} Hit / {l_miss} Miss", "tone": _tone(l_pct)},
            {"label": "Local CRD", "value": _fmt_pct(crd_l_pct) if crd_l_hit or crd_l_miss else "—", "sub": f"{crd_l_hit:,} Hit / {crd_l_miss} Miss" if crd_l_hit or crd_l_miss else "KPI CRD not in file", "tone": _tone(crd_l_pct) if crd_l_hit or crd_l_miss else "info"},
            {"label": "Remote Despatch", "value": _fmt_pct(r_pct), "sub": f"{r_hit:,} Hit / {r_miss} Miss", "tone": _tone(r_pct)},
            {"label": "Remote CRD", "value": _fmt_pct(crd_r_pct) if crd_r_hit or crd_r_miss else "—", "sub": f"{crd_r_hit:,} Hit / {crd_r_miss} Miss" if crd_r_hit or crd_r_miss else "KPI CRD not in file", "tone": _tone(crd_r_pct) if crd_r_hit or crd_r_miss else "info"},
        ],
        "rows": rows,
        "warehouses": [row["name"] for row in rows],
        "totals": {
            "local_hit": l_hit, "local_miss": l_miss, "local_pct": l_pct or 0,
            "remote_hit": r_hit, "remote_miss": r_miss, "remote_pct": r_pct or 0,
            "total": len(df),
        },
    }


def _outbound(sheets, warehouse="all"):
    companies = []
    for item in discover_companies(sheets):
        key, name = item["key"], item["name"]
        df = _orders_for(sheets, key)
        method = "kpi" if key == "iffco" or not _uses_timestamp_method(key, df) else "timestamp"
        block = _outbound_company(df, key, name, method, warehouse)
        if not block:
            continue
        companies.append(block)
    year_range = "2025 - 2026"
    oh = sheets.get("orderheader")
    if oh is not None and not oh.empty:
        date_col = _order_date_col(oh)
        if date_col:
            year_range = _period(oh[date_col])["year_range"]
    return {"year_range": year_range, "companies": companies}


def _inbound_warehouse_block(df, key, name):
    arrival = _find_col(df, "Arrival Date", "Arrival")
    period = _period(df[arrival] if arrival else pd.Series(dtype="datetime64[ns]"))
    rcv_hit = int(df["_rcv_hit"].fillna(False).sum())
    rcv_miss = int(df["_rcv_miss"].fillna(False).sum()) if "_rcv_miss" in df else 0
    grn_hit = int(df["_grn_hit"].fillna(False).sum()) if "_grn_hit" in df else 0
    scored = rcv_hit + rcv_miss
    total = scored or len(df)
    rcv_pct = _pct(rcv_hit, total) or 0
    grn_scored = int(df["_grn_hours"].notna().sum()) if "_grn_hours" in df else total
    grn_pct = _pct(grn_hit, grn_scored or total) or 0
    fac_col = _wh_col(df)
    rows = []
    if fac_col:
        for wh_name, group in df.groupby(df[fac_col].astype(str)):
            gh = int(group["_rcv_hit"].fillna(False).sum())
            gm = int(group["_rcv_miss"].fillna(False).sum()) if "_rcv_miss" in group else 0
            t = gh + gm or len(group)
            rp = _pct(gh, t) or 0
            g_hit = int(group["_grn_hit"].fillna(False).sum()) if "_grn_hit" in group else 0
            gp = _pct(g_hit, t) or 0
            rows.append({
                "name": str(wh_name).strip(),
                "receiving": rp,
                "grn": gp,
                "status": "On Track" if rp >= 99 else "Watch",
            })
    return {
        "key": key,
        "name": name,
        "period": period["long"] or period["short"],
        "subtitle": "",
        "dot_color": _dot_color(key),
        "layout": "warehouse",
        "table_title": f"Inbound by Warehouse — {name}",
        "sla_note": "Target: 24h",
        "kpis": [
            {"label": "System Receiving", "value": _fmt_pct(rcv_pct), "sub": "All within 24h" if rcv_pct >= 99.5 else f"{rcv_miss} late", "tone": _tone(rcv_pct)},
            {"label": "GRN Sharing", "value": _fmt_pct(grn_pct), "sub": "All on time" if grn_pct >= 99.5 else f"{max(total - grn_hit, 0)} late", "tone": _tone(grn_pct)},
            {"label": "All Warehouses", "value": f"{sum(1 for r in rows if r['receiving'] >= 99)}/{len(rows) or 0}", "sub": "Facility compliance", "tone": "ok" if rows and all(r["receiving"] >= 99 for r in rows) else "warn"},
            {"label": "Inbound SLA", "value": _fmt_pct(rcv_pct), "sub": "Target: 24 hours", "tone": _tone(rcv_pct)},
        ],
        "rows": rows,
        "totals": {"receiving": rcv_pct, "grn": grn_pct, "status": _fmt_pct(rcv_pct)},
        "year_range": period["year_range"],
    }


def _inbound_shipment_block(df, key, name):
    arrival = _find_col(df, "Arrival Date", "Arrival")
    period = _period(df[arrival] if arrival else pd.Series(dtype="datetime64[ns]"))
    total = len(df)
    hit = int(df["_rcv_hit"].fillna(False).sum())
    miss = int(df["_rcv_miss"].fillna(False).sum())
    scored = hit + miss
    pct = _pct(hit, scored or total) or 0
    miss_hours = df.loc[df["_rcv_miss"].fillna(False), "_rcv_hours"].dropna()
    avg_miss = round(float(miss_hours.mean()), 0) if not miss_hours.empty else 0
    ship_col = _find_col(df, "Shipment Nbr", "Shipment", "Shipment Number")
    type_col = _find_col(df, "Type", "Shipment Type", "Order Type")
    rows = []
    sample = df.head(40)
    for _, row in sample.iterrows():
        hours = row.get("_rcv_hours")
        hours = round(float(hours), 1) if pd.notna(hours) else 0
        width = min(100, round((hours / 40.0) * 100, 1))
        tone = "ok" if hours <= 24 else ("warn" if hours <= 36 else "bad")
        ship = str(row[ship_col]) if ship_col else "Shipment"
        if len(ship) > 18:
            ship = ship[:10] + "..." + ship[-5:]
        arrival_val = ""
        if arrival and pd.notna(row.get(arrival)):
            arrival_val = pd.to_datetime(row[arrival], errors="coerce")
            arrival_val = arrival_val.strftime("%Y-%m-%d") if pd.notna(arrival_val) else ""
        rows.append({
            "shipment": ship,
            "type": str(row[type_col]).title() if type_col and pd.notna(row.get(type_col)) else "Standard",
            "arrival": arrival_val,
            "hours": hours,
            "hours_width": width,
            "hours_tone": tone,
            "rcv": 100 if row.get("_rcv_hit") else round(min(99, max(50, 100 - hours)), 1),
            "status": "On Time" if row.get("_rcv_hit") else "Late",
        })
    return {
        "key": key,
        "name": name,
        "period": period["short"] or period["long"],
        "subtitle": f"{total} Shipments",
        "dot_color": _dot_color(key),
        "layout": "shipments",
        "table_title": "Inbound Shipments — SLA (24h)",
        "sla_note": "Target: 24h",
        "kpis": [
            {"label": "Inbound SLA (24h)", "value": _fmt_pct(pct), "sub": f"{hit} Hit / {miss} Miss", "tone": _tone(pct)},
            {"label": "Shipments Missed", "value": str(miss), "sub": "Exceeded 24h window", "tone": "bad" if miss else "ok"},
            {"label": "Total Shipments", "value": str(total), "sub": "Standard + Returns", "tone": "info"},
            {"label": "Avg Miss Duration", "value": f"~{int(avg_miss)}h" if avg_miss else "—", "sub": "Missed shipments only", "tone": "warn" if miss else "ok"},
        ],
        "rows": rows,
        "year_range": period["year_range"],
    }


def _inbound(sheets):
    companies = []
    years = []
    for item in discover_companies(sheets):
        df = _load_inbound(sheets, item["key"])
        if df is None or df.empty:
            continue
        if item["key"] == "aramco":
            block = _inbound_shipment_block(df, item["key"], item["name"])
        else:
            block = _inbound_warehouse_block(df, item["key"], item["name"])
        year = block.pop("year_range", "")
        if year:
            years.append(year)
        companies.append(block)
    return {"year_range": years[-1] if years else _year_range(sheets), "companies": companies}


def _warehouse_cards(df, ib):
    cards = []
    wh_col = _wh_col(df)
    if not wh_col:
        return cards
    ib_fac = _wh_col(ib) if ib is not None and not ib.empty else None
    for name, group in df.groupby(df[wh_col].astype(str)):
        h, m, t, p = _count_hit_miss(group)
        _, _, _, lp = _count_hit_miss(group, "local")
        _, _, _, rp = _count_hit_miss(group, "remote")
        inbound = None
        if ib_fac and ib is not None and not ib.empty:
            mask = ib[ib_fac].astype(str).str.contains(str(name).strip(), case=False, na=False)
            if mask.any():
                inbound = _pct(int(ib.loc[mask, "_rcv_hit"].sum()), int(mask.sum()))
        status, tone = _status(p)
        cards.append({
            "name": str(name).strip(),
            "score": p or 0,
            "status": status if status != "Excellent" or (p or 0) < 99.5 else "Excellent",
            "tone": tone,
            "orders": t,
            "misses": m,
            "local": lp,
            "remote": rp,
            "inbound": inbound if inbound is not None else 0,
        })
    return cards


def _city_cards(df):
    featured = ["Jeddah", "Riyadh", "Madinah", "Dammam", "Makkah", "Tabuk", "Yanbu"]
    cards = []
    used = set()
    city_series = df["_city"].fillna("").astype(str)
    city_l = city_series.str.lower()
    for name in featured:
        mask = _city_match_mask(city_l, name)
        group = df[mask]
        if group.empty:
            continue
        used |= set(group.index)
        h, m, t, p = _count_hit_miss(group)
        status, tone = _status(p)
        avg_hours = None
        if "_hours" in group and group["_hours"].notna().any():
            avg_hours = int(round(float(group["_hours"].mean())))
        cards.append({
            "name": name,
            "score": p or 0,
            "status": "Watch" if (p or 0) < 90 else status,
            "tone": tone,
            "orders": t,
            "misses": m,
            "avg_label": "Local" if _city_is_local(name) else "Remote",
            "avg_hours": avg_hours,
        })
    other = df.loc[~df.index.isin(used)]
    if not other.empty:
        h, m, t, p = _count_hit_miss(other)
        status, tone = _status(p)
        cards.append({
            "name": "Other Cities",
            "score": p or 0,
            "status": status,
            "tone": tone,
            "orders": t,
            "misses": m,
            "avg_label": None,
            "avg_hours": None,
        })
    return cards


def _cities(sheets):
    companies = []
    for item in discover_companies(sheets):
        key, name = item["key"], item["name"]
        df = _orders_for(sheets, key)
        if df is None or df.empty:
            continue
        if key == "iffco" or not _uses_timestamp_method(key, df):
            cards = _warehouse_cards(df, _load_inbound(sheets, key))
            layout = "warehouse"
            title = f"{name} Performance by Warehouse"
        else:
            cards = _city_cards(df)
            layout = "city"
            title = f"{name} Performance by Destination City"
        companies.append({
            "key": key,
            "name": name,
            "section_title": title,
            "layout": layout,
            "dot_color": _dot_color(key),
            "cards": cards,
        })
    return {"year_range": _year_range(sheets), "companies": companies}


def _year_range(sheets):
    def factory():
        oh = sheets.get("orderheader")
        if oh is None or oh.empty:
            return "2025 - 2026"
        col = _order_date_col(oh)
        if not col:
            return "2025 - 2026"
        return _period(oh[col])["year_range"]
    return _memo(sheets, "year_range", factory)


def _inventory_company(df, key, name):
    status_col = _find_col(df, "Status", "LPN Status")
    lpn_col = _find_col(df, "LPN Nbr", "LPN", "LPN Number")
    qty_col = _find_col(df, "Current Qty", "Qty", "Quantity", "On Hand Qty")
    fac_col = _find_col(df, "Facility", "Facility Code", "WH")
    located = df
    received = df
    if status_col:
        located = df[df[status_col].astype(str).str.contains("located", case=False, na=False)]
        received = df[df[status_col].astype(str).str.contains("received", case=False, na=False)]
    located_n = located[lpn_col].nunique() if lpn_col else len(located)
    received_n = received[lpn_col].nunique() if lpn_col else len(received)
    qty = int(pd.to_numeric(located[qty_col], errors="coerce").fillna(0).sum()) if qty_col else 0
    facility = "Warehouse"
    if fac_col and not df.empty:
        facility = str(df[fac_col].dropna().astype(str).mode().iloc[0])
    return {
        "key": key,
        "name": name,
        "section_title": f"{name} Inventory Snapshot — {facility}",
        "dot_color": _dot_color(key),
        "kpis": [
            {"label": "Located LPNs", "value": int(located_n), "sub": "In storage locations", "tone": "info"},
            {"label": "Received LPNs", "value": int(received_n), "sub": "Pending putaway", "tone": "neutral"},
            {"label": "Total Qty On Hand", "value": qty, "sub": "Units in warehouse", "tone": "ok"},
        ],
        "notes": [
            {"text": f"Facility: {facility}" + (" — Jeddah Warehouse" if key == "aramco" else ""), "status": "Active", "tone": "info"},
            {"text": f"{int(received_n)} LPNs in Received status — pending putaway", "status": "Action Needed" if received_n else "OK", "tone": "warn" if received_n else "ok"},
        ],
    }


def _inventory(sheets):
    iblpn = sheets.get("iblpn")
    year_range = _year_range(sheets)
    payload = {
        "year_range": year_range,
        "disclaimer": "IFFCO Inventory not included in current report.",
        "footer": "Tamer Logistics — 3PL KPI Dashboard — IFFCO & Aramco — KSA Operations",
        "companies": [],
    }
    if iblpn is None or iblpn.empty:
        return payload
    df = _filter_company(iblpn, "aramco")
    if df is None or df.empty:
        return payload
    fac_col = _find_col(df, "Facility", "Facility Code", "WH")
    if fac_col:
        jed = df[fac_col].astype(str).str.upper().str.contains(r"JED|3PLJED2", regex=True, na=False)
        if jed.any():
            df = df[jed]
    payload["companies"] = [_inventory_company(df, "aramco", "ARAMCO")]
    return payload


def _sla_status(score):
    if score is None:
        return "Watch"
    if score >= 99.5:
        return "Perfect"
    if score >= 90:
        return "Hit"
    return "Miss"


def _rescore_hours(df, hours_col, limit, lane=None):
    if df is None or df.empty or hours_col not in df:
        return 0, 0, 0, None
    data = df if lane is None else df[df["_lane"] == lane]
    hours = pd.to_numeric(data[hours_col], errors="coerce")
    hit = int((hours <= limit).sum())
    miss = int((hours > limit).sum())
    total = hit + miss
    return hit, miss, total, _pct(hit, total)


def _sla_row(category, target, achievement):
    return {
        "category": category,
        "target": target,
        "achievement": achievement,
        "status": _sla_status(achievement) if achievement is not None else "—",
    }


def _sla(sheets, company="all"):
    cfg = sla_settings.get(company)
    companies = []
    for item in discover_companies(sheets):
        key, name = item["key"], item["name"]
        if company not in ("all", "", None) and key != company:
            continue
        company_cfg = sla_settings.get(key)
        df = _orders_for(sheets, key)
        ib = _load_inbound(sheets, key)
        local_pct = _rescore_hours(df, "_hours", company_cfg["local_h"], "local")[3]
        remote_pct = _rescore_hours(df, "_hours", company_cfg["remote_h"], "remote")[3]
        crd_pct = _rescore_hours(df, "_hours", company_cfg["crd_h"])[3]
        if local_pct is None and df is not None and not df.empty:
            _, _, _, local_pct = _count_hit_miss(df, "local")
            _, _, _, remote_pct = _count_hit_miss(df, "remote")
            _, _, _, crd_pct = _count_hit_miss(df, kind="crd")
        ib_pct = _rescore_hours(ib, "_rcv_hours", company_cfg["inbound_h"])[3]
        grn_pct = _rescore_hours(ib, "_grn_hours", company_cfg["grn_h"])[3]
        if ib_pct is None and ib is not None and not ib.empty and "_rcv_hit" in ib:
            hit = int(ib["_rcv_hit"].fillna(False).sum())
            miss = int(ib["_rcv_miss"].fillna(False).sum()) if "_rcv_miss" in ib else 0
            ib_pct = _pct(hit, hit + miss or len(ib))
        rows = [
            _sla_row("Outbound Local Despatch", sla_settings.fmt_hours(company_cfg["local_h"]), local_pct),
            _sla_row("Outbound Remote Despatch", sla_settings.fmt_hours(company_cfg["remote_h"]), remote_pct),
            _sla_row("Outbound CRD", sla_settings.fmt_hours(company_cfg["crd_h"]), crd_pct),
            _sla_row("Branch Transfers", sla_settings.fmt_hours(company_cfg["transfer_h"]), None),
            _sla_row("Inbound Receiving", sla_settings.fmt_hours(company_cfg["inbound_h"]), ib_pct),
            _sla_row("Inbound GRN", sla_settings.fmt_hours(company_cfg["grn_h"]), grn_pct),
        ]
        companies.append({"key": key, "name": name, "rows": rows})
    return {
        "year_range": _year_range(sheets),
        "agreement_title": dummy_data.SLA["agreement_title"],
        "table_title": dummy_data.SLA["table_title"],
        "agreement": sla_settings.agreement_cards(cfg),
        "sla_cfg": cfg,
        "sla_editable": company not in ("all", "", None),
        "companies": companies,
    }


def _misses_warehouse(df, key, name):
    d_hit, d_miss, d_total, _ = _count_hit_miss(df)
    _, crd_miss, _, _ = _count_hit_miss(df, kind="crd")
    _, local_miss, _, _ = _count_hit_miss(df, "local")
    _, remote_miss, _, _ = _count_hit_miss(df, "remote")
    wh_col = _wh_col(df)
    rows = []
    perfect = []
    highest = ("—", 0, 0, 0)
    if wh_col:
        for wh_name, group in df.groupby(df[wh_col].astype(str)):
            h, m, t, p = _count_hit_miss(group)
            rate = round(100.0 * m / t, 1) if t else 0
            rows.append({"name": str(wh_name).strip(), "orders": t, "misses": m, "rate": rate, "risk": _risk(rate)})
            if m == 0:
                perfect.append(str(wh_name).strip())
            if rate > highest[1]:
                highest = (str(wh_name).strip(), rate, m, t)
    rows.sort(key=lambda r: r["rate"], reverse=True)
    remarks_col = _find_col(df, "Remarks", "Remark", "Reason", "Miss Reason")
    reasons = []
    if remarks_col:
        miss_rows = df[df["_miss"].fillna(False)]
        counts = miss_rows[remarks_col].dropna().astype(str).str.strip()
        counts = counts[counts != ""]
        for text, count in counts.value_counts().head(4).items():
            reasons.append({"text": text, "status": f"{count} orders", "tone": "warn"})
    date_col = _order_date_col(df)
    period = _period(df[date_col] if date_col else pd.Series(dtype="datetime64[ns]"))
    return {
        "key": key,
        "name": name,
        "section_title": f"{name} Miss Analysis — {period['long'] or period['short']}",
        "layout": "warehouse",
        "dot_color": _dot_color(key),
        "kpis": [
            {"label": "Despatch Misses", "value": str(d_miss), "sub": f"Local: {local_miss}, Remote: {remote_miss}", "tone": "bad"},
            {"label": "CRD Misses", "value": str(crd_miss), "sub": "Customer receiving date", "tone": "bad"},
            {"label": f"Highest — {highest[0]}", "value": f"{highest[1]}%", "sub": f"{highest[2]} misses / {highest[3]} orders", "tone": "warn"},
            {"label": "Perfect Warehouses", "value": str(len(perfect)), "sub": " — ".join(perfect[:3]) or "None", "tone": "ok"},
        ],
        "table_title": "Miss by Warehouse",
        "rows": rows,
        "reasons_title": "Common Miss Reasons",
        "reasons": reasons or [{"text": "No remarks captured on missed orders", "status": "Info", "tone": "info"}],
    }


def _misses_city(df, ib, key, name):
    _, miss, total, _ = _count_hit_miss(df)
    miss_df = df[df["_miss"].fillna(False)]
    details = []
    missed_city = "—"
    city_sla = "—"
    if not miss_df.empty and "_city" in miss_df:
        for city, group in miss_df.groupby(miss_df["_city"].astype(str)):
            label = str(city).strip() or "Other"
            avg_h = ""
            if "_hours" in group and group["_hours"].notna().any():
                avg_h = f", avg {int(round(float(group['_hours'].mean())))}h"
            details.append({"text": f"{label}: {len(group)} miss{avg_h}", "status": "Watch", "tone": "warn"})
        missed_city = str(miss_df["_city"].astype(str).mode().iloc[0])
        city_mask = df["_city"].astype(str).str.contains(re.escape(missed_city), case=False, na=False)
        h, m, t, p = _count_hit_miss(df[city_mask])
        city_sla = f"{_fmt_pct(p)} · {t} orders"
    local_ok = df[df["_lane"] == "local"] if "_lane" in df else df.iloc[0:0]
    if not local_ok.empty and int(local_ok["_miss"].sum()) == 0:
        details.append({"text": "All local orders", "status": "Perfect", "tone": "ok"})
    ib_total = 0 if ib is None or ib.empty else len(ib)
    ib_miss = int(ib["_rcv_miss"].sum()) if ib_total else 0
    ib_hit_pct = _pct(ib_total - ib_miss, ib_total) if ib_total else None
    miss_hours = ib.loc[ib["_rcv_miss"].fillna(False), "_rcv_hours"].dropna() if ib_total else pd.Series(dtype=float)
    avg_delay = int(round(float(miss_hours.mean()))) if not miss_hours.empty else 0
    date_col = _order_date_col(df)
    period = _period(df[date_col] if date_col else pd.Series(dtype="datetime64[ns]"))
    return {
        "key": key,
        "name": name,
        "section_title": f"{name} Miss Analysis — {period['short'] or period['long']}",
        "layout": "detail",
        "dot_color": _dot_color(key),
        "kpis": [
            {"label": "Outbound Misses", "value": str(miss), "sub": "No outbound misses" if not miss else f"{miss} late orders", "tone": "warn" if miss else "ok"},
            {"label": "Missed City", "value": missed_city.title() if missed_city != "—" else "—", "sub": city_sla, "tone": "warn"},
            {"label": "Inbound Misses", "value": str(ib_miss), "sub": f"{_fmt_pct(ib_hit_pct)} on-time" if ib_hit_pct is not None else "No inbound rows", "tone": "bad" if ib_miss else "ok"},
            {"label": "Avg Inbound Delay", "value": f"~{avg_delay}h" if avg_delay else "—", "sub": f"{max(avg_delay - INBOUND_SLA_H, 0)}h above SLA", "tone": "warn" if ib_miss else "ok"},
        ],
        "outbound_title": "Outbound — Miss Detail",
        "outbound_details": details or [{"text": "No outbound misses", "status": "Perfect", "tone": "ok"}],
        "inbound_title": "Inbound — Root Cause",
        "inbound_causes": [
            {"text": f"{ib_miss} shipments exceeded the 24h receiving window", "status": "Systemic" if ib_miss else "OK", "tone": "bad" if ib_miss else "ok"},
            {"text": "Large shipments — multi-day receiving", "status": "Process", "tone": "warn"},
            {"text": "Suggest: stagger arrivals or extend to 48h", "status": "Recommend", "tone": "info"},
        ],
    }


def _misses(sheets):
    companies = []
    for item in discover_companies(sheets):
        key, name = item["key"], item["name"]
        df = _orders_for(sheets, key)
        if df is None or df.empty:
            continue
        if key == "iffco" or not _uses_timestamp_method(key, df):
            companies.append(_misses_warehouse(df, key, name))
        else:
            companies.append(_misses_city(df, _load_inbound(sheets, key), key, name))
    return {"year_range": _year_range(sheets), "companies": companies}


def _nunique(df, *candidates):
    if df is None or df.empty:
        return 0
    col = _find_col(df, *candidates)
    if col:
        return int(df[col].nunique())
    return len(df)


def _sum_num(df, *candidates):
    if df is None or df.empty:
        return 0
    col = _find_col(df, *candidates)
    if col is None:
        return 0
    return int(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())


def _chart_from_series(series, presets):
    empty = [{"label": label, "value": 0} for label, _keys in presets]
    if series is None:
        return empty
    data = series.dropna().astype(str).str.strip()
    if data.empty:
        return empty
    lower = data.str.lower()
    used = pd.Series(False, index=data.index)
    bars = []
    for label, keys in presets:
        mask = False
        for key in keys:
            mask = mask | lower.str.contains(key, regex=False, na=False)
        bars.append({"label": label, "value": int(mask.sum())})
        used = used | mask
    if sum(item["value"] for item in bars) == 0:
        counts = data.value_counts().head(4)
        return [{"label": str(name), "value": int(value)} for name, value in counts.items()]
    leftover = int((~used).sum())
    if leftover and bars:
        bars[-1]["value"] += leftover
    return bars


def _pending_count(df, kind="inbound"):
    if df is None or df.empty:
        return 0
    status = _find_col(df, "Status", "Order Status", "LPN Status")
    if kind == "inbound":
        if "_rcv_hours" in df and df["_rcv_hours"].isna().any():
            missing = int(df["_rcv_hours"].isna().sum())
            if missing:
                return missing
        if "_rcv_hit" in df:
            return int((~df["_rcv_hit"].fillna(False)).sum())
        if status is None:
            return 0
        pending = df[status].astype(str).str.contains(r"pend|open|arriv|transit", case=False, na=False)
        return int(pending.sum())
    if status is None:
        return 0
    pending = df[status].astype(str).str.contains(r"pend|open|creat|allocat|picked|packed|in.?progress", case=False, na=False)
    if pending.any():
        return int(pending.sum())
    done = df[status].astype(str).str.contains(r"ship|deliver|complete|close", case=False, na=False)
    return int((~done).sum())


def _healthcare_block(sheets, key, name):
    ib = _load_inbound(sheets, key)
    oh = _orders_for(sheets, key)
    ob = _filter_company(sheets.get("oblpn"), key)
    lpn = _filter_company(sheets.get("iblpn"), key)
    color = IFFCO_DOT if key == "iffco" else (ARAMCO_DOT if key == "aramco" else "#2563eb")

    shipments = _nunique(ib, "Shipment Nbr", "Shipment", "ASN", "IB Shipment")
    vehicles = _nunique(ib, "Vehicle", "Trailer", "Truck", "Vehicle Nbr", "Truck ID") or shipments
    pallets = _sum_num(ib, "Pallets", "Pallet", "Pallet Count", "No of Pallets")
    if not pallets:
        pallets = _nunique(lpn, "LPN Nbr", "LPN", "LPN Number") or len(lpn)
    quantity = _sum_num(ib, "Total Qty", "Quantity", "Qty", "Total Quantity")
    if not quantity:
        quantity = _sum_num(lpn, "Current Qty", "Qty", "Quantity", "On Hand Qty")
    lines = _sum_num(ib, "Lines", "Line", "Number of Line", "No of Lines") or len(ib)
    pending_ib = 0
    if ib is not None and not ib.empty:
        if "_rcv_hours" in ib and ib["_rcv_hours"].notna().any():
            pending_ib = int(ib["_rcv_hours"].isna().sum())
        else:
            pending_ib = _pending_count(ib, "inbound")

    type_series = ib[_find_col(ib, "Type", "Shipment Type", "IB Type")] if ib is not None and not ib.empty and _find_col(ib, "Type", "Shipment Type", "IB Type") else None
    temp_series = ib[_find_col(ib, "Temperature", "Temp", "Storage Type", "Temp Type")] if ib is not None and not ib.empty and _find_col(ib, "Temperature", "Temp", "Storage Type", "Temp Type") else None
    types = _chart_from_series(
        type_series,
        (("Bulk", ("bulk", "ftl", "full")), ("Loose", ("loose", "ltl", "mix", "carton", "standard"))),
    )
    temps = _chart_from_series(
        temp_series,
        (("Cold", ("cold", "chill")), ("Frozen", ("frozen", "freeze")), ("Ambient", ("ambient", "dry", "normal"))),
    )
    if temp_series is None:
        total_ib = shipments or len(ib) if ib is not None else 0
        temps = [
            {"label": "Cold", "value": 0},
            {"label": "Frozen", "value": 0},
            {"label": "Ambient", "value": total_ib},
        ]

    lane_col = "_lane" if oh is not None and not oh.empty and "_lane" in oh else None
    tender = int((oh["_lane"] == "local").sum()) if lane_col else 0
    private = int((oh["_lane"] == "remote").sum()) if lane_col else 0
    if not tender and not private:
        type_oh = _find_col(oh, "Type", "Order Type", "Shipping Type", "Transport Type") if oh is not None and not oh.empty else None
        if type_oh:
            bars = _chart_from_series(oh[type_oh], (("Tender", ("tender", "contract", "local")), ("Private", ("private", "own", "remote"))))
            tender = bars[0]["value"] if bars else 0
            private = bars[1]["value"] if len(bars) > 1 else 0
        else:
            tender = len(oh) if oh is not None else 0
            private = 0
    ob_type = _find_col(ob, "Type", "LPN Type", "Order Type") if ob is not None and not ob.empty else None
    ob_types = _chart_from_series(
        ob[ob_type] if ob_type else None,
        (("Bulk", ("bulk", "ftl", "full")), ("Loose", ("loose", "ltl", "mix", "carton", "standard"))),
    )
    ob_lines = _nunique(ob, "LPN Nbr", "LPN", "OBLPN") or len(ob) if ob is not None else 0
    ob_qty = _sum_num(ob, "Current Qty", "Qty", "Quantity", "Packed Qty") or len(oh) if oh is not None else 0
    ob_pending = _pending_count(oh, "outbound")

    occupied = _nunique(lpn, "LPN Nbr", "LPN") if lpn is not None and not lpn.empty else 0
    status_col = _find_col(lpn, "Status", "LPN Status") if lpn is not None and not lpn.empty else None
    located = occupied
    received = 0
    if status_col:
        located = int(lpn[status_col].astype(str).str.contains("located", case=False, na=False).sum()) or occupied
        received = int(lpn[status_col].astype(str).str.contains("received", case=False, na=False).sum())
    loc_col = _find_col(lpn, "Location", "Current Location", "Loc") if lpn is not None and not lpn.empty else None
    storage = int(lpn[loc_col].nunique()) if loc_col else located + received
    if not storage:
        storage = located + received
    available = max(storage - located, received)

    return {
        "key": key,
        "name": name,
        "dot_color": color,
        "inbound": {
            "vehicles": vehicles,
            "pallets": pallets,
            "shipments": shipments or len(ib) if ib is not None else 0,
            "pending": pending_ib,
            "quantity": quantity,
            "lines": lines,
            "types": types,
            "temps": temps,
        },
        "outbound": {
            "tender": tender,
            "private": private,
            "bulk": ob_types[0]["value"] if ob_types else 0,
            "loose": ob_types[1]["value"] if len(ob_types) > 1 else 0,
            "lines": ob_lines or (len(oh) if oh is not None else 0),
            "quantity": ob_qty,
            "pending": ob_pending,
        },
        "capacity": {
            "wh_storage": storage,
            "occupied": located,
            "available": available,
        },
        "inventory": {"last_movement": received or located},
    }


def _healthcare(sheets):
    companies = []
    found = discover_companies(sheets) or [
        {"key": "iffco", "name": "IFFCO"},
        {"key": "aramco", "name": "ARAMCO"},
    ]
    preferred = [item for item in found if item["key"] in ("iffco", "aramco")]
    rest = [item for item in found if item["key"] not in ("iffco", "aramco")]
    for item in preferred + rest:
        companies.append(_healthcare_block(sheets, item["key"], item["name"]))
    return {
        "year_range": _year_range(sheets),
        "companies": companies,
    }


def combine_dashboard(companies):
    inbound = {"vehicles": 0, "pallets": 0, "shipments": 0, "pending": 0, "quantity": 0, "lines": 0, "types": [], "temps": []}
    outbound = {"tender": 0, "private": 0, "bulk": 0, "loose": 0, "lines": 0, "quantity": 0, "pending": 0}
    capacity = {"wh_storage": 0, "occupied": 0, "available": 0}
    inventory = {"last_movement": 0}
    type_map, temp_map = {}, {}
    for company in companies or []:
        ib = company.get("inbound") or {}
        ob = company.get("outbound") or {}
        cap = company.get("capacity") or {}
        inv = company.get("inventory") or {}
        for key in ("vehicles", "pallets", "shipments", "pending", "quantity", "lines"):
            inbound[key] += int(ib.get(key) or 0)
        for key in ("tender", "private", "bulk", "loose", "lines", "quantity", "pending"):
            outbound[key] += int(ob.get(key) or 0)
        for key in ("wh_storage", "occupied", "available"):
            capacity[key] += int(cap.get(key) or 0)
        inventory["last_movement"] += int(inv.get("last_movement") or 0)
        for item in ib.get("types") or []:
            type_map[item["label"]] = type_map.get(item["label"], 0) + int(item.get("value") or 0)
        for item in ib.get("temps") or []:
            temp_map[item["label"]] = temp_map.get(item["label"], 0) + int(item.get("value") or 0)
    inbound["types"] = [{"label": label, "value": value} for label, value in type_map.items()] or [
        {"label": "Bulk", "value": 0}, {"label": "Loose", "value": 0}
    ]
    inbound["temps"] = [{"label": label, "value": value} for label, value in temp_map.items()] or [
        {"label": "Cold", "value": 0}, {"label": "Frozen", "value": 0}, {"label": "Ambient", "value": 0}
    ]
    type_max = max((item["value"] for item in inbound["types"]), default=1) or 1
    temp_max = max((item["value"] for item in inbound["temps"]), default=1) or 1
    orders_total = outbound["tender"] + outbound["private"] or 1
    type_total = outbound["bulk"] + outbound["loose"] or 1
    return {
        "inbound": inbound,
        "outbound": outbound,
        "capacity": capacity,
        "inventory": inventory,
        "type_max": type_max,
        "temp_max": temp_max,
        "tender_pct": round(100 * outbound["tender"] / orders_total),
        "private_pct": round(100 * outbound["private"] / orders_total),
        "bulk_pct": round(100 * outbound["bulk"] / type_total),
        "loose_pct": round(100 * outbound["loose"] / type_total),
        "orders_total": outbound["tender"] + outbound["private"],
    }


def _pages_from_sheets(sheets, warehouse="all", page=None, company="all"):
    builders = {
        "overview": lambda: _overview(sheets),
        "outbound": lambda: _outbound(sheets, warehouse=warehouse),
        "inbound": lambda: _inbound(sheets),
        "cities": lambda: _cities(sheets),
        "inventory": lambda: _inventory(sheets),
        "sla": lambda: _sla(sheets, company=company),
        "misses": lambda: _misses(sheets),
        "dashboard": lambda: _healthcare(sheets),
    }
    if page in builders:
        pages = {page: builders[page]()}
    else:
        pages = {"overview": builders["overview"]()}
    pages["filter_companies"] = discover_companies(sheets)
    pages["filter_warehouses"] = discover_warehouses(sheets)
    return pages


_SHEET_CACHE = {}
_PAGE_CACHE = {}


PAGE_SHEETS = {
    "overview": ("orderheader", "oblpn", "ibshipments"),
    "outbound": ("orderheader", "oblpn"),
    "inbound": ("ibshipments",),
    "cities": ("orderheader", "oblpn", "ibshipments"),
    "inventory": ("iblpn",),
    "sla": ("orderheader", "oblpn", "ibshipments"),
    "misses": ("orderheader", "oblpn", "ibshipments"),
    "dashboard": ("orderheader", "oblpn", "ibshipments", "iblpn"),
}


def get_sheets(needed=None):
    path = find_excel_path()
    if not path:
        return None
    key = (str(path), path.stat().st_mtime)
    wanted = tuple(needed or NEEDED_SHEETS)
    cached = _SHEET_CACHE.get("key")
    sheets = _SHEET_CACHE.get("sheets") if cached == key else {}
    if cached != key:
        sheets = {}
    missing = [name for name in wanted if name not in sheets]
    if missing:
        loaded = _read_workbook(path, only=missing)
        sheets.update(loaded)
        sheets.pop("_prep", None)
        _SHEET_CACHE["key"] = key
        _SHEET_CACHE["sheets"] = sheets
    return sheets


def clear_cache():
    _PAGE_CACHE.clear()
    _SHEET_CACHE.clear()


def load_dashboard(company="all", warehouse="all", page="overview"):
    path = find_excel_path()
    if not path:
        return None, "sample"
    try:
        mtime = path.stat().st_mtime
        page_key = page or "overview"
        warehouse_key = warehouse or "all"
        sla_path = sla_settings._path()
        try:
            sla_stamp = sla_path.stat().st_mtime
        except OSError:
            sla_stamp = 0
        cache_key = (
            str(path),
            mtime,
            warehouse_key,
            page_key,
            company if page_key == "sla" else "all",
            sla_stamp,
        )
        pages = _PAGE_CACHE.get(cache_key)
        if pages is None:
            sheets = get_sheets(PAGE_SHEETS.get(page_key, NEEDED_SHEETS))
            if not sheets:
                return None, "empty"
            pages = _pages_from_sheets(
                sheets,
                warehouse=warehouse_key,
                page=page_key,
                company=company or "all",
            )
            _PAGE_CACHE[cache_key] = pages
        else:
            pages = dict(pages)
        sheets = get_sheets(PAGE_SHEETS.get(page_key, NEEDED_SHEETS))
        pages["filter_companies"] = discover_companies(sheets) if sheets else []
        pages["filter_warehouses"] = discover_warehouses(sheets, company) if sheets else []
        return pages, "excel"
    except Exception:
        import traceback
        traceback.print_exc()
        return None, "error"


def dummy_pages():
    return {
        "overview": dummy_data.OVERVIEW,
        "outbound": dummy_data.OUTBOUND,
        "inbound": dummy_data.INBOUND,
        "cities": dummy_data.CITIES,
        "inventory": dummy_data.INVENTORY,
        "sla": dummy_data.SLA,
        "misses": dummy_data.MISSES,
        "dashboard": dummy_data.DASHBOARD,
    }
