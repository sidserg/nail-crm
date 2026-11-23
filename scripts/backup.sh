#!/bin/sh
# Daily PostgreSQL backup: local ./backups + optional S3 upload.
set -eu

KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"
mkdir -p /backups

echo "Backup service: every ${INTERVAL}s, local retention ${KEEP_DAYS} days, S3: ${S3_BUCKET:-off}"
sleep 30  # let the database finish starting up

while true; do
  TS=$(date +%Y%m%d_%H%M%S)
  FILE="/backups/nailcrm_${TS}.sql.gz"
  echo "[$(date)] pg_dump…"
  if pg_dump -h "$PGHOST" -U "$PGUSER" "$PGDATABASE" | gzip > "$FILE"; then
    echo "[$(date)] saved $FILE ($(du -h "$FILE" | cut -f1))"
    if [ -n "${S3_BUCKET:-}" ]; then
      ENDPOINT_ARG=""
      [ -n "${S3_ENDPOINT:-}" ] && ENDPOINT_ARG="--endpoint-url ${S3_ENDPOINT}"
      # shellcheck disable=SC2086
      if aws s3 cp "$FILE" "s3://${S3_BUCKET}/${S3_PREFIX:-nailcrm}/$(basename "$FILE")" $ENDPOINT_ARG; then
        echo "[$(date)] uploaded to S3"
      else
        echo "[$(date)] WARNING: S3 upload failed (local copy kept)"
      fi
    fi
  else
    echo "[$(date)] ERROR: pg_dump failed"
    rm -f "$FILE"
  fi
  find /backups -name 'nailcrm_*.sql.gz' -mtime +"$KEEP_DAYS" -delete
  sleep "$INTERVAL"
done
