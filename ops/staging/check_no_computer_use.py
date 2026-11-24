"""Check the images and running containers used by the isolated release smoke test."""

import json
import re
import subprocess


def docker(*args):
    return subprocess.check_output(("docker", *args), text=True).strip()


FORBIDDEN_ENV = re.compile(
    r"^(CODEX|CUA|BROWSER_USE|PLAYWRIGHT|PUPPETEER|SELENIUM)(_|$)|^OPENAI_API_KEY$",
    re.IGNORECASE,
)
FORBIDDEN_MARKERS = r"cua_repl|mcp__cua|unified-computer-use|@openai/codex|codex[[:space:]-]+computer[[:space:]-]+use"
LOG_MARKERS = re.compile(r"cua_repl|mcp__cua|unified-computer-use|@openai/codex|codex[\s-]+computer[\s-]+use",
                         re.IGNORECASE)
RUNTIME_SCAN = r"""
set -eu
for tool in codex playwright puppeteer chromedriver geckodriver google-chrome chromium firefox; do
    if command -v "$tool" >/dev/null 2>&1; then
        echo "Unexpected runtime executable: $tool" >&2
        exit 1
    fi
done
unexpected=$(find /app "$1" \( -name .codex -o -name safari-extension -o -name 'cua_repl*' \
    -o -path '*/node_modules/playwright*' -o -path '*/node_modules/puppeteer*' \
    -o -path '*/node_modules/@playwright' -o -path '*/site-packages/playwright*' \
    -o -path '*/site-packages/selenium*' -o -name auth.json -o -name .env -o -name '.env.*' \) -print -quit)
if [ -n "$unexpected" ]; then
    echo "Unexpected runtime path: $unexpected" >&2
    exit 1
fi
status=0
grep -RilE "$2" "$3" || status=$?
test "$status" -eq 1
"""


def verify_configuration(service, configuration):
    for value in configuration.get("Env", []):
        name = value.split("=", 1)[0]
        if FORBIDDEN_ENV.search(name):
            raise RuntimeError(f"{service}: unexpected environment key {name}")
    for field in ("Entrypoint", "Cmd"):
        arguments = " ".join(configuration.get(field) or [])
        if re.search(r"codex|cua_repl|playwright|puppeteer|selenium", arguments, re.IGNORECASE):
            raise RuntimeError(f"{service}: unexpected {field}")


def run():
    for service in ("web", "api", "worker", "migrate"):
        container_id = docker("compose", "ps", "-aq", service)
        if not container_id:
            raise RuntimeError(f"{service}: container missing")
        container, = json.loads(docker("inspect", container_id))
        verify_configuration(service, container["Config"])
        for mount in container["Mounts"]:
            if mount["Type"] == "bind" and mount["Destination"] != "/run/secrets/staging_db_password":
                raise RuntimeError(f"{service}: unexpected host mount at {mount['Destination']}")
        networks = container["NetworkSettings"]["Networks"]
        if len(networks) != 1:
            raise RuntimeError(f"{service}: expected one isolated runtime network")
        network, = json.loads(docker("network", "inspect", next(iter(networks))))
        if not network["Internal"]:
            raise RuntimeError(f"{service}: runtime network has external routing")
        if service != "migrate":
            dependencies, application = ("/app/.next", "/app/.next") if service == "web" else (
                "/opt/venv", "/app/backend/app",
            )
            docker("compose", "exec", "-T", service, "sh", "-ec", RUNTIME_SCAN,
                   "verify-image", dependencies, FORBIDDEN_MARKERS, application)
    logs = docker("compose", "logs", "--no-color", "web", "api", "worker", "migrate")
    if LOG_MARKERS.search(logs):
        raise RuntimeError("Unexpected Computer Use marker in application logs")
    print("Runtime artifacts, service configuration, host mounts, isolated network and logs passed.")


if __name__ == "__main__":
    run()
