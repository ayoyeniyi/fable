#!/usr/bin/env bash
# Prepares a fresh Ubuntu 24.04 VM to run Fable's preparation service (docs/BACKEND.md). Run as root by
# deploy/deploy.sh; safe to run again (each step checks before it acts).
#
#   Blender 5.2.3 (CPU)  -> /opt/blender           checked against blender.org's published SHA-256
#   the service          -> /opt/fable             run as the unprivileged user "fable" by systemd
#   secrets              -> /etc/fable/env         the Claude key, root-only, read by systemd
#   HTTPS                -> Caddy                  certificates from Let's Encrypt for FABLE_HOST
set -euo pipefail
BLENDER_VERSION=5.2.3
BLENDER_SERIES=5.2

export DEBIAN_FRONTEND=noninteractive
echo "== packages"
apt-get update -qq
apt-get install -y -qq caddy bubblewrap rsync curl xz-utils ufw \
  libx11-6 libxi6 libxxf86vm1 libxfixes3 libxrender1 libxkbcommon0 libsm6 libice6 libgl1 libegl1 >/dev/null

echo "== Blender $BLENDER_VERSION"
if ! /opt/blender/blender --version 2>/dev/null | grep -q "Blender $BLENDER_VERSION"; then
  arch=$(uname -m); case "$arch" in x86_64) b=linux-x64;; aarch64) b=linux-arm64;; *) echo "unsupported CPU $arch"; exit 1;; esac
  f="blender-$BLENDER_VERSION-$b.tar.xz"
  cd /tmp
  curl -fsSLO "https://download.blender.org/release/Blender$BLENDER_SERIES/$f"
  curl -fsSL "https://download.blender.org/release/Blender$BLENDER_SERIES/blender-$BLENDER_VERSION.sha256" | grep " $f\$" > "$f.sha256"
  sha256sum -c "$f.sha256"
  rm -rf /opt/blender && mkdir -p /opt/blender && tar -xJf "$f" -C /opt/blender --strip-components=1 && rm -f "$f" "$f.sha256"
fi
/opt/blender/blender -b --factory-startup -noaudio --python-expr "import bpy; print('BLENDER_OK', bpy.app.version_string)" 2>/dev/null | grep BLENDER_OK

echo "== user and folders"
id fable >/dev/null 2>&1 || useradd --system --home-dir /var/lib/fable --create-home --shell /usr/sbin/nologin fable
mkdir -p /opt/fable/bin /opt/fable/out /etc/fable /var/lib/fable
chown -R fable:fable /opt/fable/out /var/lib/fable
chmod 700 /etc/fable

echo "== sandbox"
# Ubuntu 24.04 lets a program create user namespaces (which bubblewrap needs) only if an AppArmor profile allows it.
# This profile allows it for bwrap alone; everything else stays restricted.
if [ ! -f /etc/apparmor.d/bwrap ]; then
  cat > /etc/apparmor.d/bwrap <<'PROFILE'
abi <abi/4.0>,
include <tunables/global>

profile bwrap /usr/bin/bwrap flags=(unconfined) {
  userns,
  include if exists <local/bwrap>
}
PROFILE
  apparmor_parser -r /etc/apparmor.d/bwrap
fi

# room builds run Claude-written scripts inside bubblewrap; make sure it works here (Ubuntu's AppArmor profile for
# bwrap allows the user namespaces it needs)
if su -s /bin/bash fable -c "bwrap --die-with-parent --unshare-all --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp --tmpfs /etc/fable -- /opt/blender/blender -b --factory-startup -noaudio --python-expr \"print('SANDBOX_OK')\"" 2>/dev/null | grep -q SANDBOX_OK; then
  echo "sandbox: ok"; echo "FABLE_SANDBOX=--sandbox" > /etc/fable/sandbox
else
  echo "sandbox: bubblewrap does not work on this VM; room builds will run unsandboxed (see docs/BACKEND.md)"; echo "FABLE_SANDBOX=" > /etc/fable/sandbox
fi

echo "== firewall"
ufw allow OpenSSH >/dev/null; ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null; ufw --force enable >/dev/null
echo "PROVISION_OK"
