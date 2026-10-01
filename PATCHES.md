# Changes we made to upstream code

When you re-sync an app from upstream (steps in `AGENTS.md`, "Re-syncing an app from upstream"),
re-apply these or check whether upstream fixed them. Each changed spot is marked `crm-desk patch`.

| File | What | Why |
|---|---|---|
| `apps/frappe/frappe/utils/redis_wrapper.py` (`ClientCache.__init__`) | Wrapped the client-side-cache connection in try/except + `ping()`, falls back to plain `frappe.cache` | Redis Cloud rejects `CLIENT TRACKING ... REDIRECT` over RESP2, which crashed every request. Only costs a small speed-up (no in-process cache). |
| `apps/frappe/frappe/locale.py` (`get_locale_value`) | `value = None` before `if lang:` | `UnboundLocalError` when there's no language, e.g. in the email-pull background job. Broke incoming email tickets. |
| `apps/frappe/node_utils.js` (`get_redis_subscriber`) | Added `client.on("error", ...)` | node-redis only auto-reconnects when an error listener exists; without it a dropped Redis Cloud connection crashed socketio, and `bench start` then stopped every process. |
| `apps/helpdesk/desk/src/components/Customer360.vue` (new file) | Customer 360 card + dialog, data from `insurance.api.get_customer_360` | Insurance 360 view on tickets. **Identical copy** in `apps/crm/frontend/src/components/Customer360.vue`: change both together. |
| `apps/helpdesk/desk/src/components/ticket-agent/TicketDetailsTab.vue` | Import + render `<Customer360>` above the Overview section, keyed on the ticket's `contact` / `raised_by` | Agents see the customer's policies, claims and premiums on the ticket. |
| `apps/crm/frontend/src/components/Customer360.vue` (new file) | Same file as the Helpdesk copy | Insurance 360 view in CRM. |
| `apps/crm/frontend/src/pages/Contact.vue` | Import + render `<Customer360>` under the contact header | 360 view on a CRM contact. |
| `apps/crm/frontend/src/pages/Deal.vue` | Import + render `<Customer360>` under the SLA block, for the deal's primary contact | 360 view on a CRM deal. |
