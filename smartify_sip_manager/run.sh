#!/usr/bin/with-contenv bashio
# In Home Assistant's s6 environment, this imports SUPERVISOR_TOKEN.
set -e
if [ -z "${SUPERVISOR_TOKEN:-}" ]; then
  bashio::log.warning 'SUPERVISOR_TOKEN nicht verfügbar: bitte Add-on frisch bauen und Supervisor-Zugriff prüfen.'
fi
exec python3 -u /app/app.py
