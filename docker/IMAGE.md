# Docker image (single container, for the InfoSec review)

Developers use `docker-compose.yml`. This is the other way to run the app: the root `Dockerfile`
builds **one image**, and **one container** runs the whole app (web, realtime, background jobs,
scheduler). MariaDB and Redis are **not** in the image: point it at existing ones with env vars.

Not a production setup yet (one container, no scaling). That comes after the InfoSec review.

## Build and run

```bash
docker build -t crm-desk .
docker run -d --name crm-desk --restart unless-stopped -p 8000:8000 -p 9000:9000 --env-file crm-desk.env crm-desk
```

`--restart unless-stopped`: if one process inside dies, the whole container stops, and this brings
it back. The first build takes a long time (about 30 minutes on a laptop, mostly Python packages);
later builds reuse that step unless something under `apps/` changed.

The first start on an empty database creates the site and installs the apps. That takes a few
minutes; follow it with `docker logs -f crm-desk`. Then open `http://<SITE_NAME>:8000` and log in as
`Administrator` with `ADMIN_PASSWORD`.

## Env file (`crm-desk.env`)

| Variable | Value |
|---|---|
| `SITE_NAME` | **The host name people open in the browser**, e.g. `crm-desk.internal.example.com`. Realtime updates only work when it matches. |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | MariaDB (tested with 11.8). The database and user must already exist, and the database should be empty on the first start. |
| `DB_SSL_CA` | CA file for SSL to the DB, e.g. `/etc/ssl/certs/ca-certificates.crt`. Empty means no SSL. |
| `REDIS_URL` | `redis://default:<password>@<host>:<port>` |
| `ENCRYPTION_KEY` | Generate once and keep it: `python3 -c "import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"` |
| `ADMIN_PASSWORD` | Administrator password, set on the first start |
| `INSTALL_APPS` | Optional. Default `telephony helpdesk crm insurance` |
| `GUNICORN_WORKERS` | Optional. Default `2` |

## Ports, nginx and health check

- `8000`: the app. `9000`: realtime (socket.io).
- In the DevOps nginx in front, send everything to port `8000`, **except the path `/socket.io`, which
  goes to port `9000`** (with the WebSocket upgrade headers). Pass the `Host` header through unchanged;
  it must equal `SITE_NAME`.
- **The container must be able to reach the site's public address** (`https://<SITE_NAME>`, through
  that nginx). When a browser opens a realtime connection, the realtime server checks the login by
  calling back the address the page was opened on. If the container can't resolve or reach it,
  realtime is refused with `Unauthorized: fetch failed`. The rest of the app still works.
- Without the `/socket.io` rule, live updates in Desk (`/app`) don't connect. Helpdesk and CRM still work when
  opened directly on `:8000`, because they go to `:9000` themselves.
- Health check: `GET /api/method/ping` returns `{"message":"pong"}`.

## Keep in mind

- **Use a database of its own.** Don't point this at the team's shared dev database (the one in
  `.env.cloud.example`): the first start installs apps there, and the built-in scheduler would run
  jobs twice next to a dev's.
- Uploaded files live inside the container at `/home/frappe/frappe-bench/sites/<SITE_NAME>/`. Mount a
  volume there if they must survive the container being removed. Not over `sites/`: that would hide
  the built frontend.
- After deploying a newer image on an existing database, run
  `docker exec crm-desk bench --site <SITE_NAME> migrate`.
- No demo data. The seed script only runs in local mode.
- The app runs as the ordinary user `frappe` (uid 1000) with no sudo rights; the image removes the
  passwordless sudo the base image comes with.
