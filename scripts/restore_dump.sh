#!/bin/bash
set -euo pipefail

# === CONFIGURATION ===
DB_NAME="skyvan"                # database name
DB_USER="root"                  # MySQL user
DB_PASSWORD="rootpassword"      # MySQL password
CONTAINER_NAME="skyvan-db-1"             # Docker container name for MySQL
DUMP_FILE="./scripts/backup_2025-09-22_03-00-01.sql"  # path to your dump file (.sql or .sql.gz)

# === CHECK FILE ===
if [ ! -f "$DUMP_FILE" ]; then
  echo "🚨 Dump file not found: $DUMP_FILE"
  exit 1
fi

# === DROP & RECREATE DATABASE ===
echo "==> Dropping and recreating database $DB_NAME ..."
docker exec -i "$CONTAINER_NAME" mysql -u"$DB_USER" -p"$DB_PASSWORD" -e "DROP DATABASE IF EXISTS \`$DB_NAME\`; CREATE DATABASE \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# === IMPORT DUMP ===
echo "==> Importing dump into $DB_NAME ..."
if [[ "$DUMP_FILE" == *.gz ]]; then
  gunzip -c "$DUMP_FILE" | docker exec -i "$CONTAINER_NAME" mysql -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME"
else
  docker exec -i "$CONTAINER_NAME" mysql -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < "$DUMP_FILE"
fi

echo "✅ Restore completed successfully into database $DB_NAME"