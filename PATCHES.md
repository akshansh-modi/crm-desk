# Changes we made to upstream code

When you re-sync an app from upstream (steps in `AGENTS.md`, "Re-syncing an app from upstream"),
re-apply these or check whether upstream fixed them. Each changed spot is marked `crm-desk patch`.

| File | What | Why |
|---|---|---|
| `apps/frappe/frappe/utils/redis_wrapper.py` (`ClientCache.__init__`) | Wrapped the client-side-cache connection in try/except + `ping()`, falls back to plain `frappe.cache` | Redis Cloud rejects `CLIENT TRACKING ... REDIRECT` over RESP2, which crashed every request. Only costs a small speed-up (no in-process cache). |
| `apps/frappe/frappe/locale.py` (`get_locale_value`) | `value = None` before `if lang:` | `UnboundLocalError` when there's no language, e.g. in the email-pull background job. Broke incoming email tickets. |
| `apps/frappe/node_utils.js` (`get_redis_subscriber`) | Added `client.on("error", ...)` | node-redis only auto-reconnects when an error listener exists; without it a dropped Redis Cloud connection crashed socketio, and `bench start` then stopped every process. |
