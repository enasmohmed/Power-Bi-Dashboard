from django.db.utils import OperationalError, ProgrammingError
from django.utils import timezone

from .models import InboundShipmentReview

APPROVER_ROLES = {"admin", "manager"}
APPROVER_GROUPS = {"Admin", "Manager", "Managers", "admin", "manager"}


def can_approve(user):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser or user.is_staff:
        return True
    role = str(getattr(user, "role", "") or "").strip().lower()
    if role in APPROVER_ROLES:
        return True
    return user.groups.filter(name__in=APPROVER_GROUPS).exists()


def approved_override_state():
    try:
        rows = list(
            InboundShipmentReview.objects.exclude(approved_result="").values_list(
                "shipment_key", "approved_result", "reviewed_at", "submitted_at"
            )
        )
    except (OperationalError, ProgrammingError):
        return {}, ""
    mapping = {
        key: result
        for key, result, _reviewed, _submitted in rows
        if result in {InboundShipmentReview.RESULT_HIT, InboundShipmentReview.RESULT_MISS}
    }
    stamps = [item[2] or item[3] for item in rows]
    latest = max(stamps) if stamps else ""
    return mapping, f"{len(mapping)}:{latest}"


def attach(companies):
    keys = []
    for company in companies or []:
        if company.get("layout") != "shipments":
            continue
        for row in company.get("rows") or []:
            if row.get("shipment_key"):
                keys.append(row["shipment_key"])
    reviews = {}
    if keys:
        try:
            reviews = {
                item.shipment_key: item
                for item in InboundShipmentReview.objects.filter(shipment_key__in=keys)
            }
        except (OperationalError, ProgrammingError):
            reviews = {}
    for company in companies or []:
        if company.get("layout") != "shipments":
            continue
        updated = []
        for row in company.get("rows") or []:
            item = dict(row)
            review = reviews.get(item.get("shipment_key"))
            item["approved_reason"] = ""
            item["review_pending"] = False
            item["pending_reason"] = ""
            item["edit_result"] = item.get("hit_miss") or InboundShipmentReview.RESULT_HIT
            item["edit_reason"] = ""
            if review:
                if review.approved_result in {InboundShipmentReview.RESULT_HIT, InboundShipmentReview.RESULT_MISS}:
                    item["hit_miss"] = review.approved_result
                    item["status"] = "On Time" if review.approved_result == InboundShipmentReview.RESULT_HIT else "Late"
                    item["approved_reason"] = (review.approved_reason or "").strip()
                    item["edit_result"] = review.approved_result
                    item["edit_reason"] = review.approved_reason or ""
                if review.status == InboundShipmentReview.STATUS_PENDING:
                    item["review_pending"] = True
                    item["pending_reason"] = (review.proposed_reason or "").strip()
                    item["edit_result"] = review.proposed_result or item["edit_result"]
                    item["edit_reason"] = review.proposed_reason or ""
            updated.append(item)
        company["rows"] = updated


def attach_outbound(companies):
    keys = []
    for company in companies or []:
        if company.get("layout") != "city":
            continue
        for row in company.get("rows") or []:
            if row.get("review_key"):
                keys.append(row["review_key"])
    reviews = {}
    if keys:
        try:
            reviews = {
                item.shipment_key: item
                for item in InboundShipmentReview.objects.filter(shipment_key__in=keys)
            }
        except (OperationalError, ProgrammingError):
            reviews = {}
    for company in companies or []:
        if company.get("layout") != "city":
            continue
        updated = []
        for row in company.get("rows") or []:
            item = dict(row)
            item["approved_reason"] = ""
            item["review_pending"] = False
            item["pending_reason"] = ""
            item["edit_result"] = "miss" if item.get("status") == "Watch" else "hit"
            item["edit_reason"] = ""
            review = reviews.get(item.get("review_key"))
            if review:
                if review.approved_result in {InboundShipmentReview.RESULT_HIT, InboundShipmentReview.RESULT_MISS}:
                    item["hit_miss"] = review.approved_result
                    item["status"] = "Hit" if review.approved_result == InboundShipmentReview.RESULT_HIT else "Miss"
                    item["approved_reason"] = (review.approved_reason or "").strip()
                    item["edit_result"] = review.approved_result
                    item["edit_reason"] = review.approved_reason or ""
                if review.status == InboundShipmentReview.STATUS_PENDING:
                    item["review_pending"] = True
                    item["pending_reason"] = (review.proposed_reason or "").strip()
                    item["edit_result"] = review.proposed_result or item["edit_result"]
                    item["edit_reason"] = review.proposed_reason or ""
            updated.append(item)
        company["rows"] = updated


def save_proposal(user, shipment_key, company, shipment, warehouse, result, reason):
    review, _created = InboundShipmentReview.objects.get_or_create(shipment_key=shipment_key)
    review.company = company or review.company
    review.shipment_nbr = shipment or review.shipment_nbr
    review.warehouse = warehouse or review.warehouse
    review.proposed_result = result
    review.proposed_reason = reason
    review.status = InboundShipmentReview.STATUS_PENDING
    review.submitted_by = user
    review.submitted_at = timezone.now()
    review.reviewed_by = None
    review.save()
    return review


def decide(user, shipment_key, decision):
    review = InboundShipmentReview.objects.filter(shipment_key=shipment_key).first()
    if review is None or review.status != InboundShipmentReview.STATUS_PENDING:
        return None
    review.reviewed_by = user
    review.reviewed_at = timezone.now()
    if decision == "approve":
        review.status = InboundShipmentReview.STATUS_APPROVED
        review.approved_result = review.proposed_result
        review.approved_reason = review.proposed_reason
    else:
        review.status = InboundShipmentReview.STATUS_REJECTED
    review.save()
    return review
