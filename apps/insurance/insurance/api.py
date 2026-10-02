import frappe
from frappe.utils import flt, getdate, today

OPEN_CLAIM = ("Intimated", "Under Review", "Query Raised", "Approved")


def sync_customer_from_contact(doc, method=None):
	"""Contact on_update: keep the Contact copies on Insurance Customer current."""
	frappe.db.set_value(
		"Insurance Customer",
		{"contact": doc.name},
		{"customer_name": doc.full_name, "email_id": doc.email_id, "mobile_no": doc.mobile_no},
	)


@frappe.whitelist()
def get_customer_360(contact: str | None = None, email: str | None = None) -> dict:
	"""Everything about one customer, for the 360 view in Helpdesk and CRM.

	Pass the Contact name, or an email (e.g. a ticket's raised_by / a lead's email).
	Sections the user can't read come back empty instead of failing the whole view.
	"""
	contact = contact or _contact_from_email(email)
	if not contact:
		return {"contact": None, "customer": None}

	frappe.has_permission("Contact", doc=contact, throw=True)
	c = frappe.get_doc("Contact", contact)
	out = {
		"contact": {
			"name": c.name,
			"full_name": c.full_name,
			"email_id": c.email_id,
			"mobile_no": c.mobile_no or c.phone,
			"image": c.image,
		},
		"customer": None,
		"tickets": _tickets(c),
		"deals": _deals(c.name),
	}

	customer = frappe.db.get_value("Insurance Customer", {"contact": contact})
	if not customer or not frappe.has_permission("Insurance Customer", doc=customer):
		return out

	out["customer"] = frappe.get_list(
		"Insurance Customer",
		filters={"name": customer},
		fields=["name", "customer_name", "kyc_status", "segment", "customer_since", "date_of_birth", "gender", "city", "state", "pincode"],
	)[0]

	policies = frappe.get_list(
		"Insurance Policy",
		filters={"customer": customer},
		fields=["name", "product_name", "plan_type", "status", "sum_insured", "premium_amount", "payment_frequency", "start_date", "end_date", "sales_channel"],
		order_by="start_date desc",
	)
	names = [p.name for p in policies]
	# Child rows: their parents were permission-checked by the get_list above.
	members_by_policy = _children("Policy Member", names, ["parent", "member", "health_id", "member_name", "relationship", "sum_insured", "is_active"])
	docs_by_policy = _children("Policy Document", names, ["parent", "document_type", "file", "uploaded_on"])
	for p in policies:
		p["members"] = members_by_policy.get(p.name, [])
		p["documents"] = docs_by_policy.get(p.name, [])

	members = frappe.get_list(
		"Insured Member",
		filters={"customer": customer},
		fields=["name", "member_name", "relationship", "date_of_birth", "gender", "pre_existing_conditions"],
		order_by="creation asc",
	)
	emis = frappe.get_list(
		"Premium EMI",
		filters={"customer": customer},
		fields=["name", "policy", "installment_no", "due_date", "amount", "status", "paid_on", "payment_mode", "transaction_ref"],
		order_by="due_date desc",
		limit=0,
	)
	claims = frappe.get_list(
		"Insurance Claim",
		filters={"customer": customer},
		fields=[
			"name", "policy", "member", "member_name", "health_id", "hospital", "claim_type", "status", "admission_date",
			"discharge_date", "diagnosis", "claimed_amount", "approved_amount", "settled_amount", "settled_on", "rejection_reason",
		],
		order_by="admission_date desc",
	)
	hospitals = dict(
		frappe.get_all("Network Hospital", filters={"name": ("in", {c.hospital for c in claims if c.hospital})}, fields=["name", "hospital_name"], as_list=True)
	) if claims else {}
	for cl in claims:
		cl["hospital_name"] = hospitals.get(cl.hospital)

	out.update(policies=policies, members=members, emis=emis, claims=claims, summary=_summary(policies, emis, claims))
	return out


def _contact_from_email(email):
	if not email:
		return None
	return frappe.db.get_value("Contact", {"email_id": email}) or frappe.db.get_value(
		"Contact Email", {"email_id": email, "parenttype": "Contact"}, "parent"
	)


def _children(doctype, parents, fields):
	grouped = {}
	if parents:
		for row in frappe.get_all(doctype, filters={"parent": ("in", parents), "parenttype": "Insurance Policy"}, fields=fields, order_by="idx asc"):
			grouped.setdefault(row.parent, []).append(row)
	return grouped


def _tickets(contact):
	if "helpdesk" not in frappe.get_installed_apps() or not frappe.has_permission("HD Ticket", "read"):
		return []
	filters = {"contact": contact.name}
	or_filters = {"raised_by": contact.email_id} if contact.email_id else None
	return frappe.get_list(
		"HD Ticket",
		or_filters={**filters, **(or_filters or {})},
		fields=["name", "subject", "status", "priority", "creation", "modified"],
		order_by="creation desc",
		limit=20,
	)


def _deals(contact):
	if "crm" not in frappe.get_installed_apps() or not frappe.has_permission("CRM Deal", "read"):
		return []
	deal_names = frappe.get_all("CRM Contacts", filters={"contact": contact, "parenttype": "CRM Deal"}, pluck="parent")
	if not deal_names:
		return []
	return frappe.get_list(
		"CRM Deal",
		filters={"name": ("in", deal_names)},
		fields=["name", "organization", "status", "deal_value", "currency", "modified"],
		order_by="modified desc",
	)


def _summary(policies, emis, claims):
	active = [p for p in policies if p.status in ("Active", "Grace Period")]
	overdue = [e for e in emis if e.status in ("Overdue", "Failed")]
	upcoming = sorted((e for e in emis if e.status == "Due" and getdate(e.due_date) >= getdate(today())), key=lambda e: e.due_date)
	return {
		"active_policies": len(active),
		"total_policies": len(policies),
		"sum_insured": sum(flt(p.sum_insured) for p in active),
		"current_policy": active[0] if active else (policies[0] if policies else None),
		"overdue_count": len(overdue),
		"overdue_amount": sum(flt(e.amount) for e in overdue),
		"next_due": upcoming[0] if upcoming else None,
		"open_claims": len([c for c in claims if c.status in OPEN_CLAIM]),
		"open_claimed_amount": sum(flt(c.claimed_amount) for c in claims if c.status in OPEN_CLAIM),
		"total_claims": len(claims),
		"total_settled": sum(flt(c.settled_amount) for c in claims),
	}


# ---------------------------------------------------------------- sharing documents on a ticket


def _ticket_customer(ticket):
	"""(contact, customer) for a Helpdesk ticket, resolved the same way as the 360 view."""
	frappe.has_permission("HD Ticket", doc=ticket, throw=True)
	t = frappe.db.get_value("HD Ticket", ticket, ["contact", "raised_by"], as_dict=True)
	contact = t.contact or _contact_from_email(t.raised_by)
	customer = contact and frappe.db.get_value("Insurance Customer", {"contact": contact})
	return contact, customer


@frappe.whitelist()
def get_ticket_documents(ticket: str) -> dict:
	"""The ticket customer's policy documents, for the reply composer's attach picker."""
	contact, customer = _ticket_customer(ticket)
	if not customer or not frappe.has_permission("Insurance Policy", "read"):
		return {"documents": [], "emails": []}

	policies = {
		p.name: p
		for p in frappe.get_list(
			"Insurance Policy",
			filters={"customer": customer},
			fields=["name", "product_name", "status", "start_date", "end_date"],
		)
	}
	rows = frappe.get_all(
		"Policy Document",
		filters={"parenttype": "Insurance Policy", "parent": ("in", list(policies) or [""])},
		fields=["name", "parent", "document_type", "file", "uploaded_on"],
		order_by="idx asc",
	)
	documents = [
		{
			"name": r.name,
			"document_type": r.document_type,
			"file_name": f"{r.document_type} - {r.parent}.pdf",
			"file_url": r.file,
			"policy": r.parent,
			"product_name": policies[r.parent].product_name,
			"policy_status": policies[r.parent].status,
			"start_date": policies[r.parent].start_date,
			"end_date": policies[r.parent].end_date,
		}
		for r in rows
		if r.file
	]
	documents.sort(key=lambda d: d["start_date"], reverse=True)  # stable: keeps idx order within a policy
	emails = frappe.get_all("Contact Email", filters={"parent": contact, "parenttype": "Contact"}, pluck="email_id")
	return {"documents": documents, "emails": emails}


@frappe.whitelist(methods=["POST"])
def attach_ticket_document(ticket: str, document: str) -> dict:
	"""Attach a copy of one of the ticket customer's policy documents (a Policy Document row) to the ticket.

	A copy, because the composer deletes an attachment's File when the agent removes it,
	and that must never delete the customer's actual policy document.
	"""
	frappe.has_permission("HD Ticket", "write", doc=ticket, throw=True)
	_contact, customer = _ticket_customer(ticket)
	row = frappe.db.get_value("Policy Document", document, ["parent", "parenttype", "document_type", "file"], as_dict=True)
	if (
		not customer
		or not row
		or row.parenttype != "Insurance Policy"
		or frappe.db.get_value("Insurance Policy", row.parent, "customer") != customer
	):
		frappe.throw(frappe._("This document doesn't belong to the ticket's customer"), frappe.PermissionError)
	frappe.has_permission("Insurance Policy", doc=row.parent, throw=True)

	copy = frappe.get_doc(
		{
			"doctype": "File",
			"file_url": row.file,
			"file_name": f"{row.document_type} - {row.parent}.pdf",
			"is_private": 1,
			"attached_to_doctype": "HD Ticket",
			"attached_to_name": ticket,
		}
	).insert(ignore_permissions=True)
	return {"name": copy.name, "file_name": copy.file_name, "file_url": copy.file_url}
