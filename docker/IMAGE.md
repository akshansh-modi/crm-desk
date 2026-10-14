# Docker image (single container, for SIT and the InfoSec review)

Developers use `docker-compose.yml`. This is the deployment path: the root `Dockerfile` builds
**one image**, and **one pod** runs the whole app (web, realtime, background jobs, scheduler).
MariaDB and Redis are **not** in the image: point it at existing ones with env vars.
Target: AWS EKS behind the existing ingress. Splitting into separate pods comes after the InfoSec review.

## Build (Jenkins)

```bash
docker build -t <ecr-repo>/crm-desk:<git-commit> .
docker push <ecr-repo>/crm-desk:<git-commit>
```

- **BuildKit is required** (Docker's default builder since version 23): the Dockerfile uses build cache mounts.
- **Build for the nodes' CPU type.** Graviton nodes are `linux/arm64`, the others `linux/amd64`. Pass `--platform` to match, or pin the pod with `nodeSelector: kubernetes.io/arch: amd64`.
- **Build time:** the Python packages step only reruns when a `pyproject.toml` changes; a code-only change rebuilds in a few minutes (mostly the frontend). On a fresh build machine, the first build takes about 25 minutes. Agents that start empty every time lose the cache; use `--cache-from`/`--cache-to type=registry` on ECR there.
- **Network during the build:** PyPI, the npm registry and GitHub (a few packages are installed from GitHub).
- Tag images with the git commit, never only `latest`, so you always know what runs and can roll back.

## Kubernetes settings

- **`replicas: 1` and `strategy: Recreate`, always.** The default RollingUpdate briefly runs two pods: two schedulers (duplicate emails and tickets), two first-start installs racing on an empty database, and an EBS volume that can't attach to the second pod.
- **Probes.** The first start (creating the site, installing apps, migrating) takes several minutes before anything listens:
  - `startupProbe`: TCP 8000, allowing up to 30 minutes (e.g. `periodSeconds: 10`, `failureThreshold: 180`). A probe that kills the pod mid-install leaves a half-built database that has to be emptied by hand.
  - `livenessProbe`: TCP 8000. Not the HTTP ping: it needs the database, so a database blip would restart the pod.
  - `readinessProbe`: HTTP `GET /api/method/ping` on 8000, which returns `{"message":"pong"}`.
- **Security context:** `runAsNonRoot: true` works (the image runs as uid 1000). Set `allowPrivilegeEscalation: false` and `fsGroup: 1000`. `readOnlyRootFilesystem` is **not** supported: the start script writes config into `sites/`.
- **Shutdown:** on a deploy, the process manager gives running requests and background jobs 5 seconds, then stops them. Fine for SIT.
- **Network:** only the ingress should reach ports 8000 and 9000 (a NetworkPolicy, if the cluster enforces them). The image trusts `X-Forwarded-*` headers from any address that reaches it.
- **Logs:** gunicorn's access log and process output go to stdout (CloudWatch). Frappe's own logs are files inside the container (`sites/<SITE_NAME>/logs/`, `logs/`), lost when the pod is replaced, unless they're on the uploads volume.

## Ingress

- **Host rule:** match only `SITE_NAME`. No catch-all rule pointing at this service.
- **Routing:** everything to port `8000`, **except the path `/socket.io`, which goes to port `9000`**, with WebSocket upgrade allowed.
- **Headers to the pod:** keep the `Host` header (it must equal `SITE_NAME`) and send `X-Forwarded-Proto: https` (Frappe then puts `Secure` on the login cookie). `X-Forwarded-For` must be overwritten, not appended, or clients can fake their IP and dodge the login lockout: on an ALB set `routing.http.xff_header_processing.mode=replace`; on ingress-nginx keep `use-forwarded-headers` off (the default), so it sets the header itself.
- **Upload size:** about 50 MB (ingress-nginx defaults to 1 MB). **Timeouts:** 120 s (on an ALB, the idle timeout).
- **Security headers:** nothing in the image adds them, so add them here: `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin`.
- **ALB health check** for the 9000 target: path `/socket.io/?EIO=4&transport=polling`.

## Env vars (a Kubernetes Secret)

| Variable | Value |
|---|---|
| `SITE_NAME` | **The host name people open in the browser**, e.g. `crm-desk-sit.example.com` |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | MariaDB, e.g. RDS (tested with MariaDB 11.8). The database and user must exist; the database must be empty on the first start. |
| `DB_SSL_CA` | Path of the CA file for SSL to the database. For RDS: Amazon's `global-bundle.pem` (not in the image), mounted from a ConfigMap, e.g. `/etc/rds/global-bundle.pem`. The certificate's host name is checked. Empty means no SSL. |
| `REDIS_URL` | `redis://default:<password>@<host>:<port>`, or `rediss://…` for ElastiCache with encryption in transit. Use a non-serverless, cluster-mode-disabled ElastiCache. |
| `ENCRYPTION_KEY` | Generate once and never change it: `python3 -c "import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"` |
| `ADMIN_PASSWORD` | Administrator password. Only used on the first start |
| `AUTO_MIGRATE` | `1` runs `migrate` on every start, so new doctypes and fields in a new image get their tables. Set it on SIT (its own database). Default `0`. |
| `HOST_NAME` | Optional. Base URL for links in emails. Default `https://<SITE_NAME>` |
| `INSTALL_APPS` | Optional. Default `telephony helpdesk crm insurance` |
| `GUNICORN_WORKERS` | Optional. Default `2` |

## Storage

Uploaded files (ticket attachments, policy documents) are written to
`/home/frappe/frappe-bench/sites/<SITE_NAME>/`. Every deploy replaces the pod, so without a volume
they're lost on each deploy. If they should survive: one EBS volume (ReadWriteOnce) mounted at exactly
that path. With one pod it doesn't need to be shared. EBS lives in one availability zone, so the pod
stays in that zone. Never mount over `sites/`: that hides the built frontend.

## What happens on each deploy

1. The new pod starts and writes its config from the env vars.
2. Empty database: it creates the site. Existing site: it skips that.
3. `AUTO_MIGRATE=1`: `migrate` updates the tables for the new code.
4. Apps in `INSTALL_APPS` that aren't installed yet get installed.
5. Web, realtime, worker and scheduler start; the readiness probe turns green.

## Keep in mind

- **Use a database of its own.** Never point this at the team's shared dev database (`.env.cloud.example`).
- No demo data. The seed script only runs in local mode.
- The app runs as uid 1000 with no sudo; Server Scripts and developer mode are off.
- To try the image on a laptop: run MariaDB and Redis containers on one docker network, then
  `docker run --network <net> -p 8000:8000 -p 9000:9000 --env-file crm-desk.env <image>`. Desk's live
  updates need the `/socket.io` routing, so without an ingress only Helpdesk and CRM get them.
