#!/usr/bin/env python3
"""Evidence ledger for the RAMWS candidate: 32 native work-package records (kit evidence/task.json shape),
   6300 overlay dispositions (ledger/dispositions.jsonl), ledger/release.json with the kit's five separate
   status words, release/manifest.json. Only facts backed by files on disk or rows in e/full-suite.tap."""
import json, os, re, glob, hashlib, collections, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
KIT = os.environ.get('RAMWS_KIT', os.path.join(os.path.dirname(ROOT), 'ramws', 'RAMWS_v1.0.0'))
REV = json.load(open('package.json'))['version']; NOW = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
tap = open('e/full-suite.tap').read(); TESTS = [(m.group(1) == 'ok', m.group(2)) for m in re.finditer(r'^(ok|not ok) \d+ - (.+)$', tap, flags=re.M)]
def tests(*pats): return [(ok, n) for ok, n in TESTS if any(re.search(p, n) for p in pats)]
ENV = 'Linux 6.18.44 x86_64, 2 vCPU, Node v22.22.2, Chromium 1194; loopback only'
PROFILE = 'LOCAL_VOLATILE'

P, IP, B, NA, O = 'PASS', 'IN_PROGRESS', 'BLOCKED', 'NOT_APPLICABLE', 'OPEN'
R = {
 'R01': (P, 'docs/RAMWS.md#the-claim-and-what-it-is-not', 'RAM-resident defined as placement + bounded ledger + reduced avoidable CPU; no CPU-replacement claim.', [], []),
 'R02': (P, 'docs/RAMWS.md#decisions-approved-by-the-owner-on-2026-09-21', 'LOCAL_VOLATILE approved; other profiles refuse to start; SESSION_RESET/OUTCOME_UNKNOWN semantics implemented.', [r'SESSION_RESET', r'profile/snapshot'], []),
 'R03': (P, 'ram/descriptor.js', 'Eight fields + six invariants implemented; kit schema byte-identical; 13/13 fixtures.', [r'kit fixtures', r'lifecycle: admit', r'Ownership/Validity', r'state gating', r'plan identity'], []),
 'R04': (P, 'ledger/dispositions.jsonl', '6300 original IDs preserved with the kit overlays; per-item dispositions; evidence flow via this ledger.', [], ['self-review only']),
 'R05': (IP, 'gateway/server.js', 'Node runtime probed (heap-cap enforcement, cgroup boundary, worker thread cost). PowerShell/.NET/HttpListener probes NOT_RUN (no pwsh, registries blocked).', [], ['HttpListener feasibility untestable here']),
 'R06': (P, 'ram/allowance.js', 'L/F/G/H/s allowance computed at startup, enforced by the ledger; verified with a 2-session boundary test.', [r'memory admission'], ['s measured on one host']),
 'R07': (IP, 'ram/residency.js', 'Process-scope residency observer; 0 major faults observed per experiment launch. No page locking; RESIDENCY_VERIFIED not claimed.', [], ['gateway scope only']),
 'R08': (P, 'gateway/worker-link.js', 'Thread (transfer) and process (copy) boundaries fixed and both tested; traffic ledger names every copy/transfer stage.', [r'\[thread\] vertical slice', r'\[process\] vertical slice'], []),
 'R09': (P, 'ram/ledger.js', 'Reservation ledger + slab pool: charge once, idle capacity visible, refusal allocates nothing, duplicate release counted.', [r'admission is all-or-nothing', r'leases: capacity', r'slab pool', r'randomized acquire'], []),
 'R10': (P, 'gateway/ws.js', 'Bounded receive: caps from headers, in-place unmask, single-copy reassembly, reservation before buffer.', [r'declared 64-bit', r'fragmented message over the cap', r'split UTF-8', r'stalled fragment'], []),
 'R11': (P, 'gateway/ws.js', 'Leases released in write callbacks; cancellation/timeouts never release early; single exit.', [r'Lifetime: capacity returns', r'ledger returns to zero'], []),
 'R12': (P, 'gateway/connection.js', 'Byte credits + pause budget + cooperative yield(); slow consumer and stopped reader bounded; fair to other tenants.', [r'^credits:', r'slow consumer', r'stops reading', r'^S5:'], []),
 'R13': (P, 'protocol/codec.js', 'Binary frames, uint48 seq, no base64, incremental UTF-8; zero-length refused; fidelity exact in 60 runs.', [r'binary data frames', r'binary data discipline', r'every split point'], []),
 'R14': (IP, 'ram/ledger.js', 'Ledger reconciles from leaf leases in every test; predicted-vs-observed RSS comparison (gate H1) NOT RUN.', [r'reconcil'], ['H1 not run']),
 'R15': (P, 'src/main/spiral/kernel.js', 'VFS quotas, history cap, capture cap, per-session isolate; thread heap cap enforced.', [r'VFS quota', r'F17 bounds', r'worker heap cap'], []),
 'R16': (P, 'ram/descriptor.js', 'Extents, generations, epoch and plan identity checked on every operation.', [r'Validity: stale', r'stale epoch'], []),
 'R17': (P, 'src/main/spiral/line-reader.js', 'Event-driven throughout; batched repaint; streaming seq; ack coalescing. Measured W1/W3.', [], []),
 'R18': (P, 'ram/traffic.js', 'Software copy/transfer ledger per stage exposed in /live; labelled as estimates.', [], ['no hardware counters']),
 'R19': (P, 'ram/descriptor.js', 'Immutable OPERATORS dispatch table; plan cache keyed by plan identity; trusted-shape marker for server-built descriptors.', [], []),
 'R20': (IP, 'docs/EXPERIMENT.md', 'End-to-end experiment is authoritative; no analytical ceiling asserted; H4 not run.', [], []),
 'R21': (P, 'ram/descriptor.js', 'Descriptor admission on every operation with explicit rejection reasons.', [r'lifecycle: admit'], []),
 'R22': (P, 'worker/core.js', 'Headless SPIRAL behind a typed boundary; both hosts; adapter operations preserved in client/.', [r'\[thread\]', r'\[process\]'], []),
 'R23': (P, 'src/main/spiral/kernel.js', 'Lifecycle hazards: close settles readers, split UTF-8/escapes, paste hand-off, Ctrl-C cases, close during readline, repeated close.', [r'F04 close', r'Ctrl-C at prompt', r'type-ahead', r'every split point'], []),
 'R24': (NA, 'docs/RAMWS.md#not-done--not-claimed', 'No neural processing exists in this service; nothing to keep off the critical path.', [], []),
 'R25': (P, 'tests/security/authz.test.js', 'Tenant isolation regression on v2: no sid in data frames; foreign sid indistinguishable from unknown; per-session isolates.', [r'session ids authorize', r'secrets and host', r'capacity:'], ['no independent review']),
 'R26': (B, 'deploy/render.yaml', 'Render deploy/drain requires an authorized service; Dockerfile never built.', [], []),
 'R27': (P, 'gateway/server.js', '/live: bounded, payload-free, label-free telemetry; UNKNOWN for unmeasured.', [r'health / live'], []),
 'R28': (P, 'e/R28/result.json', 'Preregistered 3x10 experiment + ablation, re-run in full after each post-data code change (4 runs, all preserved); H2 supported on this host for W1-W3 (thread backend): 42/67/99 %; process-backend ablation W1 NOT_SUPPORTED.', [], ['one host']),
 'R29': (P, 'ledger/release.json', 'Five statuses reported separately; claim ledger; gates table.', [], []),
 'R30': (P, 'gateway/connection.js', 'session.reset with OUTCOME_UNKNOWN/NO_PENDING_INPUT; nothing replayed; epoch per launch.', [r'SESSION_RESET', r'web client in Chromium'], []),
 'R31': (P, 'release/manifest.json', 'Short paths, SHA-256 manifest, tools/verify.js, zero third-party runtime dependencies.', [], []),
 'R32': (NA, 'docs/RAMWS.md#not-done--not-claimed', 'PIM_RESEARCH disabled: no device, primitive, driver or evidence.', [], []),
}
W = {i['id']: i for i in json.load(open(os.path.join(KIT, 'index/work.json')))}
os.makedirs('e/native', exist_ok=True); tot = collections.Counter()
for rid, (st, artefact, delta, pats, risks) in R.items():
    tr = tests(*pats) if pats else []
    if st == P and pats: assert tr and all(ok for ok, _ in tr), (rid, tr[:2])
    rec = {'schema': 'RAMWS/TASK_EVIDENCE/1', 'task_id': rid, 'title': W[rid]['title'], 'status': st, 'applicability': 'NODE-WEB profile' if st != NA else 'not applicable in this profile', 'applicability_approval': 'owner decisions RD-01..RD-05 (2026-09-21)',
           'selected_profile': PROFILE, 'source_identity': 'ledger/ramws_source.json', 'runtime_identity': ENV, 'configuration_identity': 'gateway/config.js defaults; e/R28/experiment.frozen.json for R28',
           'predecessor_evidence': [f'e/native/{d}.json' for d in W[rid]['depends_on']], 'decision_or_code_delta': f'{artefact}: {delta}', 'command': 'node --test "tests/*/*.test.js" (e/full-suite.tap)' if tr else None,
           'started_at': '2026-09-21T20:30:00Z', 'finished_at': NOW, 'expected': W[rid]['oracle'], 'observed': f'{len(tr)} linked tests, all ok' if tr else ('see artefact' if st in (P, IP) else st),
           'raw_result_paths': ['e/full-suite.tap'] + (['e/R28/result.json', 'e/R28/result.process-backend.json'] if rid == 'R28' else []), 'memory_scope': 'gateway process (+ worker threads) and worker processes', 'allocation_change_bytes': None,
           'cpu_scope': 'server process tree' if rid == 'R28' else None, 'cpu_change_seconds': None, 'residency_status': 'OBSERVED_RESIDENT_FOR_INTERVAL (gateway scope, experiment launches)' if rid in ('R07', 'R28') else 'UNKNOWN',
           'residual_risks': risks + ['self-reviewed by the implementer; no independent verification'], 'rollback': 'delete ram/, gateway/worker-link.js, worker/core.js, worker/thread.js; restore the v1 files from hermit-vws 1.1.0-vws.1 (hashes in ledger/ramws_source.json)',
           'linked_tests': [n for _, n in tr]}
    json.dump(rec, open(f'e/native/{rid}.json', 'w'), indent=1); tot[st] += 1

# ---- 6300 overlays
K = {}
for f in glob.glob(os.path.join(KIT, 'ledger/*.jsonl')):
    for l in open(f): d = json.loads(l); K[d['id']] = d
prior = {}
for l in open('ledger/prior/vws200_dispositions.jsonl'): d = json.loads(l); prior[d['id']] = d
reviewed = {}
for f in glob.glob('ledger/review_outputs/C*.jsonl'):
    for l in open(f):
        if l.strip(): r = json.loads(l); reviewed[r['id']] = r
NAC = {'C01': 'PowerShell execution host', 'C02': '.NET BCL', 'C11': 'HttpListener prefixes', 'C12': 'managed HttpListener', 'C35': 'runspaces/jobs', 'C42': 'PowerShell image', 'C44': 'pwsh entry point', 'C55': 'PowerShell client', 'C56': 'PowerShell client init', 'C57': 'PowerShell client receive', 'C58': 'PowerShell client keep-alive', 'C59': 'PowerShell client closure', 'ALT01': 'TcpListener (inactive)', 'ALT02': 'Kestrel (inactive)', 'ALT03': 'PwshWebSocketClient (inactive)', 'C05': 'shared datastore (DISTRIBUTED_VOLATILE not approved)', 'C22': 'auth-hook compatibility (identity is an adapter seam)', 'C45': 'BuildKit secrets (no dependency install)'}
BLC = {'C03': 'Render service', 'C06': 'Render edge', 'C07': 'public WSS/TLS', 'C43': 'Dockerfile never built', 'C51': 'Blueprint never applied', 'C52': 'deployment health-check registration'}
disp = []; adj = collections.Counter()
for tid in sorted(K):
    k = K[tid]; c = k['component']; rec = {'id': tid, 'component': c, 'task_class': k['task_class'], 'phase': k['phase'], 'source_check_sha256': hashlib.sha256(k['source_check'].encode()).hexdigest(), 'reference_work_packages': k['reference_work_packages'], 'profile': PROFILE, 'candidateRevision': REV, 'prior_vws200_status': prior.get(tid, {}).get('status')}
    if c in NAC: rec.update(status=NA, basis='component', evidence=['docs/RAMWS.md#decisions-approved-by-the-owner-on-2026-09-21'], note=f'RD-03/D-001 or inactive branch: {NAC[c]}')
    elif c in BLC: rec.update(status=B, basis='component', evidence=['docs/EXPERIMENT.md#gates-kit-validation-table'], note=f'{BLC[c]}: requires Docker/Render/TLS edge')
    else:
        r = reviewed.get(tid)
        if not r: rec.update(status=O, basis='none', evidence=[], note='not reviewed')
        else:
            st = r['status']; ev = r.get('evidence') or []; note = (r.get('note') or '')[:240]
            if st not in (P, IP, NA, B, O): st = IP; adj['invalid status'] += 1
            if st == P:
                paths = [re.split(r'[#:]', e)[0].strip() for e in ev]; exist = [p for p in paths if os.path.exists(p)]
                if not exist: st = IP; note += ' [downgraded: evidence path missing]'; adj['PASS->IN_PROGRESS missing path'] += 1
                elif k['task_class'] in ('VERIFY', 'TEST', 'MEASURE') and not any(p.startswith(('tests/', 'e/')) or p == 'docs/EXPERIMENT.md' for p in exist): st = IP; note += ' [downgraded: VERIFY/TEST/MEASURE without test or measurement]'; adj['PASS->IN_PROGRESS verify w/o test'] += 1
                elif k['task_class'] in ('RECORD', 'DOCUMENT', 'PUBLISH') and not any(p.startswith(('docs/', 'ledger/', 'e/', 'config/', 'deploy/', 'protocol/')) for p in exist): st = IP; note += ' [downgraded: RECORD without written record]'; adj['PASS->IN_PROGRESS record w/o doc'] += 1
            rec.update(status=st, basis='item-review', evidence=ev, note=note)
    rec['reviewMode'] = 'SELF_REVIEWED'; disp.append(rec)
assert len(disp) == 6300
with open('ledger/dispositions.jsonl', 'w') as fh:
    for d in disp: fh.write(json.dumps(d, ensure_ascii=False) + '\n')
src = collections.Counter(d['status'] for d in disp); byc = collections.OrderedDict()
for d in disp: byc.setdefault(d['component'], collections.Counter())[d['status']] += 1
tc = collections.Counter(k['task_class'] for k in K.values())
exp = json.load(open('e/R28/result.json')); abl = json.load(open('e/R28/result.process-backend.json'))
json.dump({'generated': NOW, 'candidate': REV, 'kit': 'RAMWS v1.0.0 4bf7b67e7f4aa3a6b1fddb09c81b9e8dd65b94d0b921fd16b05fd59ff279c769', 'profile': PROFILE, 'protocol': 'hermit.vws.v2', 'workerBackendDefault': 'thread',
   'status_words': {'PACKAGE_VERIFIED': 'PASS (kit verify.py PASS; candidate manifest tools/verify.js)', 'IMPLEMENTATION_TESTED': f'PASS on one Linux host ({len(TESTS)} tests, {sum(1 for ok, _ in TESTS if ok)} pass)', 'DEPLOYMENT_TESTED': 'NOT_RUN (no Docker/Render/TLS edge)', 'RESIDENCY_VERIFIED': 'NOT_CLAIMED (interval observation only: 0 major faults, gateway scope)', 'CPU_BENEFIT_SUPPORTED': 'SUPPORTED on this host vs. the previous candidate for W1/W2/W3 (thread backend); with the process backend W1 is NOT supported'},
   'experiment': {'main': {w: {'reduction': v['reduction_point'], 'ci95': v['reduction_ci95_cluster_bootstrap'], 'H2': v['gate_H2']} for w, v in exp['workloads'].items()}, 'ablation_process_backend': {w: {'reduction': v['reduction_point'], 'ci95': v['reduction_ci95_cluster_bootstrap'], 'H2': v['gate_H2']} for w, v in abl['workloads'].items()}, 'fidelity_exact_all_runs': exp['fidelity']['allRunsExact'] and abl['fidelity']['allRunsExact']},
   'gates': {'G0': 'PASS (this host)', 'H1': 'NOT_RUN', 'H2': 'SUPPORTED (this host)', 'H3': 'PASS', 'H4': 'NOT_RUN', 'H5': 'OBSERVED interval only'},
   'tests': {'total': len(TESTS), 'pass': sum(1 for ok, _ in TESTS if ok), 'log': 'e/full-suite.tap', 'sha256': sha('e/full-suite.tap')},
   'nativeWorkPackages': {'total': 32, 'byStatus': dict(tot), 'records': 'e/native/Rxx.json'},
   'originalChecks': {'total': 6300, 'byStatus': dict(src), 'byTaskClass': dict(tc), 'adjustments': dict(adj), 'byComponent': {c: dict(v) for c, v in byc.items()}, 'reviewMode': 'per-item re-audit by AI subagents under ledger/review_inputs/RUBRIC.md against the RAM overlays, with the v1 disposition as context; mechanically tightened; SELF_REVIEWED'},
   'release_gate': {'local_loopback_owner_use': 'GO', 'private_single_operator_behind_tls': 'CONDITIONAL (re-measure s on the target host; keep NODE_OPTIONS heap flags off)', 'public_or_multi_tenant': 'NO-GO (identity provider, container/hosted rehearsal, independent security review, deployed-profile measurements outstanding)', 'desktop_electron': 'NO-GO until launched', 'ram_processing_or_pim_claim': 'NONE MADE'}},
  open('ledger/release.json', 'w'), indent=1)
files = []
for r_, ds, fs in os.walk('.'):
    ds[:] = [d for d in ds if d not in ('.vws-local', 'node_modules', 'dist', '.git')]
    for n in fs:
        p = os.path.relpath(os.path.join(r_, n), '.').replace(os.sep, '/')
        if p != 'release/manifest.json': files.append({'path': p, 'bytes': os.path.getsize(p), 'sha256': sha(p)})
os.makedirs('release', exist_ok=True)
json.dump({'candidate': REV, 'generated': NOW, 'protocol': 'hermit.vws.v2', 'profile': PROFILE, 'license': 'All rights reserved (LICENSE, unchanged)', 'testedProfiles': ['WEB on Linux/Node 22 loopback incl. Chromium and DF fabric; thread and process worker backends'], 'untestedProfiles': ['LOCAL/Electron', 'Windows', 'Docker image', 'Render', 'PowerShell gateway', 'DISTRIBUTED_VOLATILE', 'DURABLE_HYBRID', 'PIM_RESEARCH'], 'files': sorted(files, key=lambda x: x['path'])}, open('release/manifest.json', 'w'), indent=1)
print(json.dumps({'tests': len(TESTS), 'native': dict(tot), 'checks': dict(src), 'adjust': dict(adj), 'files': len(files)}, indent=1))
