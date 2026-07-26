#!/usr/bin/env bash
set -euo pipefail
BACKUP_ROOT=/opt/tcrm/backups
STAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_ROOT"
sudo -u postgres pg_dumpall | gzip > "$BACKUP_ROOT/pg_all_${STAMP}.sql.gz"
tar -C /opt/tcrm -czf "$BACKUP_ROOT/filestore_${STAMP}.tar.gz" tcrm_data
# Retain 14 days
find "$BACKUP_ROOT" -type f -mtime +14 -delete
echo "Backup complete: $STAMP"
