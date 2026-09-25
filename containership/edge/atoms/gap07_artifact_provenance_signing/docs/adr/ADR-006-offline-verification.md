# ADR-006: Offline verification model
Status: accepted
Decision: sites verify entirely locally using (a) a signed trust generation with `max_staleness_s` and distribution `expires`, (b) signed time attestations with a persisted floor and offline budget, (c) cached checkpoints with max age. Past any budget, admission becomes `defer`/`deny`. It never becomes allow.
