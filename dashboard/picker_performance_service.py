"""
Aggregations and Excel parsing for Picker Performance (files/Picking .xlsx · Data).
Each SAP/Data row = one picked line. Business column is the company name.
"""

from __future__ import annotations

import io
import math
import re
from calendar import monthrange
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

SHIFT_S1 = "S1"
SHIFT_S2 = "S2"
SHIFT_S3 = "S3"

SHIFT_LABELS = {
    SHIFT_S1: "S1 (06:00–15:00)",
    SHIFT_S2: "S2 (15:00–00:00)",
    SHIFT_S3: "S3 (00:00–06:00)",
}

WEEKDAYS_EN = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


def _norm_header(s: Any) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    t = str(s).strip().lower().replace("\n", " ")
    t = re.sub(r"\s+", " ", t)
    return t


def _pick_column(norm_map: dict[str, str], aliases: set[str]) -> str | None:
    best_col = None
    best_score = -1
    for col, norm in norm_map.items():
        if not norm:
            continue
        score = 0
        if norm in aliases:
            score = 100
        else:
            for a in aliases:
                if len(a) <= 1:
                    continue
                if a == norm:
                    score = max(score, 100)
                elif norm.startswith(a + " ") or norm.endswith(" " + a) or (" " + a + " ") in norm:
                    score = max(score, 40)
                elif a in norm:
                    score = max(score, 20)
                elif norm in a and len(norm) >= 4:
                    score = max(score, 10)
        if score > best_score:
            best_score = score
            best_col = col
    return best_col if best_score >= 10 else None


def _excel_col_index(letter: str) -> int:
    """Excel column letter → 0-based index (A=0, R=17)."""
    letter = letter.strip().upper()
    n = 0
    for ch in letter:
        if not ("A" <= ch <= "Z"):
            continue
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def _resolve_picker_column(norm_map: dict[str, str]) -> str | None:
    """
    Picker confirmation user = SAP column R (second ``User`` header).
    """
    r_col = f"c{_excel_col_index('R')}"
    q_col = f"c{_excel_col_index('Q')}"
    if norm_map.get(r_col) == "user":
        return r_col

    user_cols = sorted(
        (k for k, v in norm_map.items() if v == "user"),
        key=lambda k: int(k[1:]),
    )
    if len(user_cols) >= 2 and norm_map.get(q_col) == "user":
        return user_cols[-1]
    if len(user_cols) >= 2:
        return user_cols[-1]

    col = _pick_column(
        norm_map,
        {"user.1", "user 1", "user1", "picker", "picker name"},
    )
    if col:
        return col

    if user_cols:
        return user_cols[0]

    return None


def _resolve_type_column(norm_map: dict[str, str]) -> str | None:
    """Role/type label from an explicit Type column — not Source Storage Type."""
    exact = {"type", "user type", "role", "picker type"}
    for col, norm in norm_map.items():
        if norm in exact:
            return col
    s_col = f"c{_excel_col_index('S')}"
    if norm_map.get(s_col) == "type":
        return s_col
    return None


def _dominant_label(values: list[str]) -> str:
    cleaned = [v.strip() for v in values if v and str(v).strip().lower() not in ("", "nan")]
    if not cleaned:
        return ""
    return Counter(cleaned).most_common(1)[0][0]


def _resolve_sheet_name(xl: pd.ExcelFile, requested: str) -> str:
    names = list(xl.sheet_names)
    if not names:
        raise ValueError("Workbook has no sheets.")
    if len(names) == 1:
        return names[0]
    req = (requested or "").strip()
    if not req:
        return names[0]
    if req in names:
        return req
    by_lower = {str(n).strip().lower(): n for n in names}
    if req.lower() in by_lower:
        return by_lower[req.lower()]
    for cand in ("data", "sap", "sheet1", "dashboard"):
        if cand in by_lower:
            return by_lower[cand]
    avail = ", ".join(names[:20])
    raise ValueError(f"Sheet {requested!r} not found. Available: {avail}")


def _detect_header_row(df: pd.DataFrame, max_scan: int = 30) -> int:
    best_i = 0
    best_score = -1
    limit = min(max_scan, len(df))
    for i in range(limit):
        cells = [_norm_header(x) for x in df.iloc[i].tolist()]
        score = 0
        joined = " ".join(cells)
        if any("user" in c for c in cells) or any("picker" in c for c in cells):
            score += 3
        if any(c in ("business", "company") for c in cells):
            score += 3
        if any("source storage" in c or "storage bin" in c for c in cells):
            score += 3
        if any("confirmation" in c for c in cells):
            score += 2
        if any("creation" in c for c in cells):
            score += 1
        if any("delivery" in c for c in cells):
            score += 1
        if score > best_score:
            best_score = score
            best_i = i
    return best_i


def _parse_datetime(val: Any) -> datetime | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime.combine(val, datetime.min.time())
    try:
        ts = pd.to_datetime(val, dayfirst=True)
        if pd.isna(ts):
            return None
        return ts.to_pydatetime()
    except Exception:
        return None


def _combine_date_time(d_val: Any, t_val: Any) -> datetime | None:
    dt = _parse_datetime(d_val)
    if dt is None:
        return None
    if t_val is None or (isinstance(t_val, float) and pd.isna(t_val)):
        return dt
    if isinstance(t_val, datetime):
        return datetime.combine(dt.date(), t_val.time())
    if isinstance(t_val, time):
        return datetime.combine(dt.date(), t_val)
    if isinstance(t_val, timedelta):
        base = datetime.combine(dt.date(), datetime.min.time())
        return base + t_val
    try:
        frac = float(t_val)
        if 0 <= frac < 1:
            seconds = int(round(frac * 86400))
            base = datetime.combine(dt.date(), datetime.min.time())
            return base + timedelta(seconds=seconds)
    except (TypeError, ValueError):
        pass
    tt = _parse_datetime(t_val)
    if tt is not None:
        return datetime.combine(dt.date(), tt.time())
    return dt


def _is_empty_cell(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, float) and pd.isna(val):
        return True
    if isinstance(val, str) and not val.strip():
        return True
    return False


def _hour_from_time_raw(raw: Any) -> float | None:
    """Extract hour-of-day (0–24) from Excel time cell."""
    if _is_empty_cell(raw):
        return None
    if isinstance(raw, datetime):
        return raw.hour + raw.minute / 60 + raw.second / 3600
    if isinstance(raw, time):
        return raw.hour + raw.minute / 60 + raw.second / 3600
    if isinstance(raw, timedelta):
        return (raw.total_seconds() / 3600) % 24
    if isinstance(raw, str):
        s = raw.strip()
        if ":" in s:
            parts = s.split(":")
            try:
                h = int(parts[0])
                m = int(parts[1]) if len(parts) > 1 else 0
                sec = float(parts[2]) if len(parts) > 2 else 0
                return h + m / 60 + sec / 3600
            except (TypeError, ValueError):
                pass
    try:
        frac = float(raw)
        if 0 <= frac < 1:
            return frac * 24
        if 0 <= frac <= 24:
            return frac
    except (TypeError, ValueError):
        pass
    dt = _parse_datetime(raw)
    if dt is not None:
        return dt.hour + dt.minute / 60 + dt.second / 3600
    return None


def classify_shift_from_hour(hour: float) -> str:
    """S1: 06–15, S2: 15–24, S3: 00–06 (from Confirmation time × 24)."""
    if 6 <= hour < 15:
        return SHIFT_S1
    if 15 <= hour < 24:
        return SHIFT_S2
    return SHIFT_S3


def shift_from_confirmation_time(raw: Any) -> str | None:
    hour = _hour_from_time_raw(raw)
    if hour is None:
        return None
    return classify_shift_from_hour(hour)


def resolve_shift_band(time_raw: Any, conf_dt: datetime | None) -> str:
    """Prefer Confirmation time column; fall back to combined confirmation datetime."""
    if not _is_empty_cell(time_raw):
        band = shift_from_confirmation_time(time_raw)
        if band is not None:
            return band
    if conf_dt is not None:
        band = shift_from_confirmation_time(conf_dt)
        if band is not None:
            return band
    return SHIFT_S3


def normalize_shift_code(raw: str | None) -> str:
    """Map legacy / alias shift labels to S1|S2|S3."""
    if not raw:
        return SHIFT_S3
    s = str(raw).strip().upper()
    if s in (SHIFT_S1, "MORNING", "1"):
        return SHIFT_S1
    if s in (SHIFT_S2, "EVENING", "2"):
        return SHIFT_S2
    if s in (SHIFT_S3, "NIGHT", "3", "OTHER"):
        return SHIFT_S3
    return s if s in (SHIFT_S1, SHIFT_S2, SHIFT_S3) else SHIFT_S3


def mixed_target(pick_count: int, other_count: int, total_lines: int) -> int:
    if total_lines <= 0:
        return 0
    return round((pick_count * 200 + other_count * 150) / total_lines)


def _half_split_delta(daily_values: list[float]) -> tuple[float | None, str]:
    """Compare avg of second half vs first half of chronologically ordered daily values."""
    n = len(daily_values)
    if n < 2:
        return None, "flat"
    mid = n // 2
    first = daily_values[:mid]
    second = daily_values[mid:]
    if not first or not second:
        return None, "flat"
    a = sum(first) / len(first)
    b = sum(second) / len(second)
    d = b - a
    direction = "up" if d > 0 else ("down" if d < 0 else "flat")
    return round(d, 1), direction


def parse_sap_sheet(
    file_obj: Any,
    sheet_name: str = "Data",
) -> tuple[list[dict[str, Any]], str]:
    """
    Read line-level picker rows from files/Picking .xlsx (sheet Data).

    Returns (rows, resolved_sheet_name). Each row dict:
    work_date, picker_name, business, is_pick, shift_band (S1|S2|S3),
    pick_duration_min, delivery_number, lines (always 1).
    """
    raw = file_obj.read() if hasattr(file_obj, "read") else file_obj
    buf = io.BytesIO(raw) if not isinstance(raw, io.BytesIO) else raw

    try:
        xl = pd.ExcelFile(buf, engine="openpyxl")
    except Exception as e:
        raise ValueError(f"Could not read Excel file: {e}") from e

    resolved = _resolve_sheet_name(xl, sheet_name)
    df = pd.read_excel(xl, sheet_name=resolved, header=None)
    header_idx = _detect_header_row(df)
    header_row = df.iloc[header_idx].tolist()
    body = df.iloc[header_idx + 1 :].dropna(how="all")

    norm_map = {f"c{i}": _norm_header(h) for i, h in enumerate(header_row)}

    col_picker = _resolve_picker_column(norm_map)
    col_bin = _pick_column(
        norm_map,
        {"source storage bin", "source storage", "storage bin", "source bin"},
    )
    col_conf_date = _pick_column(
        norm_map,
        {"confirmation date", "confirm date"},
    )
    col_conf_time = _pick_column(
        norm_map,
        {
            "confirmation time",
            "confirm time",
            "confirmation time x 24",
            "conf time",
            "conf. time",
        },
    )
    col_conf_dt = _pick_column(
        norm_map,
        {"confirmation date+time", "confirmation datetime", "confirmation date time"},
    )
    col_create_date = _pick_column(
        norm_map,
        {"creation date", "create date", "created date"},
    )
    col_create_time = _pick_column(
        norm_map,
        {"creation time", "create time", "created time"},
    )
    col_create_dt = _pick_column(
        norm_map,
        {"creation date+time", "creation datetime", "creation date time"},
    )
    col_delivery = _pick_column(
        norm_map,
        {
            "transfer order number",
            "transfer order",
            "transfer order no",
            "transfer order #",
            "delivery",
            "delivery number",
            "delivery no",
            "delivery document",
        },
    )
    col_type = _resolve_type_column(norm_map)
    col_business = _pick_column(
        norm_map,
        {"business", "company", "account", "customer", "sold-to", "sold to"},
    )

    if not col_picker:
        found = [f"{k}={v}" for k, v in norm_map.items() if v]
        raise ValueError(
            "Could not find Picker column (User · column R). "
            f"Detected headers (row {header_idx + 1}): {found[:25]}"
        )

    pi = int(col_picker[1:])
    bi = int(col_bin[1:]) if col_bin else None
    cdi = int(col_conf_date[1:]) if col_conf_date else None
    cti = int(col_conf_time[1:]) if col_conf_time else None
    cdti = int(col_conf_dt[1:]) if col_conf_dt else None
    crdi = int(col_create_date[1:]) if col_create_date else None
    crti = int(col_create_time[1:]) if col_create_time else None
    crdti = int(col_create_dt[1:]) if col_create_dt else None
    deli = int(col_delivery[1:]) if col_delivery else None
    ti = int(col_type[1:]) if col_type else None
    bsi = int(col_business[1:]) if col_business else None

    rows: list[dict[str, Any]] = []
    for _, r in body.iterrows():
        picker = r.iloc[pi] if pi < len(r) else None
        if picker is None or (isinstance(picker, float) and pd.isna(picker)):
            continue
        picker_name = str(picker).strip()
        if not picker_name or picker_name.lower() == "nan":
            continue

        bin_val = r.iloc[bi] if bi is not None and bi < len(r) else ""
        bin_str = "" if bin_val is None or (isinstance(bin_val, float) and pd.isna(bin_val)) else str(bin_val).strip()
        is_pick = bin_str[:4].upper() == "PICK"

        if cdti is not None and cdti < len(r):
            conf_dt = _parse_datetime(r.iloc[cdti])
        elif cdi is not None and cdi < len(r):
            conf_dt = _combine_date_time(r.iloc[cdi], r.iloc[cti] if cti is not None and cti < len(r) else None)
        else:
            conf_dt = None

        if crdti is not None and crdti < len(r):
            create_dt = _parse_datetime(r.iloc[crdti])
        elif crdi is not None and crdi < len(r):
            create_dt = _combine_date_time(
                r.iloc[crdi], r.iloc[crti] if crti is not None and crti < len(r) else None
            )
        else:
            create_dt = None

        pick_duration_min: float | None = None
        if conf_dt and create_dt:
            pick_duration_min = (conf_dt - create_dt).total_seconds() / 60.0
            if pick_duration_min < 0 or not math.isfinite(pick_duration_min):
                pick_duration_min = None

        time_raw = r.iloc[cti] if cti is not None and cti < len(r) else None
        shift_band = resolve_shift_band(time_raw, conf_dt)

        work_date = conf_dt.date() if conf_dt else None

        delivery = ""
        if deli is not None and deli < len(r):
            dv = r.iloc[deli]
            if dv is not None and not (isinstance(dv, float) and pd.isna(dv)):
                delivery = str(dv).strip()

        picker_type = ""
        if ti is not None and ti < len(r):
            tv = r.iloc[ti]
            if tv is not None and not (isinstance(tv, float) and pd.isna(tv)):
                picker_type = str(tv).strip()

        business = ""
        if bsi is not None and bsi < len(r):
            bv = r.iloc[bsi]
            if bv is not None and not (isinstance(bv, float) and pd.isna(bv)):
                business = str(bv).strip()
                if business.lower() in ("nan", "none", "-"):
                    business = ""

        rows.append(
            {
                "work_date": work_date,
                "picker_name": picker_name,
                "picker_type": picker_type,
                "business": business,
                "is_pick": is_pick,
                "shift_band": shift_band,
                "pick_duration_min": pick_duration_min,
                "delivery_number": delivery,
                "lines": 1,
            }
        )

    return rows, resolved


def load_lines_from_workbook_path(
    path: Path | str,
    sheet_name: str,
) -> list[dict[str, Any]]:
    path = Path(path)
    with path.open("rb") as f:
        rows, _ = parse_sap_sheet(f, sheet_name=sheet_name)
        return rows


def serialize_lines_for_client(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compact line dicts for browser-side filter + re-aggregation."""
    out: list[dict[str, Any]] = []
    for ln in lines:
        wd = ln.get("work_date")
        pm = ln.get("pick_duration_min")
        out.append(
            {
                "p": ln["picker_name"],
                "d": wd.isoformat() if wd else "",
                "ip": 1 if ln.get("is_pick") else 0,
                "s": normalize_shift_code(ln.get("shift_band")),
                "pm": round(pm, 2) if pm is not None else None,
                "dn": ln.get("delivery_number", "") or "",
                "ty": ln.get("picker_type", "") or "",
                "b": ln.get("business", "") or "",
            }
        )
    return out


def build_filter_meta(lines: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Date filter options: single calendar month → all days 1..last;
    multiple months in data → month labels (e.g. Oct 2025).
    """
    pickers = sorted({ln["picker_name"] for ln in lines})
    type_options = sorted(
        {
            (ln.get("picker_type") or "").strip()
            for ln in lines
            if (ln.get("picker_type") or "").strip()
        }
    )
    business_options = sorted(
        {
            (ln.get("business") or "").strip()
            for ln in lines
            if (ln.get("business") or "").strip()
        }
    )
    dated = [ln for ln in lines if ln.get("work_date") is not None]
    if not dated:
        return {
            "date_mode": "days",
            "date_options": [{"value": "", "label": "All"}],
            "pickers": pickers,
            "type_options": type_options,
            "business_options": business_options,
        }

    months = sorted({(ln["work_date"].year, ln["work_date"].month) for ln in dated})
    date_options: list[dict[str, str]] = [{"value": "", "label": "All"}]

    if len(months) == 1:
        y, m = months[0]
        _, last_day = monthrange(y, m)
        for day in range(1, last_day + 1):
            d = date(y, m, day)
            date_options.append({"value": d.isoformat(), "label": d.isoformat()})
        return {
            "date_mode": "days",
            "date_options": date_options,
            "pickers": pickers,
            "type_options": type_options,
            "business_options": business_options,
        }

    for y, m in months:
        date_options.append(
            {
                "value": f"{y}-{m:02d}",
                "label": f"{y}-{m:02d}",
            }
        )
    return {
        "date_mode": "months",
        "date_options": date_options,
        "pickers": pickers,
        "type_options": type_options,
        "business_options": business_options,
    }


def aggregate_table_rows(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build picker table rows from a (possibly filtered) line list."""
    if not lines:
        return []

    by_picker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    picker_daily: dict[str, dict[date, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for ln in lines:
        by_picker[ln["picker_name"]].append(ln)
        wd = ln.get("work_date")
        if wd is not None:
            picker_daily[ln["picker_name"]][wd].append(ln)

    table_rows: list[dict[str, Any]] = []
    for pname, plines in by_picker.items():
        n = len(plines)
        pick_n = sum(1 for x in plines if x.get("is_pick"))
        other_n = n - pick_n
        days_set = {x["work_date"] for x in plines if x.get("work_date")}
        days_count = len(days_set) if days_set else 1
        orders = len({x.get("delivery_number", "") for x in plines if x.get("delivery_number")})
        lines_per_day = n / days_count if days_count else 0.0
        target = mixed_target(pick_n, other_n, n)
        achievement_pct = (lines_per_day / target * 100) if target > 0 else 0.0

        durations = [x["pick_duration_min"] for x in plines if x.get("pick_duration_min") is not None]
        pick_min_avg = round(sum(durations) / len(durations), 1) if durations else None

        day_compl_below = 0
        days_target_missed = 0
        days_target_met = 0
        daily_spark: list[int] = []
        daily_floats: list[float] = []
        if pname in picker_daily:
            for wd in sorted(picker_daily[pname].keys()):
                dl = picker_daily[pname][wd]
                dn = len(dl)
                dp = sum(1 for x in dl if x.get("is_pick"))
                do = dn - dp
                dtgt = mixed_target(dp, do, dn)
                dach = (dn / dtgt * 100) if dtgt > 0 else 0.0
                if dach < 80:
                    day_compl_below += 1
                if dach < 100:
                    days_target_missed += 1
                else:
                    days_target_met += 1
                daily_spark.append(dn)
                daily_floats.append(float(dn))

        trend_delta, trend_dir = _half_split_delta(daily_floats)

        shift_counts = Counter(ln.get("shift_band") or SHIFT_S3 for ln in plines)
        dominant_shift = shift_counts.most_common(1)[0][0] if shift_counts else SHIFT_S3
        picker_type = _dominant_label([str(x.get("picker_type") or "") for x in plines])
        business = _dominant_label([str(x.get("business") or "") for x in plines])

        if achievement_pct >= 100:
            bar_tier = "high"
        elif achievement_pct >= 80:
            bar_tier = "mid"
        else:
            bar_tier = "low"
        bar_w = max(4.0, min(100.0, achievement_pct)) if target > 0 else 0.0

        table_rows.append(
            {
                "picker_name": pname,
                "picker_type": picker_type,
                "business": business,
                "days": days_count,
                "lines": n,
                "pick": pick_n,
                "other": other_n,
                "orders": orders,
                "lines_per_day": round(lines_per_day, 1),
                "target": target,
                "pick_min": pick_min_avg,
                "days_target_met": days_target_met,
                "day_compl_below": day_compl_below,
                "day_compl_total": days_count if days_set else 0,
                "days_target_missed": days_target_missed,
                "shift_band": dominant_shift,
                "shift_label": SHIFT_LABELS.get(dominant_shift, dominant_shift),
                "trend_sparkline": daily_spark,
                "trend_delta": trend_delta,
                "trend_direction": trend_dir,
                "achievement_pct": round(achievement_pct, 1),
                "perf_bar_width_pct": round(bar_w, 1),
                "perf_bar_tier": bar_tier,
            }
        )

    return sorted(table_rows, key=lambda r: -r["lines_per_day"])


def build_performance_context(
    lines: list[dict[str, Any]],
    *,
    period_label: str = "",
) -> dict[str, Any]:
    """Context for home template: summary cards + picker table rows."""
    out: dict[str, Any] = {
        "has_data": bool(lines),
        "period_label": period_label,
        "cards": [],
        "rows": [],
        "picker_count": 0,
    }
    if not lines:
        out["cards"] = _empty_cards()
        out["filter_meta"] = {
            "date_mode": "days",
            "date_options": [{"value": "", "label": "All"}],
            "pickers": [],
            "type_options": [],
            "business_options": [],
            "picker_types": {},
            "picker_businesses": {},
        }
        out["client_lines"] = []
        out["shift_labels"] = SHIFT_LABELS
        out["companies"] = []
        out["company_label"] = ""
        return out

    dated = [ln for ln in lines if ln.get("work_date") is not None]
    operating_days = len({ln["work_date"] for ln in dated}) if dated else 0
    total_lines = len(lines)

    # --- Daily picker-day records for target achievement KPI ---
    daily_rows: list[dict[str, Any]] = []
    picker_daily: dict[str, dict[date, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for ln in dated:
        picker_daily[ln["picker_name"]][ln["work_date"]].append(ln)

    for pname, days_map in picker_daily.items():
        for wd, day_lines in days_map.items():
            n = len(day_lines)
            pick_n = sum(1 for x in day_lines if x.get("is_pick"))
            other_n = n - pick_n
            tgt = mixed_target(pick_n, other_n, n)
            ach = (n / tgt * 100) if tgt > 0 else 0.0
            daily_rows.append(
                {
                    "picker": pname,
                    "date": wd,
                    "lines": n,
                    "target": tgt,
                    "achievement_pct": ach,
                }
            )

    target_achievement_days = sum(1 for d in daily_rows if d["achievement_pct"] >= 100)
    target_achievement_pct = (
        (target_achievement_days / len(daily_rows) * 100) if daily_rows else 0.0
    )

    # --- Table rows ---
    table_rows = aggregate_table_rows(lines)

    # --- At-risk pickers (Lines/Day ≤ 150) ---
    at_risk = sum(1 for r in table_rows if r["lines_per_day"] <= 150)

    # --- Top / lowest performer ---
    top = max(table_rows, key=lambda r: (r["lines_per_day"], r["lines"]))
    lowest = min(table_rows, key=lambda r: (r["lines_per_day"], -r["lines"]))

    # --- Daily avg lines ---
    daily_avg = (total_lines / operating_days) if operating_days else 0.0

    # --- Total distinct transfer orders ---
    total_orders = len({ln.get("delivery_number") for ln in lines if ln.get("delivery_number")})

    # --- Picker-days where daily target not met (<100%) ---
    days_target_missed_total = len(daily_rows) - target_achievement_days

    # --- Three-shift totals (all period) ---
    s1 = sum(1 for ln in lines if ln.get("shift_band") == SHIFT_S1)
    s2 = sum(1 for ln in lines if ln.get("shift_band") == SHIFT_S2)
    s3 = sum(1 for ln in lines if ln.get("shift_band") == SHIFT_S3)
    shift_main = f"{s1:,} · {s2:,} · {s3:,}"
    shift_sub = "S1 (06–15) · S2 (15–00) · S3 (00–06) lines"

    best_improved_name = "—"
    best_improved_sub = "No positive gain (first → last half of days)"
    best_improved_delta: float | None = None
    for row in table_rows:
        td = row.get("trend_delta")
        if td is not None and td > 0:
            if best_improved_delta is None or td > best_improved_delta:
                best_improved_delta = td
                best_improved_name = row["picker_name"]
                best_improved_sub = f"+{td:.1f} lines (first → last half)"

    cards = [
        {
            "key": "at_risk",
            "title_en": "At-Risk Pickers",
            "value": str(at_risk),
            "sub": "Avg lines ≤ 150 / day",
            "accent": "rose",
        },
        {
            "key": "target_rate",
            "title_en": "Target Achievement",
            "value": f"{target_achievement_pct:.1f}%",
            "sub": f"Picker-days at ≥100% target ({target_achievement_days}/{len(daily_rows)})",
            "accent": "emerald",
        },
        {
            "key": "top",
            "title_en": "Top Performer",
            "value": top["picker_name"],
            "sub": f"Avg {top['lines_per_day']} lines / day",
            "accent": "amber",
        },
        {
            "key": "lowest",
            "title_en": "Lowest Performer",
            "value": lowest["picker_name"],
            "sub": f"Avg {lowest['lines_per_day']} lines / day",
            "accent": "orange",
        },
        {
            "key": "daily_avg",
            "title_en": "Daily Avg Lines",
            "value": f"{daily_avg:.1f}",
            "sub": "Total lines ÷ operating days",
            "accent": "sky",
        },
        {
            "key": "orders",
            "title_en": "Total Orders",
            "value": f"{total_orders:,}",
            "sub": "Distinct Transfer Order Number",
            "accent": "violet",
        },
        {
            "key": "days_missed",
            "title_en": "Days Target Not Met",
            "value": str(days_target_missed_total),
            "sub": f"Picker-days below 100% target (of {len(daily_rows)})",
            "accent": "lime",
        },
        {
            "key": "shift_cmp",
            "title_en": "Shift 1 · 2 · 3",
            "value": shift_main,
            "sub": shift_sub,
            "accent": "blue",
        },
        {
            "key": "mip",
            "title_en": "Most Improved",
            "value": best_improved_name,
            "sub": best_improved_sub,
            "accent": "teal",
        },
    ]

    out["cards"] = cards
    out["rows"] = table_rows
    out["picker_count"] = len(table_rows)
    filter_meta = build_filter_meta(lines)
    filter_meta["picker_types"] = {
        r["picker_name"]: r.get("picker_type") or ""
        for r in table_rows
        if r.get("picker_type")
    }
    filter_meta["picker_businesses"] = {
        r["picker_name"]: r.get("business") or ""
        for r in table_rows
        if r.get("business")
    }
    out["filter_meta"] = filter_meta
    out["client_lines"] = serialize_lines_for_client(lines)
    out["shift_labels"] = SHIFT_LABELS
    companies = filter_meta.get("business_options") or []
    out["companies"] = companies
    out["company_label"] = " · ".join(companies)
    if not period_label and operating_days:
        out["period_label"] = f"{operating_days} operating days"
    return out


def import_picker_shifts_from_excel(
    program: Any,
    file_obj: Any,
    *,
    sheet_name_override: str | None = None,
) -> tuple[int, str]:
    """
    Replace all line rows for the program from the Excel uploaded in Admin.
    Reads the Business column as company name.

    Returns (count_imported, resolved_sheet_name).
    """
    from .models import PickerShiftRecord

    sheet = (sheet_name_override or program.excel_sheet_name or "Data").strip()
    sheet = sheet or "Data"
    rows, resolved = parse_sap_sheet(file_obj, sheet_name=sheet)
    program.excel_sheet_name = resolved[:64]
    PickerShiftRecord.objects.filter(program=program).delete()
    batch = [
        PickerShiftRecord(
            program=program,
            work_date=r["work_date"],
            picker_name=r["picker_name"],
            picker_type=r.get("picker_type", "") or "",
            business=r.get("business", "") or "",
            lines=r.get("lines", 1),
            is_pick=r.get("is_pick", False),
            shift_band=normalize_shift_code(r["shift_band"]),
            pick_duration_min=r.get("pick_duration_min"),
            delivery_number=r.get("delivery_number", ""),
        )
        for r in rows
    ]
    PickerShiftRecord.objects.bulk_create(batch, batch_size=1000)
    program.save()
    return len(batch), resolved


def lines_from_db_rows(records: Any) -> list[dict[str, Any]]:
    """Build line dicts from PickerShiftRecord queryset or list."""
    out = []
    for r in records:
        out.append(
            {
                "work_date": r.work_date,
                "picker_name": r.picker_name,
                "picker_type": getattr(r, "picker_type", "") or "",
                "business": getattr(r, "business", "") or "",
                "is_pick": getattr(r, "is_pick", False),
                "shift_band": normalize_shift_code(r.shift_band),
                "pick_duration_min": getattr(r, "pick_duration_min", None),
                "delivery_number": getattr(r, "delivery_number", "") or "",
                "lines": getattr(r, "lines", 1) or 1,
            }
        )
    return out


# Backward-compatible aliases
shifts_from_db_rows = lines_from_db_rows
parse_dashboard_sheet = parse_sap_sheet
load_shifts_from_workbook_path = load_lines_from_workbook_path


def _empty_cards() -> list[dict[str, Any]]:
    titles = [
        ("at_risk", "At-Risk Pickers"),
        ("target_rate", "Target Achievement"),
        ("top", "Top Performer"),
        ("lowest", "Lowest Performer"),
        ("daily_avg", "Daily Avg Lines"),
        ("orders", "Total Orders"),
        ("days_missed", "Days Target Not Met"),
        ("shift_cmp", "Shift 1 · 2 · 3"),
        ("mip", "Most Improved"),
    ]
    return [
        {
            "key": k,
            "title_en": title,
            "value": "—",
            "sub": "Import PICKING_.xlsx (SAP sheet) from Admin",
            "accent": "slate",
        }
        for k, title in titles
    ]
