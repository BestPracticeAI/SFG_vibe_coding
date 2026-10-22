#!/usr/bin/env bash
# Deploys an SFG vibe-coding tool beside the other apps (skill file, section 5). Idempotent.
#   sudo bash projects/<name>/deploy/install.sh
# Fill in the three values below and save as projects/<name>/deploy/install.sh.
# What it does: installs and starts the service, adds the nginx location in the HTTPS block, lists the
# app in the knowledge base navigation, and checks the health URL locally and over HTTPS.
set -euo pipefail
NAME='<name>'            # project folder, URL path and service suffix, e.g. customer-orders
APP_NAME='<App name>'    # label in the knowledge base menu, e.g. Customer orders
PORT='<port>'            # from the project index in the root README

HERE=$(cd "$(dirname "$0")" && pwd)
HOST=44.218.227.134
NGINX_CONF=/etc/nginx/conf.d/hello.conf
NGINX_COPY=/opt/sfg-kb/nginx-kb.conf
KB_BASE=/opt/sfg-kb/templates/base.html
UNIT="sfg-$NAME.service"

[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
[ -f "$HERE/$UNIT" ] || { echo "missing $HERE/$UNIT"; exit 1; }
[ -f "$HERE/nginx-location.conf" ] || { echo "missing $HERE/nginx-location.conf"; exit 1; }
free -m | sed -n 2p

# the platform MCP server must already be installed (sage-mcp.service); never ship a second copy
systemctl is-active --quiet sage-mcp.service || { echo "sage-mcp.service is not active; ask the platform champion"; exit 1; }

# stop a development copy on the port so the unit can take it (by PID, never pkill -f)
for pid in $(pgrep -f "[g]unicorn.*127.0.0.1:$PORT" || true); do kill "$pid" || true; done
sleep 1

install -m 644 "$HERE/$UNIT" "/etc/systemd/system/$UNIT"
systemctl daemon-reload
systemctl enable --now "$UNIT"
systemctl restart "$UNIT"

if ! grep -q "location /$NAME " "$NGINX_CONF"; then
  python3 - "$NGINX_CONF" "$HERE/nginx-location.conf" <<'PY'
import sys
conf, snippet = sys.argv[1], sys.argv[2]
s = open(conf).read()
i = s.rindex('    location / {')   # the HTTPS server's catch-all is the last one; the first is the port-80 redirect
open(conf, 'w').write(s[:i] + open(snippet).read().rstrip('\n') + '\n' + s[i:])
PY
  [ -f "$NGINX_COPY" ] && cp "$NGINX_CONF" "$NGINX_COPY"
fi
nginx -t && systemctl reload nginx

if ! grep -q "'/$NAME/'" "$KB_BASE"; then
  sed -i "s#('/sources','Sources')#('/$NAME/','$APP_NAME'),('/sources','Sources')#" "$KB_BASE"
  systemctl restart sfg-kb.service
fi

sleep 2
curl -fsS "http://127.0.0.1:$PORT/$NAME/healthz" >/dev/null && echo "$NAME: up on 127.0.0.1:$PORT"
curl -fsS -o /dev/null -w "https://$HOST/$NAME/ -> HTTP %{http_code}\n" "https://$HOST/$NAME/"
free -m | sed -n 2p
