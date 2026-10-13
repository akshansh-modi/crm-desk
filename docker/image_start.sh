#!/bin/bash
# Start script of the single-container image (Dockerfile). See docker/IMAGE.md.
set -e
cd /home/frappe/frappe-bench

: "${SITE_NAME:?set SITE_NAME (the host name people open in the browser)}"
: "${REDIS_URL:?set REDIS_URL}"

# common_site_config.json + sites/<site>/site_config.json from env, on every start
env/bin/python docker/write_config.py

# Empty database: build the site in it (same checks as docker/entrypoint.sh in cloud mode)
rc=0; env/bin/python docker/site_in_db.py || rc=$?
if [ "$rc" = 3 ]; then
	echo "Database '$DB_NAME' is empty, creating site $SITE_NAME in it..."
	bench new-site "$SITE_NAME" --force --no-setup-db \
		--db-name "$DB_NAME" \
		--admin-password "${ADMIN_PASSWORD:?set ADMIN_PASSWORD for the first start}"
	bench --site "$SITE_NAME" scheduler enable
elif [ "$rc" = 4 ]; then
	echo "Database '$DB_NAME' is half-built (has tables, but Frappe never finished installing). Empty it by hand, then start again."
	exit 1
elif [ "$rc" != 0 ]; then
	echo "Can't reach the database (see error above)"; exit 1
fi

# Already-installed apps are skipped. No `migrate` here, same as dev: run it by hand after an image update.
bench --site "$SITE_NAME" install-app ${INSTALL_APPS:-telephony helpdesk crm insurance}

# --no-dev: plain `bench start` sets DEV_SERVER=true, which shows full Python error tracebacks to
# every visitor, including logged-out ones. Fine on a dev laptop, an information leak anywhere else.
exec bench start --no-dev
