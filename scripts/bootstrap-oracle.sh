#!/usr/bin/env bash
# One-time bootstrap for a fresh Oracle Cloud / Ubuntu VM.
# Run as root or with sudo:
#   curl -fsSL https://raw.githubusercontent.com/srijan816/sniper/cursor/sniperip-pipeline-upgrade-f271/scripts/bootstrap-oracle.sh | sudo bash
#
# Or after clone:
#   sudo ./scripts/bootstrap-oracle.sh

set -euo pipefail

SNIPER_REPO_DIR="${SNIPER_REPO_DIR:-/home/ubuntu/sniper}"
SNIPER_BRANCH="${SNIPER_BRANCH:-cursor/sniperip-pipeline-upgrade-f271}"
SNIPER_REPO_URL="${SNIPER_REPO_URL:-https://github.com/srijan816/sniper.git}"

echo "==> Installing Docker..."
if ! command -v docker >/dev/null 2>&1; then
  apt-get update
  apt-get install -y ca-certificates curl git ufw
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "${VERSION_CODENAME:-jammy}") stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable docker
  systemctl start docker
fi

echo "==> Configuring firewall (SSH + HTTP + HTTPS)..."
ufw allow OpenSSH || true
ufw allow 80/tcp || true
ufw allow 443/tcp || true
ufw --force enable || true

echo "==> Cloning SniperIP to ${SNIPER_REPO_DIR}..."
mkdir -p "$(dirname "$SNIPER_REPO_DIR")"
if [[ ! -d "${SNIPER_REPO_DIR}/.git" ]]; then
  git clone --branch "$SNIPER_BRANCH" "$SNIPER_REPO_URL" "$SNIPER_REPO_DIR"
else
  echo "Repo already exists at ${SNIPER_REPO_DIR}, skipping clone."
fi

if [[ ! -f "${SNIPER_REPO_DIR}/.env" ]]; then
  cp "${SNIPER_REPO_DIR}/deploy/env.oracle.example" "${SNIPER_REPO_DIR}/.env"
  echo ""
  echo "Created ${SNIPER_REPO_DIR}/.env — edit secrets, then run:"
  echo "  cd ${SNIPER_REPO_DIR} && ./scripts/deploy-oracle.sh"
else
  echo ""
  echo "Bootstrap complete. Deploy with:"
  echo "  cd ${SNIPER_REPO_DIR} && ./scripts/deploy-oracle.sh"
fi
