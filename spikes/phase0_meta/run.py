from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from meta_oauth_spike.config import Config, load_env  # noqa: E402
from meta_oauth_spike.flow import OAuthFlow, check_tokens  # noqa: E402
from meta_oauth_spike.graph import GraphClient  # noqa: E402
from meta_oauth_spike.server import serve  # noqa: E402
from meta_oauth_spike.state import StateManager  # noqa: E402


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd not in ("serve", "check", "studio"):
        print("usage: run.py serve|check|studio [uvicorn options]")
        return 2
    cfg = Config.from_env_file(HERE.parent.parent / ".env")
    if cmd == "studio":
        root = HERE.parent.parent
        page_id = os.environ.get("META_TEST_PAGE_ID") or load_env(root / ".env").get("META_TEST_PAGE_ID")
        if not page_id:
            raise SystemExit("Configure META_TEST_PAGE_ID first")
        encrypted = (HERE / ".secrets" / "meta_tokens.enc").read_bytes()
        saved = json.loads(Fernet(cfg.encryption_key.encode()).decrypt(encrypted))
        page = saved["pages"].get(page_id)
        if not page or not page.get("page_token"):
            raise SystemExit("Run Meta OAuth for the configured Page first")
        python = root / "backend" / ".venv" / "bin" / "python"
        env = {**os.environ, "META_TEST_PAGE_ID": page_id, "META_PAGE_ACCESS_TOKEN": page["page_token"]}
        os.chdir(root)
        os.execve(python, [str(python), "-m", "uvicorn", "--app-dir", "backend", "app.main:app",
                          "--host", "127.0.0.1", "--port", "8001", *sys.argv[2:]], env)
    if cmd == "check":
        print(json.dumps(check_tokens(cfg, HERE), indent=2, ensure_ascii=False))
        return 0
    flow = OAuthFlow(cfg, GraphClient(cfg.version, cfg.app_secret), StateManager(cfg.state_secret), HERE)
    serve(flow)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
