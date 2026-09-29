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

### Option B: cloud mode (the shared cloud database and Redis)

```bash
cp .env.cloud.example .env     # then fill in the blanks, see below
docker compose up              # no --profile
```

Fill in these values in `.env`:

| Line | What to put |
|---|---|
| `DB_USER`, `DB_PASSWORD` | SkySQL login (ask a teammate) |
| `REDIS_URL` | `redis://default:<password>@<host>:<port>` from Redis Cloud |
| `ENCRYPTION_KEY` | The **same** value for everyone on the shared site (ask a teammate) |
| `BENCH_ID` | Your own name. It must be different from your teammates' |
| `RUN_SCHEDULER` | `1` for exactly **one** dev, `0` for everyone else |

The host, port and DB name are already filled in.

**Don't do these on the cloud site without telling the team:** `migrate`, `install-app`, `new-site` or `reinstall`. Everyone shares this database, so these change it for all of you.

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
