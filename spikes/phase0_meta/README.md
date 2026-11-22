# Phase 0 spike — Meta OAuth → list Pages (live capable)

Standalone, stdlib + `cryptography`. Reads `../../.env` (never printed). Tokens are Fernet-encrypted in `.secrets/` (gitignored); sanitized evidence goes to `evidence/` (gitignored).

```bash
uv run --with pytest --with cryptography pytest spikes/phase0_meta -q   # fakes only, no network
uv run --with cryptography python spikes/phase0_meta/run.py serve       # then open http://localhost:8000/
uv run --with cryptography python spikes/phase0_meta/run.py check       # decrypt + print ids/names/tasks/scopes only
```

The server binds 127.0.0.1:8000; the callback path comes from `META_OAUTH_REDIRECT_URI`. Set optional `META_LOGIN_CONFIG_ID` for Facebook Login for Business (sent as `config_id` instead of `scope`).
Graph calls carry `appsecret_proof`. Errors are redacted. Request logging of the HTTP server is disabled (URLs contain code/state).

For Facebook Login for Business, create a **User access token** configuration in the Meta dashboard and set `META_LOGIN_CONFIG_ID`. Select only the test Page in the consent dialog. Meta automatically allows `http://localhost` redirects in Development Mode.

If the OAuth callback reports a network error on macOS because Python cannot find a trusted CA bundle, set `SSL_CERT_FILE=/etc/ssl/cert.pem` when starting the server.
