#!/usr/bin/env bash
set -euo pipefail
umask 077

export PGHOST=db PGUSER=studio PGDATABASE=studio
PGPASSWORD=$(</run/secrets/staging_db_password)
export PGPASSWORD
renders=/var/lib/studio/renders

backup() (
  exec 9>/backups/.archive.lock
  flock -n 9
  date_id=$(date -u +%Y%m%dT%H%M%S%NZ)
  directory=$(mktemp -d /backups/.incomplete.XXXXXX)
  marker=""
  trap '[[ -z "$marker" ]] || rm -f -- "$marker"; rm -rf -- "$directory"' EXIT

  pg_dump --format=custom --no-owner --no-acl --file="$directory/studio.dump"
  tar -C "$renders" -czf "$directory/renders.tar.gz" .
  (cd "$directory" && sha256sum studio.dump renders.tar.gz > SHA256SUMS)
  pg_restore --list "$directory/studio.dump" >/dev/null
  tar -tzf "$directory/renders.tar.gz" >/dev/null
  mv -- "$directory" "/backups/$date_id"
  marker=$(mktemp /backups/.last-success.XXXXXX)
  date -u +%s > "$marker"
  chmod 644 "$marker"
  mv -f -- "$marker" /backups/last-success
  printf '%s\n' "$date_id"
)

restore_check() (
  id=${1:?Provide the backup ID printed by backup}
  [[ "$id" =~ ^[0-9]{8}T[0-9]{15}Z$ ]] || { echo "Invalid backup ID" >&2; exit 2; }
  directory="/backups/$id"
  (cd "$directory" && sha256sum --check SHA256SUMS)
  scratch=$(mktemp -d)
  database="studio_restore_$(date +%s)_$$"
  created=false
  trap 'if $created; then dropdb "$database"; fi; rm -rf -- "$scratch"' EXIT

  createdb --template=template0 "$database"
  created=true
  pg_restore --dbname="$database" --single-transaction --exit-on-error --no-owner --no-acl "$directory/studio.dump"
  tar --no-same-owner -xzf "$directory/renders.tar.gz" -C "$scratch"
  psql -XAt --dbname="$database" --set=ON_ERROR_STOP=1 \
    -c "SELECT COALESCE(video_relpath, '') FROM renders WHERE status='completed'" |
    while IFS= read -r render; do
      [[ "$render" =~ ^[a-zA-Z0-9-]+/preview\.mp4$ && -s "$scratch/$render" ]] || {
        echo "A completed render has no valid artifact in the backup" >&2
        exit 1
      }
    done
  psql -X --dbname="$database" --set=ON_ERROR_STOP=1 -c \
    "SELECT (SELECT count(*) FROM organizations) AS workspaces,
            (SELECT count(*) FROM renders) AS renders,
            (SELECT count(*) FROM campaign_items) AS campaign_items;"
  echo "Restore drill passed for $id"
)

case "${1:-}" in
  backup) backup ;;
  restore-check) shift; restore_check "$@" ;;
  *) echo "Usage: archive.sh backup | restore-check BACKUP_ID" >&2; exit 2 ;;
esac
