# Version/feature negotiation (INV-38-C027)

`negotiation.py` (+ `compatibility/version-policy.yaml`) negotiates a common
schema version before data-plane activation and negotiates optional features
separately. Mixed-version behaviour is defined for N/N, N/N-1, N/N+1 and
unsupported peers; unknown required fields are rejected, and a peer cannot force a
version below the minimum-security version (downgrade protection). Bidirectional
tests in `tests/test_negotiation.py`. **Status:** `IN_PROGRESS` — real-backend
adapter transcripts needed for the full matrix.
