# Phase 0 spike — publish state machine + reconcile (mock only)

Standalone proof of concept. Not the future backend. No network, no credentials, no Meta call is made.

- `publish_spike/domain.py` — pure logic: statuses, transition table, idempotency key, marker, reconcile decisions.
- `publish_spike/ports.py` — `MetaReelsPort` Protocol and error types (`AmbiguousOutcome`, `DefiniteFailure`).
- `publish_spike/fake_meta.py` — `FakeMetaReels`: scriptable per phase (`OK`, `FAIL`, `TIMEOUT_NO_EFFECT`, `TIMEOUT_APPLIED`), keeps remote state.
- `publish_spike/service.py` — orchestration with an in-memory job store.
- `tests/test_publish.py` — scenarios from the Phase 0 brief.

Run from the repo root (ephemeral, no install):

```bash
uv run --with pytest pytest spikes/phase0_publish -q
```

Findings that affect the design (see ADR-0003):
- The reel `description` (and so the idempotency marker) is only sent at the `finish` call. A start-phase orphan session carries no marker and is not a published reel, so list-by-marker cannot see it; it is also harmless. Marker adoption therefore covers lost-state cases (state not persisted after a reel was finished), not start-phase orphans.
- The fake models Meta behavior from documentation; it proves our logic, not Meta's actual behavior.
