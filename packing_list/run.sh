#!/usr/bin/with-contenv bashio
bashio::log.info "Starting Pakkeliste on port 8099"
cd /app
exec python3 -u server.py
