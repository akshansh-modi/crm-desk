frappe.listview_settings["Insurance Customer"] = {
	get_indicator(doc) {
		const colors = {"Verified": "green", "Pending": "orange", "Rejected": "red"};
		return [__(doc.kyc_status), colors[doc.kyc_status] || "gray", "kyc_status,=," + doc.kyc_status];
	},
};
