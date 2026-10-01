app_name = "insurance"
app_title = "Insurance"
app_publisher = "crm-desk"
app_description = "Insurance data for the customer 360 view"
app_email = ""
app_license = "mit"

doc_events = {
	"Contact": {"on_update": "insurance.api.sync_customer_from_contact"},
}
