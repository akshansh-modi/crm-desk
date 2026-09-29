# AGENTS.md

Notes for any AI agent (or new dev) working in this repo. Read this before changing anything.

## What this is

A POC support + sales platform for a health insurer, built on the [Frappe](https://frappe.io) framework:

- **Helpdesk**: support tickets, served at `/helpdesk`
- **CRM**: sales leads and deals, served at `/crm`
- **Custom apps**: our own integrations and features (policy, claims, and so on). None exist yet.

One site runs all the apps. Which app a user sees is decided by their **role**:

- Helpdesk: `Agent`, `Agent Manager`, `HD Customer`, `HD Customer Manager`
- CRM: `Sales User`, `Sales Manager`
- `System Manager` sees both.

## Repo layout

```
apps/
  frappe/      framework, branch version-16 (Python 3.14)
  helpdesk/    branch main
  crm/         branch main
  telephony/   branch develop (the only branch it has)
docker/
  entrypoint.sh     builds a bench around apps/ and starts it
  write_config.py   merges .env values into Frappe's config json files
docker-compose.yml
.env.cloud.example / .env.local.example
UPSTREAM_VERSIONS.txt   which upstream commit each app was copied from
PATCHES.md              every change we made to upstream code
```

## The upstream apps are vendored, not submodules

The upstream code was cloned and then its `.git` was deleted, so everything lives in this one repo. That gives two rules:

- **Don't** run `bench get-app` or `git clone` into `apps/`. Don't add submodules either.
- **You may edit upstream code** (frappe, helpdesk, crm) when a customization needs it. When you do:
  - mark the spot with a `# crm-desk patch, see PATCHES.md` comment (or `//` in JS/Vue)
  - add a row to `PATCHES.md` saying what changed and why

  Otherwise the patch gets silently lost the next time someone re-syncs from upstream.

The empty `apps/crm/frappe-ui` and `apps/helpdesk/frappe-ui` folders are left over from git submodules. They are **not needed**: the build uses the `frappe-ui` npm package.

## Running it

Everything runs in Docker. There is no local Python or Node setup.

```bash
cp .env.cloud.example .env && docker compose up                   # shared cloud DB + Redis
cp .env.local.example .env && docker compose --profile local up   # your own local DB + Redis
```

Open http://localhost:8000 and log in as `Administrator`. The username is `Administrator`, not an email address.

- `apps/` is bind-mounted from the host. Python changes are picked up on reload. A new or reinstalled app needs `docker compose restart frappe`: the running worker and scheduler processes won't see it otherwise, and the scheduler has crashed from this before.
- The virtualenv, `sites/` and every `node_modules` live in Docker named volumes. `docker compose down -v` wipes them.
- The frontend is only built on the first start. After changing Vue code:

  ```bash
  docker compose exec frappe bench build --app <app>
  ```

- To create a new custom app, run inside the container, from the bench folder:

  ```bash
  bench new-app <name> --no-git
  ```

  Use `--no-git` so it doesn't get its own nested `.git`. Then restart the container: the entrypoint picks up any new folder in `apps/`. If the app has its own frontend, add a `node_modules` volume line for it in `docker-compose.yml`.

## The cloud DB is SHARED between devs — be careful

In cloud mode every dev points at the **same** MariaDB database (SkySQL) and the same Redis (Redis Cloud). Anything you do to the site's data or schema, your teammates see immediately.

- **Never** run these without the team agreeing, because they change the shared schema or data:
  - `bench new-site`
  - `bench reinstall`
  - `bench drop-site`
  - `bench migrate`
  - `bench install-app` / `bench uninstall-app`
  - DDL
  - bulk deletes

  The entrypoint deliberately never runs them in cloud mode.
- **`ENCRYPTION_KEY`** must be the same for every dev on the shared site. Otherwise stored passwords, such as email-account passwords, can't be decrypted.
- **`BENCH_ID`** controls background-job queue names (`<bench_id>:<queue>`). The rule is: same code → same id, different code → different id.
  - Two devs on the shared Redis each set their own id, so one dev's worker doesn't run the other's jobs.
  - In prod, all pods share one id (or leave it unset).
- **`RUN_SCHEDULER=1` on only ONE dev.** Two schedulers means scheduled jobs run twice. For example, email gets pulled twice, which creates duplicate tickets.
- **Seed or demo data** goes in through `frappe.get_doc({...}).insert()`, via `bench console` or `bench execute`, using Faker. **Never raw SQL**: it skips validation, naming and hooks.

## Secrets

- Never commit `.env`, `sites/`, or any real password, host credential or key. `.gitignore` already covers these.
- Only the `.env.*.example` files, with the secret values left blank, are committed.

## Frappe gotchas we've hit

- **Redis Cloud** rejects Frappe's client-side cache tracking over RESP2. The patch in `redis_wrapper.py` makes Frappe fall back to plain Redis caching.
- **SkySQL requires SSL.** `write_config.py` sets `db_ssl_ca` for cloud mode.
- **Scheduler flags.** There are three separate ones:
  - `pause_scheduler` in site_config
  - `disable_scheduler`
  - `System Settings.enable_scheduler`

  `bench scheduler resume` only clears the first. Use `bench scheduler enable` if scheduled jobs (like the email pull) aren't running.
- **Client Scripts don't run on Helpdesk or CRM pages.** They only work on the generic Desk forms (`/app/...`), not on Helpdesk's or CRM's own Vue pages. Customizing those pages means editing the Vue source, which counts as a patch.
- **`mute_emails: 1`** in site config silently stops all outgoing email.
- **API routes** are just dotted Python paths: `/api/method/<app>.<module>.<function>`. The function must be decorated with `@frappe.whitelist()`, which is the security gate. Check permissions inside it, for example with `frappe.only_for(...)`.

## Working with the maintainers

The team is learning Frappe hands-on:

- Explain what you're doing and why, in plain language.
- Prefer giving commands for them to run over running state-changing commands yourself, unless asked.
- Before anything destructive, or anything that touches the shared cloud DB or Redis, ask first.
