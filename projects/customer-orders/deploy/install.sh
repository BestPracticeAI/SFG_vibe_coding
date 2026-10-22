#!/usr/bin/env bash
# Deploys Customer Orders beside the other SFG apps (skill file, section 4). Idempotent.
#   sudo bash projects/customer-orders/deploy/install.sh
# What it does: installs and starts the two services (MCP server, dashboard), adds the nginx location,
# lists the app in the knowledge base navigation (the company project index), and checks the health URL.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
NGINX_CONF=/etc/nginx/conf.d/hello.conf
NGINX_COPY=/opt/sfg-kb/nginx-kb.conf
KB_BASE=/opt/sfg-kb/templates/base.html

[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
free -m | sed -n 2p

# stop development copies of either server so the units can take the ports
for pid in $(pgrep -f '[s]age_mcp.server --http' || true); do kill "$pid" || true; done
for pid in $(pgrep -f '[g]unicorn.*127.0.0.1:8102' || true); do kill "$pid" || true; done
sleep 1

install -m 644 "$HERE/sage-mcp.service" /etc/systemd/system/sage-mcp.service
install -m 644 "$HERE/sfg-customer-orders.service" /etc/systemd/system/sfg-customer-orders.service
systemctl daemon-reload
systemctl enable --now sage-mcp.service
systemctl enable --now sfg-customer-orders.service
systemctl restart sfg-customer-orders.service

if ! grep -q 'location /customer-orders' "$NGINX_CONF"; then
  python3 - "$NGINX_CONF" "$HERE/nginx-location.conf" <<'PY'
import sys
conf, snippet = sys.argv[1], sys.argv[2]
s = open(conf).read()
i = s.rindex('    location / {')   # the HTTPS server's catch-all is the last one
open(conf, 'w').write(s[:i] + open(snippet).read() + '\n' + s[i:])
PY
  [ -f "$NGINX_COPY" ] && cp "$NGINX_CONF" "$NGINX_COPY"
fi
nginx -t && systemctl reload nginx

if ! grep -q "/customer-orders/" "$KB_BASE"; then
  sed -i "s#('/tutor','Tutor')#('/tutor','Tutor'),('/customer-orders/','Customer orders')#" "$KB_BASE"
  systemctl restart sfg-kb.service
fi

sleep 2
curl -fsS http://127.0.0.1:8102/customer-orders/healthz >/dev/null && echo "customer-orders: up on 127.0.0.1:8102"
curl -fsS -o /dev/null -w "https://44.218.227.134/customer-orders/ -> HTTP %{http_code}\n" https://44.218.227.134/customer-orders/
free -m | sed -n 2p
