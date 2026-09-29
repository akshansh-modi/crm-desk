"""Merge settings from .env into common_site_config.json (and, in cloud mode, the
site's site_config.json). Merging instead of overwriting keeps keys Frappe or we
added by hand (mute_emails etc.)."""

import json
import os
from pathlib import Path

env = os.environ
sites = Path("sites")


def merge(path: Path, values: dict):
	path.parent.mkdir(parents=True, exist_ok=True)
	current = json.loads(path.read_text()) if path.exists() else {}
	current.update(values)
	path.write_text(json.dumps(current, indent=1))


def required(key: str) -> str:
	if not env.get(key):
		raise SystemExit(f"{key} is empty in .env (needed for MODE={env['MODE']})")
	return env[key]


merge(
	sites / "common_site_config.json",
	{
		"redis_cache": env["REDIS_URL"],
		"redis_queue": env["REDIS_URL"],
		"redis_socketio": env["REDIS_URL"],
		"default_site": env["SITE_NAME"],
		"serve_default_site": True,
		"developer_mode": 1,
		"server_script_enabled": 1,  # off by default in Frappe; needed for Server Scripts
		"webserver_port": 8000,
		"socketio_port": 9000,
	},
)

# Background-job queue names are "<bench_id>:<queue>"; workers with the same bench_id share
# a queue. Same code -> same id (prod pods: leave empty or set one shared value).
# Different code -> different id (two devs on the shared cloud Redis: each sets their own).
if env.get("BENCH_ID"):
	merge(sites / "common_site_config.json", {"bench_id": env["BENCH_ID"]})

if env["MODE"] == "cloud":
	# The folders `bench new-site` would have made (frappe/installer.py make_site_dirs);
	# cloud mode never runs new-site, and Frappe crashes without logs/ etc.
	for folder in ("public/files", "private/backups", "private/files", "locks", "logs"):
		(sites / env["SITE_NAME"] / folder).mkdir(parents=True, exist_ok=True)

	merge(
		sites / env["SITE_NAME"] / "site_config.json",
		{
			"db_type": "mariadb",
			"db_host": required("DB_HOST"),
			"db_port": int(required("DB_PORT")),
			"db_name": required("DB_NAME"),
			"db_user": required("DB_USER"),
			"db_password": required("DB_PASSWORD"),
			"db_ssl_ca": "/etc/ssl/certs/ca-certificates.crt",  # SkySQL requires SSL
			# Must be identical for everyone on the shared site, or saved passwords
			# (email accounts etc.) encrypted by one dev can't be decrypted by the other.
			"encryption_key": required("ENCRYPTION_KEY"),
		},
	)
