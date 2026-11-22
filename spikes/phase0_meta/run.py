from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from meta_oauth_spike.config import Config  # noqa: E402
from meta_oauth_spike.flow import OAuthFlow, check_tokens  # noqa: E402
from meta_oauth_spike.graph import GraphClient  # noqa: E402
from meta_oauth_spike.server import serve  # noqa: E402
from meta_oauth_spike.state import StateManager  # noqa: E402


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd not in ("serve", "check"):
        print("usage: run.py serve|check")
        return 2
    cfg = Config.from_env_file(HERE.parent.parent / ".env")
    if cmd == "check":
        print(json.dumps(check_tokens(cfg, HERE), indent=2, ensure_ascii=False))
        return 0
    flow = OAuthFlow(cfg, GraphClient(cfg.version, cfg.app_secret), StateManager(cfg.state_secret), HERE)
    serve(flow)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
