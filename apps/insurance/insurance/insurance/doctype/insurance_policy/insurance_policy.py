# Copyright (c) 2026, crm-desk and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import getdate


class InsurancePolicy(Document):
	def validate(self):
		if getdate(self.end_date) <= getdate(self.start_date):
			frappe.throw(_("End Date must be after Start Date"))

		# Health ID formats are configured in Insurance Settings (UI); empty = don't generate.
		formats = frappe.db.get_value(
			"Insurance Settings", None, ["policyholder_health_id_format", "member_health_id_format"], as_dict=True
		) or {}
		missing = False
		for row in self.members:
			customer, relationship = frappe.db.get_value("Insured Member", row.member, ["customer", "relationship"])
			if customer != self.customer:
				frappe.throw(_("Row {0}: {1} does not belong to customer {2}").format(row.idx, row.member_name or row.member, self.customer))
			# Health IDs belong to this policy; a renewal is a new policy, so its rows get fresh IDs.
			if not row.health_id:
				series = formats.get("policyholder_health_id_format" if relationship == "Self" else "member_health_id_format")
				if series:
					row.health_id = make_autoname(series)
				else:
					missing = True
		if missing:
			frappe.msgprint(
				_("Some members got no health ID: set the health ID formats in Insurance Settings."),
				indicator="orange",
				alert=True,
			)
