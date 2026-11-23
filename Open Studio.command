#!/bin/bash
set -e
# Keep each background job in its own process group, including its children.
set -m

cd -- "$(dirname -- "$0")"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

host=127.0.0.1
web_port=3014
api_port=8001
studio_url="http://$host:$web_port"
export STUDIO_API_ORIGIN="http://$host:$api_port"
qa_database="$PWD/backend/.local/meta-acceptance.db"
qa_password_file="$PWD/backend/.local/meta-read-qa-password"
use_qa_account=false
if [[ -z ${DATABASE_URL:-} && -f $qa_database && -s $qa_password_file && -r $qa_password_file ]]; then
    DATABASE_URL="sqlite:///$qa_database"
    use_qa_account=true
fi
export DATABASE_URL="${DATABASE_URL:-sqlite:///$PWD/backend/local.db}"
export PYTHAINLP_READ_ONLY=1 PYTHAINLP_OFFLINE=1

if [[ -z ${SSL_CERT_FILE:-} && -r /etc/ssl/cert.pem ]]; then
    export SSL_CERT_FILE=/etc/ssl/cert.pem
fi
export META_STUDIO_PUBLISH_ENABLED=false CAMPAIGN_LIVE_ENABLED=false

jobs_to_stop=()
review_dir=""
cleanup() {
    trap '' HUP INT TERM
    set +m
    for pid in "${jobs_to_stop[@]}"; do
        kill -TERM -- "-$pid" 2>/dev/null || true
    done
    # Give the servers time to shut down, then remove any remaining children.
    for attempt in {1..20}; do
        running=false
        for pid in "${jobs_to_stop[@]}"; do
            if kill -0 -- "-$pid" 2>/dev/null; then
                running=true
            fi
        done
        [[ $running == true ]] || break
        sleep 0.1
    done
    for pid in "${jobs_to_stop[@]}"; do
        kill -KILL -- "-$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
    done
    if [[ -n $review_dir ]]; then
        rm -f -- "$review_dir/ticket"
        rmdir -- "$review_dir"
    fi
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

for executable in uv node npm; do
    if ! command -v "$executable" >/dev/null; then
        echo "Missing $executable. See 'Run locally' in README.md." >&2
        exit 1
    fi
done
for port in "$web_port" "$api_port"; do
    if lsof -nP -iTCP:"$port" -sTCP:LISTEN -t >/dev/null; then
        echo "Port $port is already in use. Close its server before opening Studio." >&2
        exit 1
    fi
done

if [[ ! -x apps/web/node_modules/.bin/next ]]; then
    npm ci --prefix apps/web &
    jobs_to_stop=("$!")
    wait "$!"
    jobs_to_stop=()
fi

uv run --project backend --locked alembic -c backend/alembic.ini upgrade head &
jobs_to_stop=("$!")
wait "$!"
jobs_to_stop=()

browser_url="$studio_url"
if [[ $use_qa_account == true ]]; then
    review_dir=$(mktemp -d "${TMPDIR:-/tmp}/studio-review.XXXXXXXX")
    nonce=$(/usr/bin/openssl rand -hex 32)
    (umask 077; printf '%s' "$nonce" > "$review_dir/ticket")
    export STUDIO_REVIEW_TICKET="$review_dir/ticket"
    export STUDIO_REVIEW_PASSWORD_FILE="$qa_password_file"
    browser_url="$studio_url#review-login=$nonce"
fi

uv run --project backend --no-sync uvicorn --app-dir backend app.main:app --host "$host" --port "$api_port" &
api_pid=$!
jobs_to_stop=("$api_pid")
npm run dev --prefix apps/web -- --webpack --hostname "$host" --port "$web_port" &
web_pid=$!
jobs_to_stop+=("$web_pid")
set +m

servers_running() {
    kill -0 "$api_pid" 2>/dev/null && kill -0 "$web_pid" 2>/dev/null
}

echo "Starting Studio at $studio_url ..."
for attempt in {1..90}; do
    if ! servers_running; then
        echo 'Studio could not start. See the server output above.' >&2
        exit 1
    fi
    if curl -fs --noproxy '*' --max-time 1 "$studio_url/api/v1/health" >/dev/null; then
        echo "Studio is ready at $studio_url. Close this Terminal window or press Ctrl+C to stop it."
        open -a Safari "$browser_url" || echo "Open $studio_url in your browser."
        while servers_running; do
            sleep 1
        done
        echo 'A Studio server stopped. Shutting down the other server.' >&2
        exit 1
    fi
    sleep 1
done

echo 'Studio did not become ready. See the server output above.' >&2
exit 1
