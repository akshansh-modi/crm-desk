frappe.listview_settings["Insurance Policy"] = {
	get_indicator(doc) {
		const colors = {"Active": "green", "Grace Period": "orange", "Lapsed": "red", "Expired": "gray", "Cancelled": "gray"};
		return [__(doc.status), colors[doc.status] || "gray", "status,=," + doc.status];
	},
};
