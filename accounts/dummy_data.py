OVERVIEW = {
    "year_range": "2025 - 2026",
    "companies": [
        {
            "key": "iffco",
            "name": "IFFCO",
            "subtitle": "3PL KPI — KSA Warehouses",
            "period_note": "March 2025  2,470 Orders",
            "period": "Mar 2025",
            "total_outbound": 2470,
            "local": 1798,
            "remote": 672,
            "overall_sla": 97.8,
            "sla_note": "Strong — all warehouses",
            "total_misses": 77,
            "misses_local": 62,
            "misses_remote": 15,
            "misses_note": "Local: 62 - Remote: 15",
            "inbound_kpi": 100,
            "inbound_note": "All within 24h",
            "local_sla": 97.0,
            "remote_sla": 99.8,
            "inbound_sla": 100.0,
            "dot_color": "#e53935",
        },
        {
            "key": "aramco",
            "name": "ARAMCO",
            "subtitle": "3PL KPI — Jeddah Warehouse",
            "period_note": "Aug 2026  197 Orders",
            "period": "Aug 2026",
            "total_outbound": 197,
            "local": 45,
            "remote": 152,
            "overall_sla": 99.0,
            "sla_note": "Excellent performance",
            "total_misses": 2,
            "misses_local": 0,
            "misses_remote": 2,
            "misses_note": "Remote only - Makkah",
            "inbound_kpi": 62.1,
            "inbound_note": "22 shipments exceeded 24h",
            "local_sla": 100.0,
            "remote_sla": 98.7,
            "inbound_sla": 62.1,
            "dot_color": "#43a047",
        },
    ],
}


OUTBOUND = {
    "year_range": "2023 - 2026",
    "companies": [
        {
            "key": "iffco",
            "name": "IFFCO",
            "period": "March 2023",
            "dot_color": "#e53935",
            "layout": "warehouse",
            "table_title": "Hit / Miss by Warehouse",
            "sla_note": "Local 48h — Remote 72h",
            "kpis": [
                {"label": "Local Despatch", "value": "96.6%", "sub": "1,736 Hit / 62 Miss", "tone": "ok"},
                {"label": "Local CRO", "value": "96.4%", "sub": "1,733 Hit / 65 Miss", "tone": "ok"},
                {"label": "Remote Despatch", "value": "98.1%", "sub": "659 Hit / 13 Miss", "tone": "ok"},
                {"label": "Remote CRO", "value": "97.6%", "sub": "643 Hit / 15 Miss", "tone": "ok"},
            ],
            "rows": [
                {"name": "Abha", "dot": "#f59e0b", "local_hit": 65, "local_miss": 3, "local_pct": 95.8, "remote_hit": 92, "remote_miss": None, "remote_pct": 100, "total": 160},
                {"name": "Buraydah", "dot": "#dc2626", "local_hit": 53, "local_miss": 8, "local_pct": 86.9, "remote_hit": 14, "remote_miss": 2, "remote_pct": 87.5, "total": 77},
                {"name": "Jeddah", "dot": "#22c55e", "local_hit": 341, "local_miss": None, "local_pct": 100, "remote_hit": 239, "remote_miss": None, "remote_pct": 100, "total": 580},
                {"name": "Khobar", "dot": "#f59e0b", "local_hit": 293, "local_miss": 9, "local_pct": 97.0, "remote_hit": 312, "remote_miss": 11, "remote_pct": 96.6, "total": 625},
                {"name": "Madinah", "dot": "#22c55e", "local_hit": 137, "local_miss": None, "local_pct": 100, "remote_hit": 1, "remote_miss": None, "remote_pct": 100, "total": 138},
                {"name": "Riyadh", "dot": "#f59e0b", "local_hit": 803, "local_miss": 41, "local_pct": 95.1, "remote_hit": None, "remote_miss": None, "remote_pct": None, "total": 844},
                {"name": "Tabuk", "dot": "#22c55e", "local_hit": 44, "local_miss": 1, "local_pct": 97.8, "remote_hit": 1, "remote_miss": None, "remote_pct": 100, "total": 46},
            ],
            "totals": {
                "local_hit": 1736, "local_miss": 62, "local_pct": 96.6,
                "remote_hit": 659, "remote_miss": 13, "remote_pct": 98.1, "total": 2470,
            },
        },
        {
            "key": "aramco",
            "name": "ARAMCO",
            "period": "Aug 2026",
            "dot_color": "#43a047",
            "layout": "city",
            "table_title": "Hit / Miss by City",
            "sla_note": "Local 48h — Remote 72h",
            "kpis": [
                {"label": "Local Despatch (48h)", "value": "100%", "sub": "45/45 orders", "tone": "ok"},
                {"label": "Remote Despatch (72h)", "value": "98.7%", "sub": "150/152 orders", "tone": "ok"},
                {"label": "Total Misses", "value": "2", "sub": "Makkah remote orders", "tone": "bad"},
                {"label": "Overall", "value": "99.0%", "sub": "195/197 orders", "tone": "ok"},
            ],
            "rows": [
                {"name": "Jeddah", "dot": "#22c55e", "orders": 45, "hit": 45, "miss": None, "sla": 100, "status": "Perfect"},
                {"name": "Riyadh", "dot": "#22c55e", "orders": 9, "hit": 9, "miss": None, "sla": 100, "status": "Perfect"},
                {"name": "Madinah", "dot": "#22c55e", "orders": 5, "hit": 5, "miss": None, "sla": 100, "status": "Perfect"},
                {"name": "Dammam", "dot": "#22c55e", "orders": 5, "hit": 5, "miss": None, "sla": 100, "status": "Perfect"},
                {"name": "Makkah", "dot": "#f59e0b", "orders": 4, "hit": 3, "miss": 1, "sla": 75.0, "status": "Watch"},
                {"name": "Tabuk", "dot": "#22c55e", "orders": 4, "hit": 4, "miss": None, "sla": 100, "status": "Perfect"},
                {"name": "Yanbu", "dot": "#22c55e", "orders": 4, "hit": 4, "miss": None, "sla": 100, "status": "Perfect"},
                {"name": "Other Cities", "dot": "#22c55e", "orders": 118, "hit": 117, "miss": 1, "sla": 99.2, "status": "Hit"},
            ],
            "totals": {
                "orders": 197, "hit": 195, "miss": 2, "sla": 99.0, "status": "99.0%",
            },
        },
    ],
}


INBOUND = {
    "year_range": "2025 - 2026",
    "companies": [
        {
            "key": "iffco",
            "name": "IFFCO",
            "period": "March 2025",
            "subtitle": "",
            "dot_color": "#e53935",
            "layout": "warehouse",
            "table_title": "Inbound by Warehouse — IFFCO",
            "sla_note": "Target: 24h",
            "kpis": [
                {"label": "System Receiving", "value": "100%", "sub": "All within 24h", "tone": "ok"},
                {"label": "GRN Sharing", "value": "100%", "sub": "All on time", "tone": "ok"},
                {"label": "All Warehouses", "value": "7/7", "sub": "Perfect compliance", "tone": "ok"},
                {"label": "Inbound SLA", "value": "100%", "sub": "Target: 24 hours", "tone": "ok"},
            ],
            "rows": [
                {"name": "Abha", "receiving": 100, "grn": 100, "status": "On Track"},
                {"name": "Buraydah", "receiving": 100, "grn": 100, "status": "On Track"},
                {"name": "Jeddah", "receiving": 100, "grn": 100, "status": "On Track"},
                {"name": "Khobar", "receiving": 100, "grn": 100, "status": "On Track"},
                {"name": "Madinah", "receiving": 100, "grn": 100, "status": "On Track"},
                {"name": "Riyadh", "receiving": 100, "grn": 100, "status": "On Track"},
                {"name": "Tabuk", "receiving": 100, "grn": 100, "status": "On Track"},
            ],
            "totals": {"receiving": 100, "grn": 100, "status": "100%"},
        },
        {
            "key": "aramco",
            "name": "ARAMCO",
            "period": "Aug 2025",
            "subtitle": "58 Shipments",
            "dot_color": "#43a047",
            "layout": "shipments",
            "table_title": "Inbound Shipments — SLA (24h)",
            "sla_note": "Target: 24h",
            "kpis": [
                {"label": "Inbound SLA (24h)", "value": "62.1%", "sub": "36 Hit / 22 Miss", "tone": "warn"},
                {"label": "Shipments Missed", "value": "22", "sub": "Exceeded 24h window", "tone": "bad"},
                {"label": "Total Shipments", "value": "58", "sub": "Standard + Returns", "tone": "info"},
                {"label": "Avg Miss Duration", "value": "~35h", "sub": "Most: 31-40h range", "tone": "warn"},
            ],
            "rows": [
                {"shipment": "SHARAMCO...88122", "type": "Return", "arrival": "2026-08-17", "hours": 14.1, "hours_width": 35.3, "hours_tone": "ok", "rcv": 100, "status": "On Time"},
                {"shipment": "1329862828", "type": "Standard", "arrival": "2026-08-12", "hours": 15.5, "hours_width": 38.8, "hours_tone": "ok", "rcv": 100, "status": "On Time"},
                {"shipment": "1329882811", "type": "Standard", "arrival": "2026-08-10", "hours": 38.6, "hours_width": 96.5, "hours_tone": "bad", "rcv": 88.8, "status": "Late"},
                {"shipment": "1329882810", "type": "Standard", "arrival": "2026-08-10", "hours": 14.8, "hours_width": 37.0, "hours_tone": "ok", "rcv": 85.6, "status": "On Time"},
                {"shipment": "1329882809", "type": "Standard", "arrival": "2026-08-09", "hours": 34.8, "hours_width": 87.0, "hours_tone": "warn", "rcv": 89.5, "status": "Late"},
                {"shipment": "1329882808", "type": "Standard", "arrival": "2026-08-08", "hours": 14.1, "hours_width": 35.3, "hours_tone": "ok", "rcv": 100, "status": "On Time"},
                {"shipment": "1329882807", "type": "Standard", "arrival": "2026-08-05", "hours": 39.7, "hours_width": 99.3, "hours_tone": "bad", "rcv": 100, "status": "Late"},
                {"shipment": "1329882806", "type": "Standard", "arrival": "2026-08-05", "hours": 38.4, "hours_width": 96.0, "hours_tone": "bad", "rcv": 100, "status": "Late"},
                {"shipment": "1329881990", "type": "Standard", "arrival": "2026-07-26", "hours": 20.8, "hours_width": 52.0, "hours_tone": "ok", "rcv": 99.2, "status": "On Time"},
                {"shipment": "1329881983", "type": "Standard", "arrival": "2026-07-23", "hours": 14.8, "hours_width": 37.0, "hours_tone": "ok", "rcv": 100, "status": "On Time"},
                {"shipment": "1329881987", "type": "Standard", "arrival": "2026-07-23", "hours": 11.4, "hours_width": 28.5, "hours_tone": "ok", "rcv": 100, "status": "On Time"},
                {"shipment": "1329881977", "type": "Standard", "arrival": "2026-07-21", "hours": 14.1, "hours_width": 35.3, "hours_tone": "ok", "rcv": 100, "status": "On Time"},
            ],
        },
    ],
}


CITIES = {
    "year_range": "2025 - 2026",
    "companies": [
        {
            "key": "iffco",
            "name": "IFFCO",
            "section_title": "IFFCO Performance by Warehouse",
            "layout": "warehouse",
            "dot_color": "#e53935",
            "cards": [
                {"name": "Abha", "score": 98.5, "status": "Good", "tone": "ok", "orders": 183, "misses": 3, "local": 95.6, "remote": 100, "inbound": 100},
                {"name": "Buraydah", "score": 91.5, "status": "Needs Attn", "tone": "bad", "orders": 117, "misses": 10, "local": 86.9, "remote": 87.5, "inbound": 100},
                {"name": "Jeddah", "score": 100, "status": "Excellent", "tone": "ok", "orders": 580, "misses": 0, "local": 100, "remote": 100, "inbound": 100},
                {"name": "Khobar", "score": 97.7, "status": "Good", "tone": "ok", "orders": 623, "misses": 20, "local": 97.0, "remote": 96.9, "inbound": 100},
                {"name": "Madinah", "score": 100, "status": "Excellent", "tone": "ok", "orders": 138, "misses": 0, "local": 100, "remote": 100, "inbound": 100},
                {"name": "Riyadh", "score": 97.5, "status": "Good", "tone": "ok", "orders": 844, "misses": 41, "local": 95.1, "remote": None, "inbound": 100},
                {"name": "Tabuk", "score": 99.3, "status": "Excellent", "tone": "ok", "orders": 46, "misses": 1, "local": 97.8, "remote": 100, "inbound": 100},
            ],
        },
        {
            "key": "aramco",
            "name": "ARAMCO",
            "section_title": "ARAMCO Performance by Destination City",
            "layout": "city",
            "dot_color": "#43a047",
            "cards": [
                {"name": "Jeddah", "score": 100, "status": "Excellent", "tone": "ok", "orders": 43, "misses": 0, "avg_label": "Local", "avg_hours": 29},
                {"name": "Riyadh", "score": 100, "status": "Excellent", "tone": "ok", "orders": 9, "misses": 0, "avg_label": "Remote", "avg_hours": 27},
                {"name": "Madinah", "score": 100, "status": "Excellent", "tone": "ok", "orders": 3, "misses": 0, "avg_label": "Remote", "avg_hours": 19},
                {"name": "Dammam", "score": 100, "status": "Excellent", "tone": "ok", "orders": 5, "misses": 0, "avg_label": "Remote", "avg_hours": 9},
                {"name": "Makkah", "score": 75, "status": "Watch", "tone": "warn", "orders": 4, "misses": 1, "avg_label": None, "avg_hours": None},
                {"name": "Tabuk", "score": 100, "status": "Excellent", "tone": "ok", "orders": 4, "misses": 0, "avg_label": None, "avg_hours": None},
                {"name": "Yanbu", "score": 100, "status": "Excellent", "tone": "ok", "orders": 4, "misses": 0, "avg_label": None, "avg_hours": None},
                {"name": "Other Cities", "score": 99.2, "status": "Good", "tone": "ok", "orders": 118, "misses": 1, "avg_label": None, "avg_hours": None},
            ],
        },
    ],
}


INVENTORY = {
    "year_range": "2025 - 2026",
    "disclaimer": "IFFCO Inventory not included in current report.",
    "footer": "Tamer Logistics — 3PL KPI Dashboard  IFFCO (Mar 2025) & Aramco (Aug 2026)  KSA Operations",
    "companies": [
        {
            "key": "aramco",
            "name": "ARAMCO",
            "section_title": "ARAMCO Inventory Snapshot — Jeddah WH · Aug 2026",
            "dot_color": "#43a047",
            "kpis": [
                {"label": "Located LPNs", "value": 1157, "sub": "In storage locations", "tone": "info"},
                {"label": "Received LPNs", "value": 59, "sub": "Pending putaway", "tone": "neutral"},
                {"label": "Total Qty On Hand", "value": 17050, "sub": "Units in warehouse", "tone": "ok"},
            ],
            "notes": [
                {"text": "Facility: 3PL JED2 — Jeddah Warehouse", "status": "Active", "tone": "info"},
                {"text": "Products: Automotive lubricants (VAL All Climate, SynPower, Fleet Extra, Axle/Gear Oil)", "status": "Veedol/Valvoline", "tone": "ok"},
                {"text": "59 LPNs in Received status — pending putaway", "status": "Action Needed", "tone": "warn"},
            ],
        },
    ],
}


SLA = {
    "year_range": "2025 - 2026",
    "agreement_title": "SLA Agreement — Tamer Logistics 3PL",
    "table_title": "Achievement vs Target",
    "agreement": [
        {
            "title": "Outbound — Customer Delivery",
            "items": [
                {"label": "Inside City (Local) — Despatch", "value": "48 Hours", "tone": "ok"},
                {"label": "Outside City (Remote) — Despatch", "value": "72 Hours", "tone": "ok"},
                {"label": "Customer Receiving Date (CRD)", "value": "72 Hours", "tone": "ok"},
            ],
        },
        {
            "title": "Outbound — Branch Transfers",
            "items": [
                {"label": "Shipping from submission", "value": "24 Hours", "tone": "ok"},
                {"label": "Cut-off for same-day picking", "value": "2:00 PM", "tone": "warn"},
            ],
        },
        {
            "title": "Inbound — Receiving",
            "items": [
                {"label": "System receiving after arrival", "value": "24 Hours", "tone": "ok"},
            ],
        },
        {
            "title": "Inbound — GRN",
            "items": [
                {"label": "GRN report sharing after arrival", "value": "24 Hours", "tone": "ok"},
            ],
        },
    ],
    "companies": [
        {
            "key": "iffco",
            "name": "IFFCO",
            "rows": [
                {"category": "Outbound Local Despatch", "target": "48h", "achievement": 96.6, "status": "Hit"},
                {"category": "Outbound Remote Despatch", "target": "72h", "achievement": 95.1, "status": "Hit"},
                {"category": "Inbound Receiving", "target": "24h", "achievement": 100, "status": "Perfect"},
            ],
        },
        {
            "key": "aramco",
            "name": "ARAMCO",
            "rows": [
                {"category": "Outbound Local Despatch", "target": "48h", "achievement": 100, "status": "Perfect"},
                {"category": "Outbound Remote Despatch", "target": "72h", "achievement": 98.7, "status": "Hit"},
                {"category": "Inbound Receiving", "target": "24h", "achievement": 62.1, "status": "Miss"},
            ],
        },
    ],
}


MISSES = {
    "year_range": "2025 - 2026",
    "companies": [
        {
            "key": "iffco",
            "name": "IFFCO",
            "section_title": "IFFCO Miss Analysis — March 2025",
            "layout": "warehouse",
            "dot_color": "#e53935",
            "kpis": [
                {"label": "Despatch Misses", "value": "75", "sub": "Local: 62, Remote: 13", "tone": "bad"},
                {"label": "CRD Misses", "value": "80", "sub": "Local: 65, Remote: 15", "tone": "bad"},
                {"label": "Highest — Buraydah", "value": "13.1%", "sub": "8 misses / 61 orders", "tone": "warn"},
                {"label": "Perfect Warehouses", "value": "2", "sub": "Jeddah — Madinah", "tone": "ok"},
            ],
            "table_title": "Miss by Warehouse",
            "rows": [
                {"name": "Buraydah", "orders": 61, "misses": 8, "rate": 13.1, "risk": "High"},
                {"name": "Riyadh", "orders": 844, "misses": 41, "rate": 4.9, "risk": "Watch"},
                {"name": "Khobar", "orders": 302, "misses": 9, "rate": 3.0, "risk": "Watch"},
                {"name": "Abha", "orders": 68, "misses": 3, "rate": 4.4, "risk": "Watch"},
                {"name": "Jeddah", "orders": 341, "misses": 0, "rate": 0, "risk": "Perfect"},
                {"name": "Madinah", "orders": 137, "misses": 0, "rate": 0, "risk": "Perfect"},
            ],
            "reasons_title": "Common Miss Reasons",
            "reasons": [
                {"text": "Remote Area — long distance", "status": "Major", "tone": "bad"},
                {"text": "Booking Orders — per schedule", "status": "Accepted", "tone": "warn"},
                {"text": "Awaited FTL consolidation", "status": "Accepted", "tone": "warn"},
                {"text": "Eid Holidays — exception", "status": "Exception", "tone": "info"},
            ],
        },
        {
            "key": "aramco",
            "name": "ARAMCO",
            "section_title": "ARAMCO Miss Analysis — Aug 2026",
            "layout": "detail",
            "dot_color": "#43a047",
            "kpis": [
                {"label": "Outbound Misses", "value": "2", "sub": "Both remote orders", "tone": "warn"},
                {"label": "Missed City", "value": "Makkah", "sub": "75% SLA · 4 orders", "tone": "warn"},
                {"label": "Inbound Misses", "value": "22", "sub": "82.1% on-time", "tone": "bad"},
                {"label": "Avg Inbound Delay", "value": "~35h", "sub": "11h above SLA", "tone": "warn"},
            ],
            "outbound_title": "Outbound — Miss Detail",
            "outbound_details": [
                {"text": "Makkah: 1 miss (remote, avg 56h)", "status": "Watch", "tone": "warn"},
                {"text": "Other: 1 miss (remote)", "status": "Watch", "tone": "warn"},
                {"text": "All Jeddah local orders", "status": "Perfect", "tone": "ok"},
            ],
            "inbound_title": "Inbound — Root Cause",
            "inbound_causes": [
                {"text": "Most shipments: 31-40h (just over 24h)", "status": "Systemic", "tone": "bad"},
                {"text": "Large shipments — multi-day receiving", "status": "Process", "tone": "warn"},
                {"text": "Suggest: stagger arrivals or extend to 48h", "status": "Recommend", "tone": "info"},
            ],
        },
    ],
}