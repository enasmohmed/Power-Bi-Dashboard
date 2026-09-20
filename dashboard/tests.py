import io
from datetime import datetime, time

from django.test import TestCase
from openpyxl import Workbook

from dashboard.picker_performance_service import build_filter_meta, parse_sap_sheet


def _picking_workbook(rows: list[dict]) -> io.BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "Data"
    headers = [None] * 26
    headers[0] = "Business"
    headers[1] = "Creation Date"
    headers[2] = "Creation time"
    headers[3] = "Transfer Order Number"
    headers[4] = "Source Storage Type"
    headers[5] = "Source Storage Bin"
    headers[8] = "Delivery"
    headers[16] = "User"
    headers[17] = "User"
    headers[18] = "Confirmation time"
    headers[19] = "Confirmation date"
    ws.append(headers)
    for row in rows:
        cells = [None] * 26
        cells[0] = row.get("business")
        cells[1] = row.get("create_date")
        cells[2] = row.get("create_time")
        cells[3] = row.get("to_number")
        cells[4] = row.get("storage_type")
        cells[5] = row.get("bin")
        cells[8] = row.get("delivery")
        cells[16] = row.get("user_q")
        cells[17] = row.get("user_r")
        cells[18] = row.get("conf_time")
        cells[19] = row.get("conf_date")
        ws.append(cells)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


class ParseSapSheetBusinessTests(TestCase):
    def test_keeps_every_business_even_without_user(self):
        day = datetime(2026, 9, 15)
        t = time(10, 15, 0)
        buf = _picking_workbook(
            [
                {
                    "business": "Nestle",
                    "create_date": day,
                    "create_time": t,
                    "to_number": "3001",
                    "storage_type": "228",
                    "bin": "PICK-01",
                    "user_q": "SAABDELAMO2",
                    "user_r": "SAKAMASHYA",
                    "conf_time": t,
                    "conf_date": day,
                },
                {
                    "business": "NESPRESSO",
                    "create_date": day,
                    "create_time": t,
                    "bin": "P-19-P-C-01",
                    "delivery": "SO-001423410",
                    "conf_time": t,
                    "conf_date": day,
                },
                {
                    "business": "IFC",
                    "create_date": day,
                    "create_time": t,
                    "bin": "A6-AB-17-D-03",
                    "delivery": "138940946",
                    "conf_time": t,
                    "conf_date": day,
                },
                {
                    "business": "ARAMCO",
                    "create_date": day,
                    "create_time": t,
                    "bin": "A7-AE-43-D-01",
                    "delivery": "2501718466",
                    "conf_time": t,
                    "conf_date": day,
                },
            ]
        )
        rows, sheet = parse_sap_sheet(buf, sheet_name="Data")
        self.assertEqual(sheet, "Data")
        self.assertEqual(len(rows), 4)
        businesses = {r["business"] for r in rows}
        self.assertEqual(businesses, {"ARAMCO", "IFC", "NESPRESSO", "Nestle"})
        nestle = next(r for r in rows if r["business"] == "Nestle")
        self.assertEqual(nestle["picker_name"], "SAKAMASHYA")
        self.assertEqual(nestle["delivery_number"], "3001")
        self.assertTrue(nestle["is_pick"])
        nespresso = next(r for r in rows if r["business"] == "NESPRESSO")
        self.assertEqual(nespresso["picker_name"], "NESPRESSO")
        self.assertEqual(nespresso["delivery_number"], "SO-001423410")
        self.assertTrue(nespresso["is_pick"])
        aramco = next(r for r in rows if r["business"] == "ARAMCO")
        self.assertEqual(aramco["delivery_number"], "2501718466")
        self.assertTrue(aramco["is_pick"])
        ifc = next(r for r in rows if r["business"] == "IFC")
        self.assertEqual(ifc["delivery_number"], "138940946")
        self.assertTrue(ifc["is_pick"])
        meta = build_filter_meta(rows)
        self.assertEqual(meta["business_options"], ["ARAMCO", "IFC", "NESPRESSO", "Nestle"])
