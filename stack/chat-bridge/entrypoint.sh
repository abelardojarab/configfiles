#!/bin/sh
# Runs as root so it can fix ownership on the bind-mounted /data volume
# (host dir is owned by the host user, not uid 10001), then drops to the
# unprivileged openhands uid before exec'ing the bridge.
set -e
mkdir -p /data
chown 10001:10001 /data
exec setpriv --reuid=10001 --regid=10001 --clear-groups python bridge.py
