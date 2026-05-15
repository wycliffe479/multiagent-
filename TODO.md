# TODO — Make Group A infallible

- [x] Inspect Group A agent/state code paths (already done analytically).
- [x] Update Agent 1 to never crash on LLM failures (rate-limit/network/auth) and use deterministic regex fallback.
- [ ] Update Agent 2 to enforce allow-list actions + remove brittle fallback parsing (split()[0]) and deterministic behavior on unknown inputs.
- [ ] Update Group A workflow/graph to short-circuit Agent 2 when Agent 1 parsing fails validation.

# TODO — Fix Full Pipeline (A → B) loader collisions

- [ ] Patch `integration/combined_workflow.py` to eliminate `src` package collisions by isolating imports per-group.
- [ ] Patch `web_ui/main.py` loader similarly so `/run` is consistent.
- [ ] Re-run `integration/combined_workflow.py` and `/run` smoke tests and ensure Decision/Slack fields are populated.

