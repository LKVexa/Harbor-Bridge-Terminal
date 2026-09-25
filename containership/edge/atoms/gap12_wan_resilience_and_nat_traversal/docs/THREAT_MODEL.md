# GAP-12 component threat models (group D)

Created by this build for each group-D component. **Not independently reviewed**: a security review is an owner-assigned human activity and none has happened.

## G12-D043

- **Assets:** peer identity binding, trust cache
- **Trust boundaries:** network <-> GAP-12; GAP-12 <-> GAP-06 verifier
- **Attacker capabilities:** on-path attacker, peer impersonator, stale-trust replayer
- **Abuse paths (spoofing/replay/amplification/exhaustion):** spoofed peer on a reachable path; replayed old attestation; trust surviving revocation
- **Mitigations in code:** TrustGate: verifier required (fail closed), peer-bound attestation, expiry + max_age, revocation list; controller refuses untrusted successes

## G12-D044

- **Assets:** session plaintext, integrity
- **Trust boundaries:** peer <-> relay <-> peer
- **Attacker capabilities:** malicious relay, on-path attacker
- **Abuse paths (spoofing/replay/amplification/exhaustion):** relay reads/alters/strips frames; downgrade to plaintext on relay switch
- **Mitigations in code:** AES-256-GCM, HKDF keys bound to both identities/role/protocol/epoch, directional keys, no plaintext fallback (channel refuses to build)

## G12-D045

- **Assets:** session keys
- **Trust boundaries:** key source <-> node
- **Attacker capabilities:** attacker holding an old key
- **Abuse paths (spoofing/replay/amplification/exhaustion):** use of a compromised epoch key
- **Mitigations in code:** epoch rotation, old-epoch frames rejected; revocation/distribution service is external (not evidenced)

## G12-D046

- **Assets:** message freshness
- **Trust boundaries:** network
- **Attacker capabilities:** replayer
- **Abuse paths (spoofing/replay/amplification/exhaustion):** duplicate, delayed, cross-session, post-restart replay
- **Mitigations in code:** 64..65536-bit sliding window per epoch, AEAD AAD binds session; restart resumes at a new epoch

## G12-D047

- **Assets:** TURN credentials
- **Trust boundaries:** node <-> TURN server
- **Attacker capabilities:** credential thief
- **Abuse paths (spoofing/replay/amplification/exhaustion):** use of leaked or long-lived credentials
- **Mitigations in code:** time-limited HMAC credentials, overlap rotation, retire, per-user revocation

## G12-D048

- **Assets:** relay capacity, tenant isolation
- **Trust boundaries:** tenant <-> shared relay
- **Attacker capabilities:** other tenant, free-rider
- **Abuse paths (spoofing/replay/amplification/exhaustion):** using another tenant's relay or relaying to unapproved peers
- **Mitigations in code:** RelayAuthorizer tenancy map + peer allow list; TURN permissions; server quota

## G12-D049

- **Assets:** CPU/memory/sockets
- **Trust boundaries:** untrusted sources
- **Attacker capabilities:** flooder, key-space exhaustion attacker
- **Abuse paths (spoofing/replay/amplification/exhaustion):** attempt floods, unbounded limiter state
- **Mitigations in code:** hierarchical token buckets, LRU-bounded keys with shared overflow bucket

## G12-D050

- **Assets:** fleet stability
- **Trust boundaries:** fleet <-> dependencies
- **Attacker capabilities:** outage-induced retry storm
- **Abuse paths (spoofing/replay/amplification/exhaustion):** nested retries multiplying load
- **Mitigations in code:** closed/open/half-open breaker, bounded half-open admission, one shared retry budget

## G12-D051

- **Assets:** egress
- **Trust boundaries:** node -> internet
- **Attacker capabilities:** attacker steering connections (SSRF-like), misconfiguration
- **Abuse paths (spoofing/replay/amplification/exhaustion):** connecting to unapproved destinations via fallback
- **Mitigations in code:** deny-by-default CIDR/port/peer policy, deny precedence, checked before every adapter

## G12-D052

- **Assets:** secret material
- **Trust boundaries:** config/logs/crash dumps
- **Attacker capabilities:** log reader, config leaker
- **Abuse paths (spoofing/replay/amplification/exhaustion):** secret in config, repr, exception, pickle
- **Mitigations in code:** secret:// references only, least-privilege grants, Secret repr/pickle refusal, 0600 file check

## G12-D053

- **Assets:** endpoint privacy
- **Trust boundaries:** telemetry sinks
- **Attacker capabilities:** telemetry reader
- **Abuse paths (spoofing/replay/amplification/exhaustion):** IP/port/credential disclosure in logs/traces
- **Mitigations in code:** redact(): pseudonymous endpoint tokens, secret patterns removed; metrics refuse IP labels

## G12-D054

- **Assets:** relay budget, credentials
- **Trust boundaries:** untrusted sources
- **Attacker capabilities:** forced-relay attacker, scanner, brute forcer
- **Abuse paths (spoofing/replay/amplification/exhaustion):** cost abuse, reconnaissance, credential guessing
- **Mitigations in code:** windowed detectors per source for forced relay, scanning, auth-failure bursts

## G12-D055

- **Assets:** audit trail
- **Trust boundaries:** audit storage
- **Attacker capabilities:** insider editing history
- **Abuse paths (spoofing/replay/amplification/exhaustion):** silent edit or deletion of security events
- **Mitigations in code:** SHA-256 hash chain with sequence numbers; verify() locates first break; head anchoring is external
