# Copyright (c) 2026, crm-desk and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class InsuranceClaim(Document):
	def validate(self):
		policy = frappe.db.get_value("Insurance Policy", self.policy, ["start_date", "end_date", "sum_insured"], as_dict=True)

		if not frappe.db.exists("Policy Member", {"parent": self.policy, "parenttype": "Insurance Policy", "member": self.member}):
			frappe.throw(_("{0} is not covered under policy {1}").format(self.member_name or self.member, self.policy))

		if self.admission_date and not (getdate(policy.start_date) <= getdate(self.admission_date) <= getdate(policy.end_date)):
			frappe.throw(_("Admission Date must fall within the policy period"))
		if self.admission_date and self.discharge_date and getdate(self.discharge_date) < getdate(self.admission_date):
			frappe.throw(_("Discharge Date cannot be before Admission Date"))

		if flt(self.claimed_amount) > flt(policy.sum_insured):
			frappe.throw(_("Claimed Amount cannot exceed the policy's Sum Insured"))
		if flt(self.approved_amount) > flt(self.claimed_amount):
			frappe.throw(_("Approved Amount cannot exceed Claimed Amount"))
		if self.settled_amount and flt(self.settled_amount) > flt(self.approved_amount):
			frappe.throw(_("Settled Amount cannot exceed Approved Amount"))
