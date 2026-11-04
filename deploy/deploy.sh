#!/usr/bin/env bash
# Deploys Fable's preparation service to a VM (docs/BACKEND.md).
#
#   deploy/deploy.sh <vm address> [--domain name.example.com] [--user root] [--update-key]
#
# First run: sets the VM up (deploy/provision.sh), copies the service and what it needs, installs the Claude key from
# ~/.config/fable/env (never printed), and starts it behind HTTPS. Later runs update the code and content only.
# It writes the address the app uses (with its access key) to ~/.config/fable/service-url, which the next Unity
# build reads (Assets/Fable/Editor/ServiceConfig.cs). Without --domain the host name is <ip>.sslip.io, a public
# name that resolves to the VM's address, so Let's Encrypt can issue a certificate with no DNS set-up.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO=$PWD

VM=""; DOMAIN=""; SSH_USER=root; UPDATE_KEY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --domain) DOMAIN=$2; shift 2;;
    --user) SSH_USER=$2; shift 2;;
    --update-key) UPDATE_KEY=1; shift;;
    -h|--help) sed -n 2,11p "$0"; exit 0;;
    *) VM=$1; shift;;
  esac
done
[ -n "$VM" ] || { echo "usage: deploy/deploy.sh <vm address> [--domain name] [--user root] [--update-key]"; exit 2; }
SSH="ssh -o StrictHostKeyChecking=accept-new $SSH_USER@$VM"
CONF=~/.config/fable
[ -f "$CONF/env" ] || { echo "no Claude key: $CONF/env is missing"; exit 1; }

if [ -z "$DOMAIN" ]; then
  ip=$($SSH "curl -fsS4 https://api.ipify.org || hostname -I | cut -d' ' -f1")
  DOMAIN="${ip//./-}.sslip.io"
fi
# the access key: made once and kept, so rebuilt apps keep working after a redeploy
[ -f "$CONF/access-key" ] || (umask 077; openssl rand -hex 16 > "$CONF/access-key")
ACCESS_KEY=$(cat "$CONF/access-key")

echo "== provisioning $VM"
$SSH "bash -s" < deploy/provision.sh | tail -4

echo "== building the service for the VM"
arch=$($SSH uname -m); case "$arch" in x86_64) GOARCH=amd64;; aarch64) GOARCH=arm64;; *) echo "unsupported $arch"; exit 1;; esac
(cd interpreter && CGO_ENABLED=0 GOOS=linux GOARCH=$GOARCH go build -trimpath -o "$REPO/out/deploy/fable-interpreter" ./cmd/fable-interpreter)

echo "== copying code and content"
R="rsync -az --delete -e 'ssh -o StrictHostKeyChecking=accept-new'"
eval $R out/deploy/fable-interpreter "$SSH_USER@$VM:/opt/fable/bin/"
eval $R --include='*.py' --exclude='*' blender/ "$SSH_USER@$VM:/opt/fable/blender/"
for d in content schema book; do eval $R "$d/" "$SSH_USER@$VM:/opt/fable/$d/"; done
# the built places' models, for chapter thumbnails (glTF, buffers and textures only)
$SSH "mkdir -p /opt/fable/unity/Fable/Assets/Fable/Models"
eval $R --include='*/' --include='*.gltf' --include='*.bin' --include='*.png' --include='*.jpg' --exclude='*' --prune-empty-dirs \
  unity/Fable/Assets/Fable/Models/ "$SSH_USER@$VM:/opt/fable/unity/Fable/Assets/Fable/Models/"
# chapter experiences already prepared on the Mac, so judges get them at once (first deploy only; the VM's own work
# is never overwritten)
if ! $SSH test -f /opt/fable/out/chapters/jobs.json; then
  [ -d out/chapters ] && eval rsync -az -e "'ssh -o StrictHostKeyChecking=accept-new'" out/chapters/ "$SSH_USER@$VM:/opt/fable/out/chapters/"
fi
$SSH "chown -R fable:fable /opt/fable/out && chmod 755 /opt/fable/bin/fable-interpreter"

echo "== secrets and settings"
if [ $UPDATE_KEY = 1 ] || ! $SSH test -s /etc/fable/env; then
  $SSH "umask 077; cat > /etc/fable/env" < "$CONF/env"
  echo "Claude key installed (root-only file on the VM)"
fi
$SSH "umask 077; printf 'FABLE_HOST=%s\nFABLE_ACCESS_KEY=%s\n' '$DOMAIN' '$ACCESS_KEY' > /etc/fable/caddy.env"
scp -q -o StrictHostKeyChecking=accept-new deploy/fable.service "$SSH_USER@$VM:/etc/systemd/system/fable.service"
scp -q -o StrictHostKeyChecking=accept-new deploy/Caddyfile "$SSH_USER@$VM:/etc/caddy/Caddyfile"
$SSH "mkdir -p /etc/systemd/system/caddy.service.d /var/log/caddy && chown caddy:caddy /var/log/caddy && printf '[Service]\nEnvironmentFile=/etc/fable/caddy.env\n' > /etc/systemd/system/caddy.service.d/fable.conf \
  && systemctl daemon-reload && systemctl enable -q fable caddy && systemctl restart fable caddy"

echo "== checking https://$DOMAIN"
URL="https://$DOMAIN/k/$ACCESS_KEY"
for i in $(seq 1 30); do
  if curl -fsS --max-time 10 "$URL/health" >/dev/null 2>&1; then break; fi; sleep 4
done
curl -fsS --max-time 10 "$URL/health" | head -c 300; echo
code=$(curl -s -o /dev/null -w '%{http_code}' "https://$DOMAIN/health")
echo "without the access key: HTTP $code (want 404)"
(umask 077; printf '%s\n' "$URL" > "$CONF/service-url")
echo "DEPLOYED https://$DOMAIN (the app's address, with its access key, is in $CONF/service-url; the next Unity build uses it)"
