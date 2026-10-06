# Copyright (c) 2026, crm-desk and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class InsuranceSettings(Document):
	def validate(self):
		for field in ("policyholder_health_id_format", "member_health_id_format"):
			value = (self.get(field) or "").strip()
			self.set(field, value)
			if value and "#" not in value:
				frappe.throw(_("{0} needs at least one # (a digit), e.g. PI.######").format(self.meta.get_label(field)))
		if self.policyholder_health_id_format and self.policyholder_health_id_format == self.member_health_id_format:
			frappe.throw(_("Policyholder and member health ID formats must be different, or IDs would collide."))
