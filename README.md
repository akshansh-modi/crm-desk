# crm-desk

Support (Frappe Helpdesk) and sales (Frappe CRM) on one Frappe site, plus our own custom apps. All the code, including Frappe itself, lives in this repo. See `AGENTS.md` for how the repo is organised and the rules for working in it.

## Running it

You only need **Docker**. Python, Node and everything else run inside the container.

There are two ways to run it. You choose one by copying an env file. Both use the same `docker-compose.yml`.

### Option A: local mode (your own database and Redis)

```bash
cp .env.local.example .env
docker compose --profile local up
```

- There's nothing to fill in. The DB password in the file is only for the MariaDB container on your machine.
- **`--profile local` is required.** The MariaDB and Redis containers only start with that flag. Without it, the Frappe container keeps printing `Waiting for local MariaDB...` forever.
- The first start creates a fresh site and installs telephony, helpdesk and crm. It then builds the frontend, which takes several minutes.

- The first start does **not** add demo data. See [Seeding demo data](#seeding-demo-data) below.

### Option B: cloud mode (the shared cloud database and Redis)

```bash
cp .env.cloud.example .env     # then fill in the blanks, see below
docker compose up              # no --profile
```

Fill in these values in `.env`:

| Line | What to put |
|---|---|
| `DB_USER`, `DB_PASSWORD` | SkySQL login  |
| `REDIS_URL` | `redis://default:<password>@<host>:<port>` from Redis Cloud |
| `ENCRYPTION_KEY` | The **same** value for everyone on the shared site |
| `BENCH_ID` | any unique word' |
| `RUN_SCHEDULER` | `1` for exactly **one** dev, `0` for everyone else |

The host, port and DB name are already filled in.

The first start installs telephony, helpdesk and crm on the site if they aren't already installed. Every later start skips that step.

#### Creating a new database (e.g. on AWS RDS)

If `DB_NAME` points at an empty database, the first start builds the site in it. Frappe doesn't create that database itself, so whoever does must set Frappe's character set and collation:

```sql
CREATE DATABASE <db_name> CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

MariaDB 11.8 otherwise defaults to `utf8mb4_uca1400_ai_ci`, and the RDS console's "Initial database name" field uses that default. Already created it that way? While it's still empty, fix it with:

```sql
ALTER DATABASE <db_name> CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

The DB user also needs full privileges on that database. Use MariaDB 10.6 to 11.8; Frappe warns outside that range.

**Don't do these on the cloud site without telling the team:** `migrate`, `install-app` of a new app, `new-site` or `reinstall`. Everyone shares this database, so these change it for all of you.

Never commit `.env`. It's gitignored, and only the `.example` files belong in git.

### Open it

Go to http://localhost:8000 and log in as `Administrator`:

- **Local mode:** the password is `admin`, from `.env.local.example`.
- **Cloud mode:** use the cloud site's admin password (ask a teammate).

| URL | App |
|---|---|
| `/helpdesk` | Helpdesk |
| `/crm` | CRM |
| `/app` | Frappe Desk (admin UI) |

## Seeding demo data

Local mode only, once per fresh site. The first start does **not** install our `insurance` app or add any demo data. With the stack running, run these in a second terminal:

```bash
docker compose exec frappe bench --site crm-desk.localhost install-app insurance
docker compose exec frappe bench --site crm-desk.localhost execute frappe.client.set_value --kwargs '{"doctype": "Insurance Settings", "name": "Insurance Settings", "fieldname": {"policyholder_health_id_format": "PI.######", "member_health_id_format": "HI.######"}}'
docker compose exec frappe bench --site crm-desk.localhost execute insurance.seed.run --kwargs '{"customers": 40}'
docker compose exec frappe bench build --app helpdesk
docker compose exec frappe bench build --app crm
docker compose restart frappe
```

1. Installs the insurance app: creates the Insurance Customer, Policy, Claim and other tables.
2. Sets the health ID formats. Without them, policies get no health IDs. You can also change them in Desk → Insurance → Insurance Settings.
3. Adds 40 fake customers, with policies, premiums, claims and hospitals, plus one demo ticket and deal. It refuses to run against the cloud DB.
4. Rebuilds the Helpdesk and CRM screens (Customer 360 panel and our other changes). Needed if the site was first started on an older branch, since the frontend is only built on the very first start. Harmless otherwise.
5. Restarts the container so the worker and scheduler see the new app. Then hard-refresh the browser (Cmd+Shift+R).

To start over: `docker compose exec frappe bench --site crm-desk.localhost execute insurance.seed.reset`, then run the seed again. See `demo.md` for what the data looks like.

## Everyday commands

```bash
docker compose logs -f --since 5m frappe                  # recent logs
docker compose exec frappe bash                           # a shell inside the bench folder
docker compose exec frappe bench build --app crm          # rebuild a frontend after changing Vue code
docker compose restart frappe                             # after adding or installing an app
docker compose down                                       # stop (keeps your data)
docker compose down -v                                    # stop and WIPE volumes: env, node_modules, local DB
```

- **In local mode, add `--profile local` to `down` as well** (`docker compose --profile local down`), so the MariaDB and Redis containers are stopped too.
- **Python changes** are picked up without a rebuild. Your `apps/` folder is shared directly with the container.
- **Frontend changes** need the `bench build` command above.
- **Force a full frontend rebuild:** `docker compose exec frappe rm sites/.built`, then restart.
