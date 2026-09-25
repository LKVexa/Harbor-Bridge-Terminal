# GAP-15 Threat Model (per component)

Method: STRIDE-style per component. For each: assets, trust boundary, attacker capability/abuse case, the failure it would cause, the fail-open/fail-closed decision, and the implemented mitigation. Status: **authored by the build, not independently reviewed** (MC-xx-13 rows are ARTIFACT_PRESENT_UNREVIEWED).

Attacker capabilities assumed: network attacker on any API; malicious or compromised producer; compromised single node; insider with one operator role; attacker who can read (not write) off-box exports. Out of scope: compromise of the HSM/KMS itself and of two independent approvers at once.

| # | Component | Assets | Trust boundary | Abuse case | Failure if unmitigated | Fail decision | Mitigation |
|---|---|---|---|---|---|---|---|
| 01 | Durable store | matrix rows, revision | process ↔ SQLite file | local writer racing, disk tamper | lost update; partial commit | fail closed on CAS conflict / chain break | BEGIN IMMEDIATE + CAS; triggers; recovery replay |
| 02 | Evidence ledger | accepted evidence history | DB ↔ operator | history rewrite, reorder, truncation | verdict can't be reconstructed | refuse to open on chain break | hash chain, signed off-box checkpoints |
| 03 | Signing | signer keys, signatures | producer ↔ service | forgery, algorithm substitution, key-id confusion, malleability | forged evidence accepted | reject unknown/weak/expired/revoked | Ed25519 strict S, domain separation, scoped keys |
| 04 | Provenance | artifact digest, builder identity | GAP-07 ↔ service | tag swap, subject confusion, forged statement | untested bytes certified | reject mismatch/missing SBOM | digest identity, signed statement, SBOM subject match, tag re-confirm |
| 05 | Attestation | node identity, measurements | node ↔ service | quote replay, cloned identity, firmware downgrade | wrong profile certified | reject stale/nonce/baseline/firmware | service nonce, freshness, baseline, min firmware, derived profile |
| 06 | Trusted time | wall clock, TTL decisions | time sources ↔ service | clock rollback to revive expired certs | expired cert treated as current | refuse decisions below confidence | multi-source skew check, monotonic jump detection |
| 07 | Authentication | tokens, IdP keys | caller ↔ API | token replay, forged claims, header spoofing | impersonation | reject; throttle; stale revocations fail closed | signed short-lived tokens, jti, cnf binding, audience/issuer |
| 08 | Authorization | privileged actions | principal ↔ action | privilege escalation, site escape | unauthorised lifecycle/revocation change | default deny, deny overrides | ABAC + token partition scope + SoD |
| 09 | Schemas | wire contracts | client ↔ parser | type confusion, unknown fields, duplicates | ambiguous interpretation | reject with stable codes | closed schemas, canonical JSON, semantic checks |
| 10 | Ingestion | ledger integrity | producer ↔ service | replay storm, zip bomb, conflicting resubmission | bad evidence committed | all-or-nothing batches; conflict quarantine | auth before parse, size limits, idempotency keys |
| 11 | Concurrency | revision monotonicity | writer ↔ writer | ABA, stale writer | lost update | explicit conflict result | monotonic revision CAS, single-writer txn |
| 12 | Audit stream | security history | operator ↔ audit | log deletion, tamper | undetected abuse | append-only; chain verify at open | separate chained table, triggers, checkpoints |
| 13 | Revocation | deny state | responder ↔ caches | stale cache bypass, accidental fleet revocation | revoked artifact deployed | revocation outranks every allow | precedence in certify, bulk preview + blast-radius guard |
| 14 | Service host | availability | network ↔ server | slowloris, huge bodies, version confusion | outage / coercion | bounded, reject unknown majors | length-required, limits, deadlines, readiness |
| 15 | Recovery/DR | state continuity | backup ↔ restore | restore of forged/corrupt/foreign backup | silent state loss | restore to staging only after verification | signed manifest, hash, partition check, verdict re-derivation |
| 16 | Negotiation | fit decisions | manifest ↔ engine | combinatorial blowup, shim inference | false compatibility | bounded cardinality; fit ≠ certification | deterministic transcript, explicit adapters |
| 17 | Capability model | profile identity | advertiser ↔ model | claimed capabilities minting new profiles | policy bypass by aliasing | UNKNOWN never wildcard | provenance strength, closed registries, alias table |
| 18 | Version policy | range semantics | rule author ↔ engine | implicit widening via ^/~/* | untested versions admitted | refuse unbounded ranges | explicit upper bounds, exclusions |
| 19 | Feature subsets | feature scope | caller ↔ decision | child pass implying parent | whole-runtime claim from partial evidence | subset scope explicit | prerequisite closure, required-set digest |
| 20 | Lifecycle | EOL state | operator ↔ lifecycle | silent reactivation | EOL runtime in service | illegal transitions refused | transition graph, waiver + SoD reactivation |
| 21 | Negative ageing | negative evidence | time ↔ verdict | waiting out a failure | incompatible becomes deployable | aged negative → retest-required (never allow) | failure classes with TTL |
| 22 | Recert scheduler | test capacity | scheduler ↔ labs | storm, stale lease | lab overload / double work | fenced leases, quotas | idempotent job keys, fencing tokens |
| 23 | Policy precedence | decision rules | policy author ↔ engine | lower domain overriding revocation | unsafe allow | deny from higher rank wins; non-waivable | ranked domains, validation, simulation |
| 24 | Offline cache | edge decisions | control plane ↔ edge | bundle rollback, copy to other site | stale/foreign allow | absence/expiry never allows | signed scoped bundles, counter, hard expiry |
| 25 | Partitions | tenant/site isolation | site ↔ site | cross-partition reuse | foreign evidence certifies | partition in every key | canonical ids, partition-leading indexes |
| 26 | Metrics | telemetry | exporter ↔ scraper | cardinality bomb, topology leak | monitoring outage / leak | reject undeclared labels | closed label sets, auth on /metrics |
| 27 | Logs/traces | diagnostics | service ↔ log sink | log injection, secret leakage | forged log lines, credential exposure | escape + redact | structured JSON, redaction, hashing |
| 28 | Explain | decision rationale | operator ↔ explain | cross-site data peek, re-evaluation drift | information leak / wrong story | authz per partition; default historical | same trace as decision, replay check |
| 29 | Alerting | detection | alertmanager ↔ ops | indefinite silence | attack unnoticed | paging silences ≤4h | watchdog, owner+expiry on silences |
| 30 | Admission | deploy gate | scheduler ↔ service | tag substitution, TOCTOU, retry divergence | unsupported deploy | digest-only, pre-start recheck | idempotent request ids, revision binding |
| 31 | Conflicts | evidence truth | producer ↔ producer | disagreement exploited | ambiguous allow | quarantine until two-person resolution | case objects, append-only resolution |
| 32 | Capacity | resources | clients ↔ service | flooding, hot keys | denial of service | shed load, keep priority paths | token buckets, bounded queues, fair share |
| 33 | Integration tests | cross-layer contract | GAP-02/07/08 ↔ GAP-15 | contract drift | silent incompatibility | gate blocks without evidence | pinned integration envs (blocked) |
| 34 | Test fixtures | certification inputs | lab ↔ ledger | fixture drift | misattributed failures | immutable signed fixtures | harness digest in every result |
| 35 | Fuzzing | parsers | attacker ↔ parser | malformed input | crash / fail-open | every non-domain exception is a finding | seeded mutation fuzz |
| 36 | Adversarial suite | all trust boundaries | red team ↔ service | replay/spoof/escalation | compromise | documented remediation before GO | adversarial tests across modules |
| 37 | Race suite | consistency | threads/processes | interleavings | lost updates, torn txns | deterministic barriers | barrier + multi-process tests |
| 38 | Fault injection | durability | faults ↔ service | crash at stage N | partial state | readiness false until consistent | fault hooks at every stage |
| 39 | Performance | capacity model | load ↔ service | unmeasured limits | overload in production | published envelope | bench harness |
| 40 | Release bundle | release evidence | CI ↔ deploy | evidence substitution | unverified release shipped | signature + build digest check | signed bundle |
| 41 | RTM | traceability | requirements ↔ evidence | orphan/stale rows | false completeness | gate on unresolved rows | generated RTM with problems report |
| 42 | ADRs | design intent | architects ↔ code | silent drift | unsafe assumption | review on change | ADR table linked to modules |
| 43 | Ownership | accountability | org ↔ service | no owner | unhandled incident | owner validation fails on placeholders | OWNERS.json validation |
| 44 | Bootstrap | deployment safety | operator ↔ host | insecure defaults, inline secrets | exposed secrets | refuse bad config | config schema, preflight |
| 45 | Supply chain | package integrity | build ↔ consumer | tampered package | malicious code | verify manifest/provenance | SBOM, provenance, signed manifest |
| 46 | Rollout | change safety | release ↔ fleet | bad release spread | fleet-wide wrong verdicts | auto halt/rollback | staged controller, emergency disable |
| 47 | Backup tooling | recoverability | operator ↔ backups | unverifiable backups | unrecoverable loss | restore-verify | signed manifests, staging restore |
| 48 | Runbooks | operator response | ops ↔ docs | stale instructions | wrong action in incident | link check in release | anchored runbooks |
| 49 | Waivers | exceptions | requester ↔ approver | over-broad or eternal waivers | policy bypass | exact scope, max duration, SoD | waiver registry |
| 50 | Exit gate | release decision | pipeline ↔ gate | manual 'pass', evidence reuse | unready release promoted | NO_GO by default | signed inputs, build binding, self-review refusal |
| 51 | MASTER.md | source integrity | author ↔ package | regenerated file passed off as original | false provenance | report absence | release check: README claims vs manifest |

<a id="tm-01"></a>

<a id="tm-02"></a>

<a id="tm-03"></a>

<a id="tm-04"></a>

<a id="tm-05"></a>

<a id="tm-06"></a>

<a id="tm-07"></a>

<a id="tm-08"></a>

<a id="tm-09"></a>

<a id="tm-10"></a>

<a id="tm-11"></a>

<a id="tm-12"></a>

<a id="tm-13"></a>

<a id="tm-14"></a>

<a id="tm-15"></a>

<a id="tm-16"></a>

<a id="tm-17"></a>

<a id="tm-18"></a>

<a id="tm-19"></a>

<a id="tm-20"></a>

<a id="tm-21"></a>

<a id="tm-22"></a>

<a id="tm-23"></a>

<a id="tm-24"></a>

<a id="tm-25"></a>

<a id="tm-26"></a>

<a id="tm-27"></a>

<a id="tm-28"></a>

<a id="tm-29"></a>

<a id="tm-30"></a>

<a id="tm-31"></a>

<a id="tm-32"></a>

<a id="tm-33"></a>

<a id="tm-34"></a>

<a id="tm-35"></a>

<a id="tm-36"></a>

<a id="tm-37"></a>

<a id="tm-38"></a>

<a id="tm-39"></a>

<a id="tm-40"></a>

<a id="tm-41"></a>

<a id="tm-42"></a>

<a id="tm-43"></a>

<a id="tm-44"></a>

<a id="tm-45"></a>

<a id="tm-46"></a>

<a id="tm-47"></a>

<a id="tm-48"></a>

<a id="tm-49"></a>

<a id="tm-50"></a>

<a id="tm-51"></a>
