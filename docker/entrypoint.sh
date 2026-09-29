#!/bin/bash
# Builds a bench around the apps/ folder from this repo (no bench init / get-app),
# then starts it. Safe to re-run on every container start.
set -e
cd /home/frappe/frappe-bench

: "${MODE:?set MODE=cloud or MODE=local in .env}"
: "${SITE_NAME:?set SITE_NAME in .env}"
: "${REDIS_URL:?set REDIS_URL in .env}"

# Docker creates volume mount points owned by root; bench refuses to run as root
sudo chown frappe:frappe env sites apps/*/node_modules apps/*/*/node_modules 2>/dev/null || true
mkdir -p config/pids logs sites

# --- Python: one virtualenv, every app installed in editable mode ---
[ -x env/bin/python ] || uv venv --seed --python 3.14 env
for app in apps/frappe apps/*/; do
    [ -f "$app/pyproject.toml" ] && uv pip install --quiet --python env/bin/python -e "$app"
done

# --- apps.txt: known apps in the order that works, then any custom app we add later ---
{
    for app in frappe telephony helpdesk crm; do echo "$app"; done
    for dir in apps/*/; do
        app=$(basename "$dir")
        case "$app" in frappe|telephony|helpdesk|crm) continue ;; esac
        [ -f "$dir/pyproject.toml" ] && echo "$app"
    done
} > sites/apps.txt

# --- Procfile (RUN_SCHEDULER=0 on all but one dev when sharing the cloud site) ---
{
    echo "web: bench serve --port 8000"
    echo "socketio: bench socketio"
    echo "worker: bench worker 1>> logs/worker.log 2>> logs/worker.error.log"
    [ "${RUN_SCHEDULER:-1}" = "1" ] && echo "schedule: bench schedule"
} > Procfile

# --- Config files, merged (never overwritten) so keys Frappe writes itself survive ---
env/bin/python /workspace/docker/write_config.py

# --- Site ---
# cloud: the site already lives in the shared DB, write_config.py pointed us at it.
# Never new-site / install-app / migrate for cloud here: that would hit the DB both devs share.
if [ "$MODE" = "local" ] && [ ! -f "sites/$SITE_NAME/site_config.json" ]; then
    until env/bin/python -c "import socket; socket.create_connection(('mariadb', 3306), 2)" 2>/dev/null; do
        echo "Waiting for local MariaDB..."; sleep 2
    done
    bench new-site "$SITE_NAME" \
        --db-host mariadb \
        --db-root-password "${DB_ROOT_PASSWORD:-123}" \
        --admin-password "${ADMIN_PASSWORD:-admin}" \
        --mariadb-user-host-login-scope='%' \
        --install-app telephony --install-app helpdesk --install-app crm
fi

# --- Frontend: install + build only on first start (rebuild by hand after frontend changes) ---
if [ ! -f sites/.built ]; then
    for app in apps/*/; do
        [ -f "$app/package.json" ] && (cd "$app" && yarn install)
    done
    bench build
    touch sites/.built
fi

exec bench start
