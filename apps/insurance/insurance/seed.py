"""Realistic fake demo data for the customer 360 view.

Run (LOCAL mode only):
    bench --site crm-desk.localhost execute insurance.seed.run --kwargs '{"customers": 40}'
    bench --site crm-desk.localhost execute insurance.seed.reset

Realism rules: most customers never claim (~85%); claims fall inside the policy period, on a
member covered by that policy, with amounts that fit the diagnosis; ages, cities and EMI history
are consistent with each other and with the policy status.
"""

import random

import frappe
from frappe.utils import add_days, add_months, add_years, date_diff, getdate, today

DEMO_EMAIL = "akshanshmodi2002@gmail.com"

# (city, state, pincode prefix): addresses are drawn together so they agree.
CITIES = [
	("Mumbai", "Maharashtra", "400"), ("Pune", "Maharashtra", "411"), ("Delhi", "Delhi", "110"),
	("Bengaluru", "Karnataka", "560"), ("Chennai", "Tamil Nadu", "600"), ("Hyderabad", "Telangana", "500"),
	("Kolkata", "West Bengal", "700"), ("Ahmedabad", "Gujarat", "380"), ("Jaipur", "Rajasthan", "302"),
	("Lucknow", "Uttar Pradesh", "226"), ("Indore", "Madhya Pradesh", "452"), ("Kochi", "Kerala", "682"),
]
HOSPITAL_NAMES = [
	"City Care Multispeciality Hospital", "Sunrise Hospital", "Lifeline Medical Centre", "Apex Heart & General Hospital",
	"Shree Sai Hospital", "Medicare Super Speciality Hospital", "Green Valley Hospital", "Sanjeevani Hospital",
	"Unity Health Hospital", "Mother & Child Care Hospital", "Metro Ortho & Trauma Centre", "Lotus Eye Hospital",
]
# diagnosis: (min amount, max amount, min days, max days, min patient age)
DIAGNOSES = {
	"Dengue fever": (20000, 60000, 3, 5, 0),
	"Typhoid fever": (25000, 60000, 3, 6, 0),
	"Acute appendicitis (appendectomy)": (60000, 150000, 2, 4, 5),
	"Pneumonia": (40000, 120000, 4, 7, 0),
	"Kidney stones (ureteroscopy)": (50000, 120000, 1, 3, 20),
	"Fractured forearm (ORIF)": (40000, 100000, 1, 3, 5),
	"Gallbladder removal (laparoscopic)": (70000, 160000, 2, 3, 25),
	"Cataract surgery": (35000, 80000, 1, 1, 50),
	"Coronary angioplasty": (200000, 400000, 3, 5, 45),
	"Total knee replacement": (250000, 450000, 4, 7, 55),
}
FREQ_MONTHS = {"Annual": 12, "Half-yearly": 6, "Quarterly": 3, "Monthly": 1}
DOCTYPES = ["Insurance Claim", "Premium EMI", "Insurance Policy", "Insured Member", "Insurance Customer", "Network Hospital"]


def _guard():
	# The cloud DB is shared: demo rows there would show up for every dev.
	if frappe.conf.db_host != "mariadb":
		frappe.throw("insurance.seed only runs in local mode (db_host 'mariadb').")


def reset():
	"""Delete all insurance data and the Contacts it created (Contacts still used elsewhere are kept)."""
	_guard()
	contacts = frappe.get_all("Insurance Customer", pluck="contact")
	for dt in DOCTYPES:
		frappe.db.delete(dt)
	frappe.db.delete("Policy Member")
	frappe.db.delete("Policy Document")
	for f in frappe.get_all("File", filters={"attached_to_doctype": "Insurance Policy"}, pluck="name"):
		frappe.delete_doc("File", f, ignore_permissions=True)
	for name in contacts:
		try:
			frappe.delete_doc("Contact", name, force=0, ignore_permissions=True)
		except frappe.LinkExistsError:
			pass
	frappe.db.commit()
	print(f"Deleted insurance data and up to {len(contacts)} contacts")


def run(customers=40):
	_guard()
	from faker import Faker

	fake = Faker("en_IN")
	random.seed()
	hospitals = _hospitals(fake)
	_demo_customer(fake, hospitals)
	for _ in range(customers - 1):
		_random_customer(fake, hospitals)
	frappe.db.commit()
	print(f"Created {customers} customers ({DEMO_EMAIL} included) and {len(hospitals)} hospitals")


# ---------------------------------------------------------------- hospitals


def _hospitals(fake):
	out = []
	for i, (city, state, pin) in enumerate(CITIES):
		for j in range(2):
			code = f"HSP{i * 2 + j + 1:04d}"
			if not frappe.db.exists("Network Hospital", code):
				frappe.get_doc(
					{
						"doctype": "Network Hospital",
						"hospital_code": code,
						"hospital_name": f"{HOSPITAL_NAMES[(i * 2 + j) % len(HOSPITAL_NAMES)]}, {city}",
						# ponytail: every 4th hospital is out of network, so cashless isn't universal
						"network_status": "Non-network" if (i * 2 + j) % 4 == 3 else "Network",
						"cashless_available": 0 if (i * 2 + j) % 4 == 3 else 1,
						"phone": f"0{random.randint(20, 80)}{random.randint(20000000, 29999999)}",
						"address": fake.street_address(),
						"city": city,
						"state": state,
						"pincode": f"{pin}{random.randint(1, 99):03d}",
					}
				).insert()
			out.append(frappe.get_doc("Network Hospital", code))
	return out


# ---------------------------------------------------------------- customers


def _demo_customer(fake, hospitals):
	"""The customer behind DEMO_EMAIL: family floater, one past settled claim, one open claim, a ticket and a deal."""
	city = CITIES[0]
	contact = frappe.db.get_value("Contact", {"email_id": DEMO_EMAIL})
	if not contact:
		contact = _contact("Akshansh", "Modi", DEMO_EMAIL, "9876543210").name
	holder_dob = add_years(getdate(today()), -34)
	customer = _customer_doc(contact, holder_dob, "Male", city, customer_since=add_years(getdate(today()), -3), kyc="Verified")

	members = [
		_member(customer, "Akshansh Modi", "Self", "Male", holder_dob),
		_member(customer, "Riya Modi", "Spouse", "Female", add_years(holder_dob, 2)),
		_member(customer, "Aarav Modi", "Son", "Male", add_years(getdate(today()), -4)),
		_member(customer, "Sunita Modi", "Mother", "Female", add_years(getdate(today()), -61), "Hypertension"),
	]
	current_start = add_months(getdate(today()), -7)
	prev = _policy(customer, members, add_years(current_start, -1), "Expired", "Family Care Plus", 1000000, "Monthly", "Agent")
	cur = _policy(customer, members, current_start, "Active", "Family Care Plus", 1000000, "Monthly", "Agent")

	hospital = next(h for h in hospitals if h.city == city[0] and h.network_status == "Network")
	_claim(prev, members[2], hospital, "Dengue fever", add_days(prev.start_date, 140), "Settled", "Cashless")
	_claim(cur, members[3], hospital, "Cataract surgery", add_days(getdate(today()), -9), "Query Raised", "Reimbursement")

	_demo_ticket(contact)
	_demo_deal(contact)


def _random_customer(fake, hospitals):
	gender = random.choice(["Male", "Female"])
	first = fake.first_name_male() if gender == "Male" else fake.first_name_female()
	last = fake.last_name()
	city = random.choice(CITIES)
	age = random.choices([random.randint(24, 35), random.randint(36, 50), random.randint(51, 68)], weights=[40, 40, 20])[0]
	holder_dob = add_days(add_years(getdate(today()), -age), -random.randint(0, 364))

	tenure_years = random.choices([0, 1, 2, 3, 5], weights=[25, 25, 20, 15, 15])[0]
	current_start = add_days(getdate(today()), -random.randint(15, 330))
	first_start = add_years(current_start, -tenure_years)

	contact = _contact(first, last, fake.unique.free_email(), f"{random.choice('6789')}{random.randint(100000000, 999999999)}")
	is_new = date_diff(today(), first_start) < 90
	customer = _customer_doc(
		contact.name, holder_dob, gender, city, customer_since=first_start,
		kyc="Pending" if is_new and random.random() < 0.5 else "Verified",
		segment="Corporate" if random.random() < 0.15 else "Retail",
	)

	members = [_member(customer, f"{first} {last}", "Self", gender, holder_dob, _condition(age))]
	if age >= 26 and random.random() < 0.7:
		spouse_gender = "Female" if gender == "Male" else "Male"
		spouse_name = (fake.first_name_female() if spouse_gender == "Female" else fake.first_name_male()) + f" {last}"
		spouse_dob = add_days(holder_dob, random.randint(-8 * 365, 6 * 365))
		members.append(_member(customer, spouse_name, "Spouse", spouse_gender, spouse_dob, _condition(_age(spouse_dob))))
		for _ in range(random.choices([0, 1, 2], weights=[30, 40, 30])[0] if age < 55 else 0):
			child_dob = add_days(holder_dob, random.randint(24 * 365, 34 * 365))
			if getdate(child_dob) >= getdate(today()):
				continue
			child_gender = random.choice(["Male", "Female"])
			child_name = (fake.first_name_male() if child_gender == "Male" else fake.first_name_female()) + f" {last}"
			members.append(_member(customer, child_name, "Son" if child_gender == "Male" else "Daughter", child_gender, child_dob))

	if customer.segment == "Corporate":
		product, sum_insured, frequency = "Group Health", random.choice([300000, 500000]), "Annual"
	elif age >= 60:
		product, sum_insured, frequency = "Senior Secure", random.choice([300000, 500000]), random.choice(["Annual", "Quarterly"])
	else:
		product = random.choice(["Health Shield", "Family Care Plus"] if len(members) > 1 else ["Health Shield", "Super Top-up"])
		sum_insured = random.choice([500000, 1000000, 1500000]) if product != "Super Top-up" else random.choice([2000000, 2500000])
		frequency = random.choices(list(FREQ_MONTHS), weights=[50, 10, 15, 25])[0]
	channel = random.choice(["Agent", "Online", "Bancassurance", "Broker", "Direct"])

	policies = []
	for y in range(tenure_years, 0, -1):
		policies.append(_policy(customer, members, add_years(current_start, -y), "Expired", product, sum_insured, frequency, channel))
	status = "Active" if frequency == "Annual" else random.choices(["Active", "Grace Period", "Lapsed"], weights=[85, 10, 5])[0]
	policies.append(_policy(customer, members, current_start, status, product, sum_insured, frequency, channel))

	# Claim frequency ~8% per policy-year, rarely a second one in the same year.
	local = [h for h in hospitals if h.city == city[0]] or hospitals
	for p in policies:
		n = random.choices([0, 1, 2], weights=[92, 7, 1])[0]
		for _ in range(n):
			member = random.choice(members)
			diagnosis = random.choice([d for d, v in DIAGNOSES.items() if _age(member.date_of_birth) >= v[4]])
			window = min(date_diff(p.end_date, p.start_date), date_diff(today(), p.start_date)) - 10
			if window < 30:
				continue
			admitted = add_days(p.start_date, random.randint(30, window))
			hospital = random.choice(local)
			claim_type = "Cashless" if hospital.cashless_available and random.random() < 0.7 else "Reimbursement"
			_claim(p, member, hospital, diagnosis, admitted, None, claim_type)


# ---------------------------------------------------------------- builders


def _contact(first, last, email, mobile):
	return frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": first,
			"last_name": last,
			"email_ids": [{"email_id": email, "is_primary": 1}],
			# Both flags: Helpdesk matches calls on Contact.phone, CRM on any Contact Phone row.
			"phone_nos": [{"phone": mobile, "is_primary_phone": 1, "is_primary_mobile_no": 1}],
		}
	).insert(ignore_permissions=True)


def _customer_doc(contact, dob, gender, city, customer_since, kyc, segment="Retail"):
	return frappe.get_doc(
		{
			"doctype": "Insurance Customer",
			"contact": contact,
			"date_of_birth": dob,
			"gender": gender,
			"kyc_status": kyc,
			"segment": segment,
			"customer_since": customer_since,
			"city": city[0],
			"state": city[1],
			"pincode": f"{city[2]}{random.randint(1, 99):03d}",
		}
	).insert()


def _member(customer, name, relationship, gender, dob, condition=""):
	return frappe.get_doc(
		{
			"doctype": "Insured Member",
			"customer": customer.name,
			"member_name": name,
			"relationship": relationship,
			"gender": gender,
			"date_of_birth": dob,
			"pre_existing_conditions": condition,
		}
	).insert()


def _policy(customer, members, start, status, product, sum_insured, frequency, channel):
	start = getdate(start)
	eldest = max(_age(m.date_of_birth) for m in members)
	base = sum_insured * (0.012 if eldest < 36 else 0.018 if eldest < 46 else 0.028 if eldest < 61 else 0.045)
	premium = round(base * (1 + 0.35 * (len(members) - 1)) * (0.4 if product == "Super Top-up" else 1), -2)
	if product == "Group Health":
		premium = round(premium * 0.6, -2)

	step = FREQ_MONTHS[frequency]
	count = 12 // step
	dues = [getdate(add_months(start, n * step)) for n in range(count)]
	past = [d for d in dues if d <= getdate(today())]
	# Grace Period: only the latest due is unpaid, and it's under 30 days late. Lapsed: older than that.
	if status == "Grace Period" and (len(past) < 2 or date_diff(today(), past[-1]) > 30):
		status = "Active"
	if status == "Lapsed" and (len(past) < 3 or date_diff(today(), past[-2]) <= 30):
		status = "Active"
	unpaid = {"Grace Period": past[-1:], "Lapsed": past[-2:]}.get(status, [])

	policy = frappe.get_doc(
		{
			"doctype": "Insurance Policy",
			"policy_number": f"POL{random.randint(10**9, 10**10 - 1)}",
			"customer": customer.name,
			"product_name": product,
			"plan_type": "Group" if product == "Group Health" else ("Family Floater" if len(members) > 1 else "Individual"),
			"status": status,
			"sum_insured": sum_insured,
			"premium_amount": premium,
			"payment_frequency": frequency,
			"start_date": start,
			"end_date": add_days(add_years(start, 1), -1),
			"sales_channel": channel,
			"members": [{"member": m.name, "sum_insured": sum_insured, "entry_date": start} for m in members],
		}
	).insert()
	_attach_documents(policy, customer, members)

	for n, due in enumerate(dues):
		if due in unpaid:
			emi_status = "Overdue"
		elif due <= getdate(today()):
			emi_status = "Paid"
		else:
			emi_status = "Due"
		paid = emi_status == "Paid"
		frappe.get_doc(
			{
				"doctype": "Premium EMI",
				"policy": policy.name,
				"installment_no": n + 1,
				"due_date": due,
				"amount": round(premium / count, 2),
				"status": emi_status,
				"paid_on": add_days(due, -random.randint(0, 3)) if paid else None,
				"payment_mode": random.choice(["UPI", "Card", "Net Banking", "NACH"]) if paid else None,
				"transaction_ref": f"TXN{random.randint(10**11, 10**12 - 1)}" if paid else None,
			}
		).insert()
	return policy


def _attach_documents(policy, customer, members):
	"""Real (tiny) PDFs as private File attachments, so the document links in the 360 view open."""
	holder = frappe.db.get_value("Insurance Customer", customer.name, "customer_name")
	for doc_type, uploaded_on in (("Policy Schedule", policy.start_date), ("Proposal Form", add_days(policy.start_date, -7))):
		lines = [
			doc_type.upper(),
			f"Policy: {policy.name}    Product: {policy.product_name} ({policy.plan_type})",
			f"Policyholder: {holder}    Customer ID: {customer.name}",
			f"Period: {policy.start_date} to {policy.end_date}",
			f"Sum insured: INR {policy.sum_insured:,.0f}    Premium: INR {policy.premium_amount:,.0f} ({policy.payment_frequency})",
			"Members: " + ", ".join(f"{m.member_name} ({m.relationship})" for m in members),
			"Demo document generated by insurance.seed - not a real policy.",
		]
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{policy.name}-{doc_type.lower().replace(' ', '-')}.pdf",
				"is_private": 1,
				"attached_to_doctype": "Insurance Policy",
				"attached_to_name": policy.name,
				"content": _pdf(lines),
			}
		).insert(ignore_permissions=True)
		policy.append("documents", {"document_type": doc_type, "file": file.file_url, "uploaded_on": uploaded_on})
	policy.save()


def _pdf(lines):
	"""Minimal one-page text PDF, no dependencies."""
	esc = lambda t: str(t).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
	text = "BT /F1 11 Tf 50 790 Td 16 TL " + " ".join(f"({esc(line)}) Tj T*" for line in lines) + " ET"
	objs = [
		"<< /Type /Catalog /Pages 2 0 R >>",
		"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
		"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
		f"<< /Length {len(text)} >>\nstream\n{text}\nendstream",
		"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
	]
	out, offsets = "%PDF-1.4\n", []
	for i, o in enumerate(objs, 1):
		offsets.append(len(out))
		out += f"{i} 0 obj\n{o}\nendobj\n"
	xref = len(out)
	out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offsets)
	out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF"
	return out.encode("latin-1")


def _claim(policy, member, hospital, diagnosis, admitted, status, claim_type):
	lo, hi, dmin, dmax, _ = DIAGNOSES[diagnosis]
	claimed = min(round(random.uniform(lo, hi), -2), policy.sum_insured)
	discharged = add_days(admitted, random.randint(dmin, dmax))
	age_days = date_diff(today(), discharged)
	if not status:
		if age_days > 45:
			status = random.choices(["Settled", "Rejected"], weights=[90, 10])[0]
		else:
			status = random.choice(["Intimated", "Under Review", "Query Raised", "Approved"])
	approved = round(claimed * random.uniform(0.82, 0.98), -2) if status in ("Approved", "Settled") else None
	frappe.get_doc(
		{
			"doctype": "Insurance Claim",
			"claim_number": f"CLM{random.randint(10**8, 10**9 - 1)}",
			"policy": policy.name,
			"member": member.name,
			"hospital": hospital.name,
			"claim_type": claim_type,
			"status": status,
			"admission_date": admitted,
			"discharge_date": discharged,
			"diagnosis": diagnosis,
			"claimed_amount": claimed,
			"approved_amount": approved,
			"settled_amount": approved if status == "Settled" else None,
			"settled_on": add_days(discharged, random.randint(7, 25)) if status == "Settled" else None,
			"rejection_reason": "Condition excluded during the initial waiting period" if status == "Rejected" else None,
		}
	).insert()


def _demo_ticket(contact):
	"""Simulates the email the customer would send; a real one creates the same HD Ticket via the email account."""
	if "helpdesk" not in frappe.get_installed_apps():
		return
	ticket = frappe.db.get_value("HD Ticket", {"raised_by": DEMO_EMAIL})
	if not ticket:
		ticket = frappe.get_doc(
			{
				"doctype": "HD Ticket",
				"subject": "Status of my mother's cataract claim",
				"raised_by": DEMO_EMAIL,
				"description": "Hi, I submitted the reimbursement documents for my mother's cataract surgery last week. "
				"The claim shows a query. Could you tell me what is pending? Policy is Family Care Plus.",
			}
		).insert(ignore_permissions=True).name
	# Inserted from a script, Helpdesk records the session user as the sender; a real email has the customer.
	frappe.db.set_value(
		"Communication",
		{"reference_doctype": "HD Ticket", "reference_name": ticket, "sent_or_received": "Received"},
		{"sender": DEMO_EMAIL, "sender_full_name": frappe.db.get_value("Contact", contact, "full_name")},
	)


def _demo_deal(contact):
	if "crm" not in frappe.get_installed_apps():
		return
	if frappe.db.exists("CRM Contacts", {"contact": contact, "parenttype": "CRM Deal"}):
		return
	frappe.get_doc(
		{
			"doctype": "CRM Deal",
			"status": "Proposal/Quotation",
			"deal_value": 18500,
			"contacts": [{"contact": contact, "is_primary": 1}],
		}
	).insert(ignore_permissions=True)


def _age(dob):
	return date_diff(today(), dob) // 365


def _condition(age):
	if age >= 45:
		return random.choices(["", "Diabetes", "Hypertension", "Diabetes, Hypertension", "Thyroid"], weights=[50, 15, 20, 10, 5])[0]
	return random.choices(["", "Asthma", "Thyroid"], weights=[90, 5, 5])[0]
