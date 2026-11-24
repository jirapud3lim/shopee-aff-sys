# Studio staging operations

Staging runs Next.js, FastAPI, PostgreSQL 17, one database-backed campaign worker, and Prometheus. The startup migration runs after PostgreSQL is ready. The API and worker use separate containers. The release uses a PostgreSQL database, media volume, and secret separate from the existing Studio installation.

The staging entrypoint runs the backend as a non-root user and forces both live-publishing switches off. It loads no Meta credential and exposes the web and Prometheus only on host loopback. Billing routes and payment services are outside this deployment.

## Start and verify

From the repository root, create the database secret once. Keep it with local deployment secrets. Set `STAGING_DB_SECRET_FILE` to use an existing secret file.

```sh
test -s .env.staging-db-password || (umask 077 && openssl rand -hex 32 > .env.staging-db-password)
docker compose -f compose.staging.yml up --build -d --wait --wait-timeout 180
python3 ops/staging/smoke.py
```

- Studio is at [localhost:3110](http://127.0.0.1:3110). Prometheus is at [localhost:19090](http://127.0.0.1:19090).
- The smoke test creates a staging-only account and product, renders an MP4, queues a simulated Reel and comment, checks the worker and Prometheus, and verifies that live writes are rejected.
- Set `STAGING_WEB_PORT` and `STAGING_MONITOR_PORT` before startup to use different ports.

## Verify the release without Computer Use

GitHub Actions tests the production-mode web, API and worker images in a fixture-only stack with an internal Docker network. Safari Capture is disabled in the container web build. The browser runs as a separate test service and reaches Studio over loopback in the web container's network namespace. The test makes no provider requests from the browser and can run without a Safari extension, browser profile or provider credentials.

Run from the repository root with a fresh project and a staging database secret. Use the existing start instructions to create the secret if needed.

```sh
export COMPOSE_PROJECT_NAME=studio-release-check
export COMPOSE_FILE=compose.staging.yml:ops/staging/compose.no-computer-use.yml
docker compose up --build -d --wait --wait-timeout 180
docker compose exec -T -u studio \
  -e STAGING_WEB_ORIGIN=http://web:3000 -e STAGING_PROM_ORIGIN=http://prometheus:9090 \
  api python - --release < ops/staging/smoke.py
docker compose build browser
docker compose run --rm --no-deps -T browser
python3 ops/staging/check_no_computer_use.py
docker compose down -v
```

The API smoke check covers channel link storage, storyboard import and approval, MP4 import and full decode, simulation with comment read-back, live-write guards, report CSV deduplication and the worker metrics. The browser checks the manual link and storyboard controls and records any bridge events or external requests. The artifact check inspects running images and service configuration for Computer Use components, credentials and mounts, then checks the runtime network and application logs. The fixture run does not establish live provider access.

## Backup and restore

```sh
backup_id=$(bash ops/staging/backup.sh)
docker compose -f compose.staging.yml run --rm -T backup restore-check "$backup_id"
python3 ops/staging/smoke.py --backup-metric
```

The backup stops API and worker writers briefly, creates a PostgreSQL custom-format dump and a render archive with SHA-256 checksums, and restarts the services that were running. The worker can recover an interrupted job using its saved queue state. A successful backup records its timestamp. Backup bundles live in the staging backup volume and contain workspace data. Keep a restricted off-host copy for host-loss recovery and choose a retention schedule before production. To export a bundle from a running stack, use the maintenance container with a trusted destination.

```sh
mkdir -m 700 -p /path/to/secure-backups
docker compose -f compose.staging.yml run --rm -T --no-deps --entrypoint tar backup \
  -C /backups -cf - "$backup_id" > "/path/to/secure-backups/$backup_id.tar"
```

Run the host backup command daily during a quiet window if staging contains data worth retaining. The host scheduler and off-host destination depend on where staging is hosted. Use only backups from a trusted source. The restore drill creates its own scratch database, restores the dump in one transaction, and verifies a media file exists for every completed render. It removes its scratch database and extraction directory when finished.

## Monitor and recover

| Signal | What to check |
|---|---|
| [Targets](http://127.0.0.1:19090/targets) shows Studio down | Check API health, PostgreSQL readiness, and migration logs. |
| Worker heartbeat is stale | Check the worker container and database connection. Restart only the worker to resume the existing queue. |
| A job is overdue or needs attention | Open the Studio campaign and inspect the job state and worker logs. |
| Render storage is low | Check volume use and move archives to the designated backup destination. |
| No recent backup | Run the backup and restore drill. Review the checksum and backup timestamp. |

Prometheus shows these rules on its [Alerts page](http://127.0.0.1:19090/alerts). The stack has no external alert receiver. Use `docker compose -f compose.staging.yml logs --tail=100 api worker` for recent process logs.

GitHub Actions runs the staging startup, simulated workflow, backup and restore drill, and alert-rule checks in an isolated stack. Before changing a persistent environment, record the current image revision and take a verified backup. Stop the API and worker for schema changes that are incompatible with the running version. For rollback, use the previous images when the schema is compatible. For incompatible schema changes, restore to a separate stack first and verify readiness, data and media before switching traffic.
