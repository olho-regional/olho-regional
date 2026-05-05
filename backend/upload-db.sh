#!/usr/bin/env bash
# Upload the SQLite database to the VPS libSQL server.
# This replaces the existing database entirely.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/.env"

DB_PATH="${1:-$(dirname "$SCRIPT_DIR")/processamento/database/olho-regional.db}"

if [[ ! -f "$DB_PATH" ]]; then
  echo "Error: database not found at $DB_PATH"
  echo "Usage: $0 [path/to/database.db]"
  exit 1
fi

DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
echo "==> Uploading database ($DB_SIZE) to $VPS_USER@$VPS_HOST..."

# Stop the server, upload, restart
ssh "$VPS_USER@$VPS_HOST" "cd $VPS_PATH && docker compose stop sqld"

# Upload DB file to the volume directory
ssh "$VPS_USER@$VPS_HOST" "rm -rf $VPS_PATH/db-upload && mkdir -p $VPS_PATH/db-upload"
scp "$DB_PATH" "$VPS_USER@$VPS_HOST:$VPS_PATH/db-upload/data.db"

# Copy into the Docker volume and convert to sqld format
ssh "$VPS_USER@$VPS_HOST" "
  cd $VPS_PATH
  VOL_NAME=\$(docker volume ls --format '{{.Name}}' | grep sqld-data | head -1)
  if [ -z \"\$VOL_NAME\" ]; then echo 'Error: sqld-data volume not found'; exit 1; fi
  VOLUME_PATH=\$(docker volume inspect \$VOL_NAME --format '{{.Mountpoint}}')
  rm -rf \$VOLUME_PATH/data.sqld
  mkdir -p \$VOLUME_PATH/data.sqld
  cp db-upload/data.db \$VOLUME_PATH/data.sqld/data
  chmod -R 777 \$VOLUME_PATH/data.sqld
  rm -rf db-upload
  docker compose up -d sqld
"

echo "==> Done. Database uploaded and server restarted."
