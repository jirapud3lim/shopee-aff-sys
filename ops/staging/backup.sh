#!/usr/bin/env bash
# Stop staging writers for the PostgreSQL and media snapshot.
set -euo pipefail
cd "$(dirname "$0")/../.."
compose=(docker compose -f compose.staging.yml)
lock=.env.staging-backup-lock
mkdir "$lock" 2>/dev/null || { echo "A staging backup is already running" >&2; exit 1; }
services=()
resume_services() {
  status=$?
  trap - EXIT
  if (( ${#services[@]} )); then
    "${compose[@]}" start "${services[@]}" >/dev/null || status=1
  fi
  rmdir "$lock"
  exit "$status"
}
trap resume_services EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

running=$("${compose[@]}" ps --status running --services)
for service in api worker; do
  if grep -qx "$service" <<< "$running"; then services+=("$service"); fi
done
if (( ${#services[@]} )); then "${compose[@]}" stop "${services[@]}" >&2; fi
"${compose[@]}" run --rm -T --no-deps backup backup
