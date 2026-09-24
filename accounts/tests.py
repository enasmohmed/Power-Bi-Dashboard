import pandas as pd
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from accounts import inbound_reviews, kpi_excel
from accounts.models import CustomUser, InboundShipmentReview


class WarehouseAndReviewTests(TestCase):
    def test_override_flips_miss_to_hit(self):
        frame = pd.DataFrame({
            "Facility Code": ["3PLJED2"],
            "Shipment Nbr": ["1329002037"],
            "_rcv_hit": [False],
            "_rcv_miss": [True],
        })
        token = kpi_excel.shipment_identity("aramco", "3PLJED2", "1329002037")
        updated = kpi_excel.apply_rcv_overrides(frame, "aramco", {token: "hit"})
        self.assertTrue(bool(updated.iloc[0]["_rcv_hit"]))
        self.assertFalse(bool(updated.iloc[0]["_rcv_miss"]))

    def test_reason_stays_hidden_until_admin_approves(self):
        employee = CustomUser.objects.create_user(
            username="picker",
            password="pass-12345",
            role="employee",
            is_approved=True,
        )
        admin = CustomUser.objects.create_user(
            username="boss",
            password="pass-12345",
            role="admin",
            is_staff=True,
            is_approved=True,
        )
        key = "aramco|3PLJED2|1329002037"
        self.client.force_login(employee)
        response = self.client.post(reverse("accounts:inbound_review"), {
            "shipment_key": key,
            "company": "aramco",
            "shipment": "1329002037",
            "warehouse": "3PLJED2",
            "result": "hit",
            "reason": "Received before the window",
            "next": "/accounts/inbound/?company=aramco&wh=3PLJED2",
        })
        self.assertEqual(response.status_code, 302)
        review = InboundShipmentReview.objects.get(shipment_key=key)
        self.assertEqual(review.status, InboundShipmentReview.STATUS_PENDING)
        self.assertEqual(review.approved_reason, "")

        companies = [{
            "layout": "shipments",
            "rows": [{
                "shipment_key": key,
                "hit_miss": "miss",
                "status": "Late",
            }],
        }]
        inbound_reviews.attach(companies)
        row = companies[0]["rows"][0]
        self.assertTrue(row["review_pending"])
        self.assertEqual(row["approved_reason"], "")
        self.assertEqual(row["hit_miss"], "miss")

        self.client.force_login(employee)
        denied = self.client.post(reverse("accounts:inbound_review_decide"), {
            "shipment_key": key,
            "decision": "approve",
        })
        self.assertEqual(denied.status_code, 302)
        review.refresh_from_db()
        self.assertEqual(review.status, InboundShipmentReview.STATUS_PENDING)

        self.client.force_login(admin)
        approved = self.client.post(reverse("accounts:inbound_review_decide"), {
            "shipment_key": key,
            "decision": "approve",
        })
        self.assertEqual(approved.status_code, 302)
        review.refresh_from_db()
        self.assertEqual(review.approved_result, "hit")
        self.assertEqual(review.approved_reason, "Received before the window")
        inbound_reviews.attach(companies)
        shown = companies[0]["rows"][0]
        self.assertEqual(shown["approved_reason"], "Received before the window")
        self.assertEqual(shown["hit_miss"], "hit")
        self.assertEqual(shown["status"], "On Time")
        self.assertFalse(shown["review_pending"])

    def test_outbound_reason_hidden_until_approval(self):
        employee = CustomUser.objects.create_user(
            username="outbound-picker",
            password="pass-12345",
            role="employee",
            is_approved=True,
        )
        admin = CustomUser.objects.create_user(
            username="outbound-boss",
            password="pass-12345",
            role="admin",
            is_staff=True,
            is_approved=True,
        )
        key = "ob|nespresso|3PLJED|Jeddah"
        self.client.force_login(employee)
        response = self.client.post(reverse("accounts:outbound_review"), {
            "shipment_key": key,
            "company": "nespresso",
            "shipment": "Jeddah",
            "warehouse": "3PLJED",
            "result": "miss",
            "reason": "Carrier delay",
            "next": "/accounts/outbound/?company=nespresso",
        })
        self.assertEqual(response.status_code, 302)
        companies = [{
            "layout": "city",
            "rows": [{
                "review_key": key,
                "name": "Jeddah",
                "status": "Perfect",
                "hit_miss": "hit",
            }],
        }]
        inbound_reviews.attach_outbound(companies)
        row = companies[0]["rows"][0]
        self.assertTrue(row["review_pending"])
        self.assertEqual(row["approved_reason"], "")
        self.assertEqual(row["status"], "Perfect")
        self.client.force_login(admin)
        self.client.post(reverse("accounts:outbound_review_decide"), {
            "shipment_key": key,
            "decision": "approve",
        })
        inbound_reviews.attach_outbound(companies)
        shown = companies[0]["rows"][0]
        self.assertEqual(shown["status"], "Miss")
        self.assertEqual(shown["approved_reason"], "Carrier delay")
        self.assertFalse(shown["review_pending"])

    def test_manager_group_can_approve(self):
        manager = CustomUser.objects.create_user(
            username="lead",
            password="pass-12345",
            role="employee",
            is_approved=True,
        )
        manager.groups.add(Group.objects.create(name="Manager"))
        self.assertTrue(inbound_reviews.can_approve(manager))
