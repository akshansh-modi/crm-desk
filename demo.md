# Customer 360 demo

How the insurance data behind the Customer 360 view works: the tables, how they get filled,
and how an incoming email ends up showing the 360 view on a Helpdesk ticket.

Everything lives in our own app, `apps/insurance` (not upstream code). The only upstream edits are
the 360 component and where it is mounted in Helpdesk and CRM; those are listed in `PATCHES.md`.

---

## 1. The tables

8 tables (Frappe DocTypes): 6 main ones and 2 sub-tables inside a policy. Each becomes a database
table named `tab<Name>`.

```
Contact (Frappe built-in; email + phone)
   │ 1:1
Insurance Customer ──1:many── Insured Member
   │ 1:many                        ▲
Insurance Policy ─┬─ Policy Member (sub-table) ─┘   who is covered
                  ├─ Policy Document (sub-table)    PDFs
                  ├─1:many── Premium EMI
                  └─1:many── Insurance Claim ──> Network Hospital
                                    └──> Insured Member
```

### 1.1 Insurance Customer: one per policyholder
IDs look like `CUST-00001`.

| Field | Type / values | Notes |
|---|---|---|
| contact | Link → Contact | Required and unique. Emails and calls find the customer through this. |
| customer_name, email_id, mobile_no | Copied from Contact (read-only) | Kept in sync by a hook on Contact save |
| kyc_status | Pending / Verified / Rejected | |
| segment | Retail / Corporate | |
| customer_since | Date | |
| date_of_birth, gender | | |
| city, state, pincode | | |

The form shows its linked policies, members, EMIs and claims.

### 1.2 Insured Member: each person who can be covered
IDs look like `MEM-00001`. A member belongs to the customer, not to one policy, so one person's
history carries across renewals.

| Field | Type / values |
|---|---|
| customer | Link → Insurance Customer |
| member_name | Text |
| relationship | Self / Spouse / Son / Daughter / Father / Mother |
| date_of_birth, gender | |
| pre_existing_conditions | Text |

### 1.3 Insurance Policy
The ID is the policy number, e.g. `POL1694311447`.

| Field | Type / values |
|---|---|
| policy_number | Unique |
| customer | Link → Insurance Customer |
| product_name | e.g. Family Care Plus |
| plan_type | Individual / Family Floater / Group |
| status | Active / Grace Period / Lapsed / Expired / Cancelled |
| sum_insured, premium_amount | Currency |
| payment_frequency | Annual / Half-yearly / Quarterly / Monthly |
| start_date, end_date | Date (end must be after start) |
| sales_channel | Agent / Online / Bancassurance / Broker / Direct |
| members | Sub-table → Policy Member (Members tab) |
| documents | Sub-table → Policy Document (Documents tab) |

### 1.4 Policy Member (sub-table inside Policy): who is covered on this policy

| Field | Type / values |
|---|---|
| member | Link → Insured Member (must belong to the same customer) |
| member_name, relationship | Copied from the member |
| sum_insured | This member's cover |
| entry_date | Date |
| is_active | Yes/No |

### 1.5 Policy Document (sub-table inside Policy)

| Field | Type / values |
|---|---|
| document_type | Policy Schedule / Proposal Form / KYC / Endorsement / Renewal Notice / Other |
| file | Attachment (private file) |
| uploaded_on | Date |

### 1.6 Premium EMI: one row per premium instalment
IDs look like `EMI-00001`.

| Field | Type / values |
|---|---|
| policy | Link → Insurance Policy |
| customer | Copied from the policy |
| installment_no | Number |
| due_date, amount | |
| status | Due / Paid / Overdue / Failed |
| paid_on, payment_mode, transaction_ref | Payment mode: UPI / Card / Net Banking / NACH / Cheque / Cash |

### 1.7 Insurance Claim
The ID is the claim number, e.g. `CLM787422153`.

| Field | Type / values |
|---|---|
| claim_number | Unique |
| policy | Link → Insurance Policy |
| customer | Copied from the policy |
| member | Link → Insured Member (must be covered on that policy) |
| member_name | Copied from the member |
| hospital | Link → Network Hospital |
| claim_type | Cashless / Reimbursement |
| status | Intimated / Under Review / Query Raised / Approved / Rejected / Settled |
| admission_date, discharge_date | Admission must fall inside the policy period; discharge on or after admission |
| diagnosis | Text (Medical & Amounts tab) |
| claimed_amount, approved_amount, settled_amount | Settled ≤ approved ≤ claimed ≤ sum insured |
| settled_on, rejection_reason | Shown only when the status is Settled or Rejected |

### 1.8 Network Hospital: master list of hospitals
The ID is the hospital code, e.g. `HSP0001`.

| Field | Type / values |
|---|---|
| hospital_code | Unique |
| hospital_name | Text |
| network_status | Network / Non-network |
| cashless_available | Yes/No |
| phone, address, city, state, pincode | |

### Rules shared by all tables
- **Access:** System Manager can edit. Agent, Agent Manager, Sales User and Sales Manager can only view. Helpdesk customer-portal users (HD Customer) have no access.
- **Indexes:** the customer, policy and member link columns are indexed, so the 360 lookups stay fast.
- **Change history:** every edit is recorded on the record.
- **Not included yet:** TPA, nominee, waiting periods.

---

## 2. How the tables were created

A Frappe table is defined by a **DocType**, a JSON file in the app that lists the fields. When the
app is installed (`install-app`) or updated (`migrate`), Frappe reads these files and creates or
alters the real database tables. No SQL is written by hand.

```
apps/insurance/insurance/insurance/doctype/
  insurance_customer/
    insurance_customer.json      fields, tabs, permissions, linked records
    insurance_customer.py        Python class for the table (validation lives here)
    insurance_customer_list.js   status colours in the list view
  insurance_policy/ ...          (same pattern for all 8 tables)
```

| File | What it does |
|---|---|
| `doctype/*/*.json` | Table definitions. The source of truth. |
| `doctype/insurance_policy/insurance_policy.py` | Validation: end date after start date; members belong to the policy's customer |
| `doctype/insurance_claim/insurance_claim.py` | Validation: member is on the policy, admission inside the policy period, amount limits |
| `doctype/*/*_list.js` | Coloured status labels in the list views |
| `hooks.py` | When a Contact is saved, its name, email and mobile are copied onto the Insurance Customer |
| `workspace_sidebar/insurance.json` | The Insurance sidebar in Desk (`/app`) |
| `api.py` | `get_customer_360`, the single API the 360 view calls |
| `seed.py` | Demo data (section 3) |

To change a table later: edit it in Desk (developer mode writes the change back to the JSON file)
or edit the JSON by hand, then run `migrate` on the **local** site.

---

## 3. How the data is filled

All demo data comes from `apps/insurance/insurance/seed.py`. Local mode only:

```
docker compose exec frappe bench --site crm-desk.localhost execute insurance.seed.reset
docker compose exec frappe bench --site crm-desk.localhost execute insurance.seed.run --kwargs '{"customers": 40}'
```

- **Safety check:** it refuses to run unless the site's database is the local `mariadb`, so it can never write to the shared cloud database.
- **Insert method:** every record is created with `frappe.get_doc({...}).insert()`, as AGENTS.md requires. The same validation, naming and hooks run as when a person fills in a form. No raw SQL inserts.
- **Order:** hospitals → Contact (email and primary phone) → Insurance Customer → family members → policies (with members and generated PDF documents) → premium instalments → occasional claims.
- **Realism:**
  - Faker supplies Indian names.
  - Ages match relationships: a spouse within about 8 years, children 24–34 years younger.
  - City, state and pincode come from one list, so they agree.
  - Premiums depend on age band, family size and product.
  - Instalment history matches the policy status: Grace Period means the latest instalment is under 30 days overdue; Lapsed means older dues are unpaid.
  - Claims are rare (about 8% per policy per year). Most customers have none, and amounts and hospital stays fit the diagnosis.
  - Older claims are mostly settled; recent ones are still in process.
- **Demo customer** (`akshanshmodi2002@gmail.com`, Akshansh Modi): a Family Care Plus floater covering self, spouse, son and mother. It has a past settled dengue claim, a current cataract claim with a query raised, 24 premium instalments, a support ticket and a CRM deal.
- **Reset:** `reset` deletes the insurance data, the generated PDFs and the demo Contacts. It keeps any Contact a ticket or deal still uses. Customer IDs keep counting up after a reseed.

---

## 4. What happens when an email comes in

Creating a ticket from an email is **built into Helpdesk**. The `insurance` app only adds the
lookup at the end. Nothing is copied or stored on the ticket; the 360 data is fetched when the
ticket is opened, so it is always current.

```
Customer sends an email to the support inbox
        │
        ▼
Email Account (Helpdesk inbox) is pulled by the scheduler
        │
        ▼
HD Ticket created, raised_by = sender's email               (built into Helpdesk)
        │
        ▼
HD Ticket.set_contact(): finds the Contact whose primary
email matches → ticket.contact                              (built into Helpdesk)
        │
        ▼
Agent opens the ticket → Customer360 card calls
insurance.api.get_customer_360(contact, email)              (ours)
        │
        ▼
Contact → Insurance Customer → policies, members,
EMIs, claims, tickets, deals → shown in the card and window
```

- **Matching:** by email. Helpdesk links the ticket to the Contact whose **primary** email matches. As a fallback, the API also checks the Contact's other email addresses using the ticket's sender email. If neither matches, the card says "Not an insurance customer".
- **Permissions:** the API returns only what the logged-in user may see. A section they can't read (for example, tickets for a Sales User) comes back empty instead of breaking the view.
- **Sites without the app:** where the `insurance` app isn't installed (the shared cloud site, for now), the card hides itself.
- **Local demo:** the inbox step was simulated by creating the ticket directly with `raised_by = akshanshmodi2002@gmail.com`; from the ticket onward the path is the same as a real email. A full end-to-end test needs a separate test mailbox connected to the local site, never the real support inbox.
- **Not built:** automatic pre-filling, such as setting the ticket's Customer field or reading a policy number from the email body. That would be a small hook on HD Ticket creation.

---

## 5. Where the 360 view appears

| App | Page | Uses |
|---|---|---|
| Helpdesk | Ticket sidebar, above Overview | The ticket's contact, or its sender email |
| CRM | Contact page, under the header | That contact |
| CRM | Deal page, under SLA | The deal's primary contact |

- **The card** shows: current policy and its status, the policy number (click to copy), sum insured, next premium, claims, members, and alerts (overdue premium, grace period or lapse, a claim query pending, KYC not verified).
- **"Open 360 view"** opens a large window with six tabs: Overview, Policies, Members, Claims, Premiums, and Interactions (tickets and deals).
  - Clicking an alert jumps to the matching tab, and the arrow keys move between tabs.
  - Each record links to its full form in Desk.
- **Same file in both apps:** `Customer360.vue` exists in `apps/helpdesk/desk/src/components/` and `apps/crm/frontend/src/components/`. Keep the two files identical.

After pulling these changes, rebuild both frontends:

```
docker compose exec frappe bench build --app helpdesk
docker compose exec frappe bench build --app crm
```
