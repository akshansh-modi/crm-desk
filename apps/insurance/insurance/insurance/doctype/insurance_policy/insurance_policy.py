# Copyright (c) 2026, crm-desk and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class InsurancePolicy(Document):
	def validate(self):
		if getdate(self.end_date) <= getdate(self.start_date):
			frappe.throw(_("End Date must be after Start Date"))

		for row in self.members:
			if frappe.db.get_value("Insured Member", row.member, "customer") != self.customer:
				frappe.throw(_("Row {0}: {1} does not belong to customer {2}").format(row.idx, row.member_name or row.member, self.customer))
