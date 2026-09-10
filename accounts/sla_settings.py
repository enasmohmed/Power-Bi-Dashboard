import json
from pathlib import Path

from django.conf import settings

FILE_NAME = "sla_settings.json"
HOUR_PRESETS = (24, 48, 72)
DEFAULTS = {
    "local_h": 48,
    "remote_h": 72,
    "crd_h": 72,
    "transfer_h": 24,
    "cutoff": "14:00",
    "inbound_h": 24,
    "grn_h": 24,
}


def _path():
    root = Path(getattr(settings, "MEDIA_ROOT", settings.BASE_DIR / "media")) / "kpi"
    root.mkdir(parents=True, exist_ok=True)
    return root / FILE_NAME


def load_all():
    path = _path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def get(company_key="all"):
    data = load_all()
    merged = dict(DEFAULTS)
    merged.update(data.get("all") or {})
    if company_key and company_key not in ("all", "", None):
        merged.update(data.get(company_key) or {})
    return merged


def _as_int(value, fallback):
    try:
        number = int(float(str(value).strip()))
    except (TypeError, ValueError):
        return fallback
    return number if 1 <= number <= 720 else fallback


def _as_time(value, fallback):
    text = str(value or "").strip()
    if not text:
        return fallback
    if ":" not in text:
        return fallback
    parts = text.split(":")
    try:
        hour = int(parts[0])
        minute = int(parts[1][:2])
    except (TypeError, ValueError):
        return fallback
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return fallback
    return f"{hour:02d}:{minute:02d}"


def parse_post(payload, company_key="all"):
    current = get(company_key)
    custom_local = payload.get("local_h_custom")
    custom_remote = payload.get("remote_h_custom")
    custom_crd = payload.get("crd_h_custom")
    custom_transfer = payload.get("transfer_h_custom")
    custom_inbound = payload.get("inbound_h_custom")
    custom_grn = payload.get("grn_h_custom")
    return {
        "local_h": _as_int(custom_local or payload.get("local_h"), current["local_h"]),
        "remote_h": _as_int(custom_remote or payload.get("remote_h"), current["remote_h"]),
        "crd_h": _as_int(custom_crd or payload.get("crd_h"), current["crd_h"]),
        "transfer_h": _as_int(custom_transfer or payload.get("transfer_h"), current["transfer_h"]),
        "cutoff": _as_time(payload.get("cutoff"), current["cutoff"]),
        "inbound_h": _as_int(custom_inbound or payload.get("inbound_h"), current["inbound_h"]),
        "grn_h": _as_int(custom_grn or payload.get("grn_h"), current["grn_h"]),
    }


def save(company_key, payload):
    key = company_key or "all"
    data = load_all()
    data[key] = parse_post(payload, key)
    _path().write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data[key]


def fmt_hours(value):
    return f"{int(value)}h"


def fmt_cutoff(value):
    text = _as_time(value, DEFAULTS["cutoff"])
    hour, minute = [int(part) for part in text.split(":")]
    suffix = "AM" if hour < 12 else "PM"
    display = hour % 12 or 12
    return f"{display}:{minute:02d} {suffix}"


def agreement_cards(cfg):
    return [
        {
            "title": "Outbound — Customer Delivery",
            "items": [
                {"key": "local_h", "label": "Inside City (Local) — Despatch", "kind": "hours", "value": cfg["local_h"], "display": f"{cfg['local_h']} Hours"},
                {"key": "remote_h", "label": "Outside City (Remote) — Despatch", "kind": "hours", "value": cfg["remote_h"], "display": f"{cfg['remote_h']} Hours"},
                {"key": "crd_h", "label": "Customer Receiving Date (CRD)", "kind": "hours", "value": cfg["crd_h"], "display": f"{cfg['crd_h']} Hours"},
            ],
        },
        {
            "title": "Outbound — Branch Transfers",
            "items": [
                {"key": "transfer_h", "label": "Shipping from submission", "kind": "hours", "value": cfg["transfer_h"], "display": f"{cfg['transfer_h']} Hours"},
                {"key": "cutoff", "label": "Cut-off for same-day picking", "kind": "time", "value": cfg["cutoff"], "display": fmt_cutoff(cfg["cutoff"])},
            ],
        },
        {
            "title": "Inbound — Receiving",
            "items": [
                {"key": "inbound_h", "label": "System receiving after arrival", "kind": "hours", "value": cfg["inbound_h"], "display": f"{cfg['inbound_h']} Hours"},
            ],
        },
        {
            "title": "Inbound — GRN",
            "items": [
                {"key": "grn_h", "label": "GRN report sharing after arrival", "kind": "hours", "value": cfg["grn_h"], "display": f"{cfg['grn_h']} Hours"},
            ],
        },
    ]
