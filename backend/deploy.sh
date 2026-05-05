#!/usr/bin/env bash
# Deploy the libSQL server to VPS (first time or update config)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/.env"

# Guard: refuse to deploy without auth key files
if [[ ! -f "$SCRIPT_DIR/jwt-public.pem" ]]; then
  echo "ERROR: jwt-public.pem not found — generate with: openssl genpkey -algorithm Ed25519 -out jwt-private.pem && openssl pkey -in jwt-private.pem -pubout -out jwt-public.pem" >&2
  exit 1
fi

echo "==> Deploying libSQL server to $VPS_USER@$VPS_HOST..."

# Ensure remote directory exists
ssh "$VPS_USER@$VPS_HOST" "mkdir -p $VPS_PATH"

# Update/upgrade OS
echo "==> Updating OS packages..."
ssh "$VPS_USER@$VPS_HOST" "
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get upgrade -y -qq
"

# Install Docker if not present
echo "==> Ensuring Docker is installed..."
ssh "$VPS_USER@$VPS_HOST" '
  if ! command -v docker &>/dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
  fi
  if ! docker compose version &>/dev/null; then
    echo "Installing Docker Compose plugin..."
    apt-get install -y -qq docker-compose-plugin
  fi
  systemctl enable --now docker
'

# Copy docker files, Caddyfile, certs, and JWT public key
scp "$SCRIPT_DIR/Dockerfile" "$SCRIPT_DIR/docker-compose.yml" "$SCRIPT_DIR/Caddyfile" "$SCRIPT_DIR/jwt-public.pem" "$VPS_USER@$VPS_HOST:$VPS_PATH/"
ssh "$VPS_USER@$VPS_HOST" "mkdir -p $VPS_PATH/certs"
scp "$SCRIPT_DIR/certs/origin.pem" "$SCRIPT_DIR/certs/origin-key.pem" "$VPS_USER@$VPS_HOST:$VPS_PATH/certs/"

# Copy .env if it exists
if [[ -f "$SCRIPT_DIR/.env" ]]; then
  scp "$SCRIPT_DIR/.env" "$VPS_USER@$VPS_HOST:$VPS_PATH/"
fi

# Configure firewall (idempotent — safe to re-run)
# Only allow SSH from anywhere + HTTPS from Cloudflare IPs
echo "==> Configuring firewall (ufw)..."
ssh "$VPS_USER@$VPS_HOST" "
  ufw --force reset
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow 22/tcp comment 'SSH'
  # Cloudflare IPv4 ranges
  ufw allow from 173.245.48.0/20 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 103.21.244.0/22 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 103.22.200.0/22 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 103.31.4.0/22 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 141.101.64.0/18 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 108.162.192.0/18 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 190.93.240.0/20 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 188.114.96.0/20 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 197.234.240.0/22 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 198.41.128.0/17 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 162.158.0.0/15 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 104.16.0.0/13 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 104.24.0.0/14 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 172.64.0.0/13 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 131.0.72.0/22 to any port 443 proto tcp comment 'Cloudflare'
  # Cloudflare IPv6 ranges
  ufw allow from 2400:cb00::/32 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 2606:4700::/32 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 2803:f800::/32 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 2405:b500::/32 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 2405:8100::/32 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 2a06:98c0::/29 to any port 443 proto tcp comment 'Cloudflare'
  ufw allow from 2c0f:f248::/32 to any port 443 proto tcp comment 'Cloudflare'
  ufw --force enable
"

# Build and start
ssh "$VPS_USER@$VPS_HOST" "cd $VPS_PATH && docker compose up -d --build"

echo "==> Done. libSQL running at https://$DOMAIN"
