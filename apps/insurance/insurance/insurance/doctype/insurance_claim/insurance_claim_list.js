frappe.listview_settings["Insurance Claim"] = {
	get_indicator(doc) {
		const colors = {"Settled": "green", "Approved": "green", "Under Review": "blue", "Intimated": "blue", "Query Raised": "orange", "Rejected": "red"};
		return [__(doc.status), colors[doc.status] || "gray", "status,=," + doc.status];
	},
};
