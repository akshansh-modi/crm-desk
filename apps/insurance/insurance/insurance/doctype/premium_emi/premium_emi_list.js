frappe.listview_settings["Premium EMI"] = {
	get_indicator(doc) {
		const colors = {"Paid": "green", "Due": "blue", "Overdue": "red", "Failed": "red"};
		return [__(doc.status), colors[doc.status] || "gray", "status,=," + doc.status];
	},
};
