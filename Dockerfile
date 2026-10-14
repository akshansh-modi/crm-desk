# Single-container image (built for the InfoSec review): web, socketio, worker and scheduler all run
# in this one container; MariaDB and Redis are external. See docker/IMAGE.md.
# The dev setup stays docker-compose.yml + docker/entrypoint.sh.
# Pinned by digest so every build starts from the same base as `frappe/bench:latest` did when this was written.
FROM frappe/bench@sha256:2f726e0386810dc21190d6d402c01bead40b721b1faf57b8b1c574af279fdca3

# DB connection comes from env (write_config.py's "cloud" path); no developer mode.
ENV MODE=cloud DEVELOPER_MODE=0
WORKDIR /home/frappe/frappe-bench

COPY --chown=frappe:frappe apps apps

# Python: one virtualenv, every app installed (same as docker/entrypoint.sh)
RUN uv venv --seed --python 3.14 env \
 && for app in apps/frappe apps/*/; do \
      if [ -f "$app/pyproject.toml" ]; then uv pip install --quiet --python env/bin/python -e "$app" || exit 1; fi; \
    done

# Bench folder + frontend build. The Helpdesk build reads socketio_port from common_site_config.json,
# so it must exist first; write_config.py fills in the rest when the container starts.
# FRAPPE_DOCKER_BUILD=1: skip telling Redis about the new assets (there's no Redis while building;
# without it the build retries forever).
RUN mkdir -p sites config/pids logs \
 && { for app in frappe telephony helpdesk crm; do echo "$app"; done; \
      for dir in apps/*/; do app=$(basename "$dir"); \
        case "$app" in frappe|telephony|helpdesk|crm) continue ;; esac; \
        if [ -f "$dir/pyproject.toml" ]; then echo "$app"; fi; \
      done; } > sites/apps.txt \
 && echo '{"socketio_port": 9000}' > sites/common_site_config.json \
 && for app in apps/*/; do \
      if [ -f "$app/package.json" ]; then (cd "$app" && yarn install --frozen-lockfile) || exit 1; fi; \
    done \
 && FRAPPE_DOCKER_BUILD=1 bench build \
 && find apps -name node_modules -prune -not -path apps/frappe/node_modules -exec rm -rf {} + \
 && yarn cache clean

# Copied after the build so editing these scripts doesn't redo the slow steps above.
COPY --chown=frappe:frappe docker docker

# The processes `bench start` runs. gunicorn, not `bench serve`: the dev server has an interactive
# debugger. socketio.js needs apps/frappe/node_modules, which is why the prune above keeps it.
RUN { echo 'web: cd sites && ../env/bin/gunicorn --pythonpath ../docker --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-2} --timeout 120 --preload wsgi:application'; \
      echo 'socketio: node apps/frappe/socketio.js'; \
      echo 'worker: bench worker'; \
      echo 'schedule: bench schedule'; } > Procfile

# Trust X-Forwarded-Proto from the ingress, which handles HTTPS: without it gunicorn treats every
# request as plain http and Frappe leaves the Secure flag off the login cookie. Only the ingress can
# reach the container, so "*" is fine; DevOps can narrow it to the ingress's address range.
ENV FORWARDED_ALLOW_IPS=*

# The base image lets the frappe user run anything as root without a password (sudoers +
# sudo group). Nothing here needs it, so take it away: the app user stays an ordinary user.
USER root
RUN sed -i '/^frappe ALL=(ALL) NOPASSWD: ALL$/d' /etc/sudoers && gpasswd -d frappe sudo
USER frappe

EXPOSE 8000 9000
CMD ["bash", "/home/frappe/frappe-bench/docker/image_start.sh"]
