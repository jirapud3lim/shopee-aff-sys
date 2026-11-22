#!/usr/bin/env bash
set -euo pipefail

DATABASE_URL=$(python - <<'PY'
from pathlib import Path
from sqlalchemy import URL

password = Path("/run/secrets/staging_db_password").read_text().rstrip("\r\n")
if not password:
    raise SystemExit("The staging database secret is empty")
print(URL.create("postgresql+psycopg", username="studio", password=password,
                 host="db", port=5432, database="studio").render_as_string(hide_password=False))
PY
)
export DATABASE_URL
export CAMPAIGN_LIVE_ENABLED=false META_STUDIO_PUBLISH_ENABLED=false
unset META_PAGE_ACCESS_TOKEN META_TEST_PAGE_ID META_APP_SECRET
exec gosu studio "$@"
