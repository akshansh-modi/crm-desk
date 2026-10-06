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
| `apps/helpdesk/helpdesk/api/auth.py` (`get_current_user_email_info`) | Also returns `helpdesk_emails`: every Email Account address | Lets the composer know the helpdesk's own inboxes (incoming ones too). |
| `apps/helpdesk/desk/src/components/EmailArea.vue` (`reply`, `replyAll`, `normalizeAndFilter`) | "Own message" = sender is the user id, the user's email or a helpdesk inbox (was: user id only). Own addresses never become recipients; if To would be empty, Cc moves up to To, else the ticket's `raised_by`. Exclusion compares bare addresses (`"Name" <a@b.com>` = `a@b.com`). | Reply All put the support inbox into Cc; replying to your own email as Administrator (id `Administrator` ≠ `admin@example.com`) sent it to yourself with the customer in Cc. Upstream bugs, independent of the insurance app. |
| `apps/helpdesk/desk/src/components/CustomerDocumentsPicker.vue` (new file) | Attach picker listing the ticket customer's policy documents (`insurance.api.get_ticket_documents`), with "Upload from computer" | Agents can send a customer their policy documents from the reply composer. Warns when a recipient isn't one of the customer's emails. |
| `apps/helpdesk/desk/src/components/EmailEditor.vue` | Paperclip opens `CustomerDocumentsPicker` when the customer has documents; otherwise the file dialog as before | Same feature. Attachments are copies (`insurance.api.attach_ticket_document`), since removing an attachment deletes its File. |
| `apps/helpdesk/desk/src/components/BrandLogo.vue` | Logo `h-8 w-8 object-cover` → `h-8 w-auto object-contain` | Wide brand logos were cropped to a 32px square. Now shown whole, like CRM. |
| `apps/helpdesk/desk/src/components/UserMenu.vue` | `<BrandLogo>` gets `max-w-16` (expanded) / `max-w-8` (collapsed sidebar) | Caps the now-natural logo width, same 64px limit CRM uses. |
| `apps/helpdesk/desk/src/components/telephony/CallNote.vue` (new file) | Call-note panel: opens when a call is placed from a ticket, stays open after hang-up, saves an internal HD Ticket Comment (`new_comment`) with call context; agent text is HTML-escaped | Agents can record what was said on a call. Never emailed. |
| `apps/helpdesk/desk/src/components/telephony/CallUI.vue` (`makeCall`, `makeCallUsing`) | Captures the ticket when an outgoing call starts and mounts `CallNote` | Notes attach to the ticket the call was placed from, not a stale `linkDoc`. Incoming calls (no ticket) get no note panel. |
