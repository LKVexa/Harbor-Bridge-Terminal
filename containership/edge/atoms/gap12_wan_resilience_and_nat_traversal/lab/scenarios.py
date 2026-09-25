"""NAT-lab scenario runner.  Every scenario builds a fresh kernel topology,
runs real GAP-12 code in the namespaces, captures packets on the NAT
router's outside interface, tears everything down, and records:
topology + gateway rules, seed, timings, outcome, pcap flow summary, and
whether teardown left anything behind.

    python3 lab/scenarios.py [--out evidence/lab] [--only name,...]

Exit 0 when every scenario's assertion held, 1 otherwise, 3 when the lab
cannot run on this host (reported NOT-EVIDENCED by the evaluator, never PASS).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import netlab  # noqa: E402
import pcap as pcapmod  # noqa: E402

STUN_SRV = """
import time
from gap12_wan_resilience_and_nat_traversal.wan import stun, turn
s = stun.StunServer([('198.51.100.254',3478),('198.51.100.253',3479),('198.51.100.254',3479),('198.51.100.253',3478),('192.0.2.254',3478)]).__enter__()
t = turn.TurnServer(('198.51.100.254',3480), {'site-a':'pw-a','site-b':'pw-b'}, quota_bytes={'site-a': 1_000_000}).__enter__()
import socket, threading
ls = socket.socket(); ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); ls.bind(('198.51.100.254', 8443)); ls.listen(8)
def echo():
    while True:
        c, _ = ls.accept(); d = c.recv(100); c.sendall(d); c.close()
threading.Thread(target=echo, daemon=True).start()
print('ready', flush=True)
time.sleep(float(__import__('os').environ.get('LAB_SERVER_SECONDS', '40')))
print('usage', __import__('json').dumps(t.usage), flush=True)
"""

DISCOVER = """
import json, socket
from gap12_wan_resilience_and_nat_traversal.wan import stun
d = stun.discover([('198.51.100.254',3478),('198.51.100.253',3479)], bind=('0.0.0.0', 40000), rto=0.1, rc=5, rm=4, deadline_s=4)
print(json.dumps({'reason': d.reason, 'mapped': d.mapped, 'consistent': d.consistent,
                  'sends': [e.get('sends') for e in d.per_server]}))
"""

CLASSIFY = """
import json
from gap12_wan_resilience_and_nat_traversal.wan import natclass
c = natclass.classify(('198.51.100.254',3478), bind=('0.0.0.0', 40001))
print(json.dumps({'mapping': c.mapping, 'filtering': c.filtering, 'label': c.label(), 'missing': c.missing,
                  'mapped': c.evidence.get('test1', {}).get('mapped')}))
"""

PEER_B = """
import json, os, socket, time
from gap12_wan_resilience_and_nat_traversal.wan import holepunch, stun
work = os.environ['LAB_WORK']
t = holepunch.Ticket(**json.load(open(work + '/ticket_b.json')))
t = holepunch.Ticket(t.session, tuple(t.me), tuple(t.peer), t.start, t.expires, t.tag)
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', 40000))
r = holepunch.punch(s, t, ticket_key=b'kb', session_key=b'session', prime_ttl=2)
out = {'punch': r.__dict__}
# relay leg: answer pings arriving via a's TURN relay
deadline = time.time() + 12
relay = None
while time.time() < deadline and relay is None:
    if os.path.exists(work + '/relay_a.json'):
        relay = tuple(json.load(open(work + '/relay_a.json')))
    time.sleep(0.05)
echoed = 0
if relay:
    s.settimeout(0.2)
    while time.time() < deadline:
        s.sendto(b'hello-from-b', relay)
        try:
            d, src = s.recvfrom(2048)
            if d == b'ping' and tuple(src) == relay:
                s.sendto(b'pong', relay); echoed += 1
                if echoed >= 3: break
        except OSError:
            pass
out['relay_echoes'] = echoed
print(json.dumps(out))
"""

CONTROLLER_A = """
import json, os, socket, time
from gap12_wan_resilience_and_nat_traversal.wan import controller, holepunch, security, transport, turn, config
from gap12_wan_resilience_and_nat_traversal.wan.quality import InstrumentedRelay
work = os.environ['LAB_WORK']
t = holepunch.Ticket(**json.load(open(work + '/ticket_a.json')))
t = holepunch.Ticket(t.session, tuple(t.me), tuple(t.peer), t.start, t.expires, t.tag)
B_PRIVATE = ('10.2.0.2', 40000)

class Direct(controller.Adapter):
    def endpoints(self): return [B_PRIVATE]
    def attempt(self, cancel):
        r = transport.tcp_connect(B_PRIVATE, deadline_s=0.8)
        if r.ok: r.sock.close()
        return r.ok

class Punch(controller.Adapter):
    def endpoints(self): return [t.peer]
    def attempt(self, cancel):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', 40000))
        try:
            self.result = holepunch.punch(s, t, ticket_key=b'ka', session_key=b'session', prime_ttl=2)
            return self.result.ok
        finally:
            s.close()
    def evidence(self): return b'attested-b'

class Relay(controller.Adapter):
    def endpoints(self): return [('198.51.100.254', 3480)]
    def attempt(self, cancel):
        c = turn.TurnClient(('198.51.100.254', 3480), 'site-a', 'pw-a')
        self.client = c
        c.allocate()
        c.create_permission(t.peer[0])
        json.dump(list(c.relayed), open(work + '/relay_a.json.tmp', 'w')); os.replace(work + '/relay_a.json.tmp', work + '/relay_a.json')
        got = None
        end = time.time() + 6
        while time.time() < end and got is None:
            m = c.recv(0.3)
            if m and m[1] == b'hello-from-b':
                got = m[0]
        if got is None: return False
        c.channel_bind(got)
        self.inst = InstrumentedRelay(c)
        pongs = 0
        for _ in range(3):
            self.inst.send(got, b'ping')
            end = time.time() + 1
            while time.time() < end:
                m = self.inst.recv(0.3)
                if m and m[1] == b'pong': pongs += 1; break
        self.pongs = pongs
        return pongs >= 1
    def cleanup(self):
        pass
    def evidence(self): return b'attested-b'

cfg = {**config.defaults(), 'environment': 'lab', 'attempt_timeout_s': 9.0, 'overall_timeout_s': 30.0}
def verifier(peer, ev):
    now = time.time()
    if ev != b'attested-' + peer[-1:].encode(): raise ValueError('bad evidence')
    return security.Attestation(peer, now - 1, now + 300, 'sha256:lab')
ctl = controller.Controller(cfg, security.TrustGate(verifier), security.EgressPolicy(allow=[('0.0.0.0/0', (1, 65535))]),
                            security.RateLimiter({'global': (100, 100)}))
adapters = {'direct': Direct('direct'), 'hole-punch': Punch('hole-punch'), 'relay': Relay('relay')}
res = ctl.connect('site-b', adapters)
relay = adapters['relay']
out = {'ok': res['ok'], 'strategy': res['strategy'], 'trusted': res['trusted'], 'reason': res['reason'],
       'trail': res['trail'], 'status': res['state']['status'], 'explain': ctl.explain('site-b'),
       'relay_counters': getattr(getattr(relay, 'client', None), 'counters', None) and relay.client.counters.as_dict(),
       'instrumented_bytes': getattr(getattr(relay, 'inst', None), 'bytes_out', None),
       'metrics_sample': [l for l in ctl.metrics.expose().splitlines() if l.startswith('g12_attempts_total{')]}
if getattr(relay, 'client', None): relay.client.close()
print(json.dumps(out, default=str))
"""

TCP_FALLBACK = """
import json
from gap12_wan_resilience_and_nat_traversal.wan import stun, transport
d = stun.discover([('198.51.100.254',3478),('198.51.100.253',3479)], rto=0.1, rc=3, rm=3, deadline_s=2)
r = transport.tcp_connect(('198.51.100.254', 8443), deadline_s=2)
echo = None
if r.ok:
    r.sock.sendall(b'tcp-ok'); echo = r.sock.recv(10).decode(); r.sock.close()
print(json.dumps({'udp': d.reason, 'tcp': r.reason, 'echo': echo, 'open_sockets': transport.open_sockets()}))
"""


def _node_env(work: str) -> dict:
    return {"LAB_WORK": work}


def _spawn(lab, node, code, env=None):
    e = dict(os.environ, PYTHONPATH=os.path.dirname(os.path.dirname(HERE)), PYTHONDONTWRITEBYTECODE="1", **(env or {}))
    return subprocess.Popen(["nsenter", f"--net=/proc/{lab.nodes[node].pid}/ns/net", sys.executable, "-B", "-c", code],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=e)


def _run(lab, node, code, env=None, timeout=60):
    p = _spawn(lab, node, code, env)
    out, err = p.communicate(timeout=timeout)
    if p.returncode:
        raise RuntimeError(f"{node}: {err[-1500:]}")
    return json.loads(out.strip().splitlines()[-1])


def _capture(lab, node, iface, seconds, path):
    return _spawn(lab, node, f"import sys; sys.path.insert(0,{HERE!r}); import pcap; pcap.capture({iface!r},{seconds},{path!r})")


def scenario(name, topology, nat_a, nat_b, body, out_dir, capture=("ra", "ra_out")):
    rec = {"scenario": name, "started": time.time(), "seed": 0}
    lab = netlab.Lab(topology, nat_a, nat_b)
    work = tempfile.mkdtemp(prefix=f"g12-{name}-")
    pcap_path = os.path.join(out_dir, f"{name}.pcap")
    try:
        lab.build()
        rec["topology"] = lab.describe()
        srv = _spawn(lab, "inet", STUN_SRV, {"LAB_SERVER_SECONDS": "45"})
        assert srv.stdout.readline().strip() == "ready"
        cap = _capture(lab, capture[0], capture[1], 30, pcap_path) if capture else None
        time.sleep(0.3)
        t0 = time.time()
        rec["result"], rec["assertion"] = body(lab, work)
        rec["elapsed_s"] = round(time.time() - t0, 3)
        srv.kill()
        if cap:
            cap.kill()
            cap.wait()
            rec["pcap"] = os.path.basename(pcap_path)
            rec["pcap_summary"] = pcapmod.summarize(pcap_path)
        rec["passed"] = bool(rec["assertion"])
    except Exception as exc:
        rec["passed"] = False
        rec["error"] = f"{type(exc).__name__}: {exc}"
        rec["traceback"] = traceback.format_exc()[-2000:]
    finally:
        rec["teardown_leftovers"] = lab.teardown()
        rec["passed"] = rec.get("passed", False) and not rec["teardown_leftovers"]
    return rec


def _discover_body(expect_reason, expect_consistent):
    def body(lab, work):
        a = _run(lab, "a", DISCOVER)
        return a, a["reason"] == expect_reason and a["consistent"] == expect_consistent
    return body


def _classify_body(expect_mapping, expect_filtering, port=40001):
    def body(lab, work):
        c = _run(lab, "a", CLASSIFY.replace("40001", str(port)))
        return c, (c["mapping"], c["filtering"]) == (expect_mapping, expect_filtering)
    return body


def _cgnat_body(lab, work):
    c = _run(lab, "a", CLASSIFY)
    code = f"""
import json
from gap12_wan_resilience_and_nat_traversal.wan import natclass
a = natclass.assess_cgnat(local_address='192.168.1.2', mapped_address={c['mapped'][0]!r} if {c['mapped']!r} else None,
                          gateway_wan_address='100.64.0.2', mapping_behaviour={c['mapping']!r})
print(json.dumps(a.__dict__))"""
    a = _run(lab, "a", code)
    return {"classification": c, "cgnat": a}, a["verdict"] == "likely" and c["mapped"][0] == "198.51.100.1"


def _e2e_body(expect_strategy):
    def body(lab, work):
        from gap12_wan_resilience_and_nat_traversal.wan import holepunch
        a = _run(lab, "a", DISCOVER)
        b_disc = DISCOVER.replace("('198.51.100.254',3478),('198.51.100.253',3479)", "('192.0.2.254',3478)")
        b = _run(lab, "b", b_disc)
        rv = holepunch.Rendezvous({"a": b"ka", "b": b"kb"})
        ta, tb = rv.issue("a", a["mapped"], "b", b["mapped"], delay=2.0, window=3.0)
        json.dump(ta.__dict__, open(work + "/ticket_a.json", "w"))
        json.dump(tb.__dict__, open(work + "/ticket_b.json", "w"))
        pb = _spawn(lab, "b", PEER_B, _node_env(work))
        ra = _run(lab, "a", CONTROLLER_A, _node_env(work), timeout=90)
        ob, eb = pb.communicate(timeout=60)
        rb = json.loads(ob.strip().splitlines()[-1]) if ob.strip() else {"error": eb[-800:]}
        res = {"a_mapped": a["mapped"], "b_mapped": b["mapped"], "controller": ra, "peer_b": rb}
        ok = ra["ok"] and ra["strategy"] == expect_strategy and ra["trusted"] and \
            [t["strategy"] for t in ra["trail"]][:1] == ["direct"]
        return res, ok
    return body


def _tcp_fallback_body(lab, work):
    r = _run(lab, "a", TCP_FALLBACK)
    return r, r["udp"] == "NET_UDP_BLOCKED" and r["tcp"] == "OK" and r["echo"] == "tcp-ok" and r["open_sockets"] == 0


def _lossy_body(lab, work):
    runs = [_run(lab, "a", DISCOVER.replace("40000", str(41000 + i))) for i in range(5)]
    ok = sum(r["reason"] == "OK" for r in runs)
    retrans = sum(any((s or 0) > 1 for s in r["sends"]) for r in runs)
    return {"runs": runs, "succeeded": ok, "runs_with_retransmission": retrans}, ok >= 4 and retrans >= 1


SCENARIOS = {
    "stun_eim_apdf": ("two_nat", "eim_apdf", "eim_apdf", _discover_body("OK", True)),
    "stun_apdm": ("two_nat", "apdm", "apdm", _discover_body("DEP_INCONSISTENT", False)),
    "stun_udp_blocked": ("two_nat", "udp_blocked", "udp_blocked", _discover_body("NET_UDP_BLOCKED", None)),
    "stun_lossy30": ("two_nat", "lossy30", "lossy30", _lossy_body),
    "classify_eim_apdf": ("two_nat", "eim_apdf", "eim_apdf", _classify_body("endpoint-independent", "address-and-port-dependent")),
    "classify_apdm": ("two_nat", "apdm", "apdm", _classify_body("address-and-port-dependent", "address-and-port-dependent")),
    "classify_eim_eif": ("two_nat", "eim_eif", "eim_eif", _classify_body("endpoint-independent", "endpoint-independent", port=40000)),
    "cgnat_double_nat": ("cgnat", "eim_apdf", "none", _cgnat_body),
    "tcp_fallback_udp_blocked": ("two_nat", "udp_blocked", "udp_blocked", _tcp_fallback_body),
    "e2e_holepunch_eim": ("two_nat", "eim_apdf", "eim_apdf", _e2e_body("hole-punch")),
    "e2e_relay_symmetric": ("two_nat", "apdm", "apdm", _e2e_body("relay")),
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "evidence", "lab"))
    ap.add_argument("--only", default="")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    ok, why = netlab.available()
    if not ok:
        json.dump({"available": False, "reason": why}, open(os.path.join(args.out, "lab_results.json"), "w"), indent=1)
        print("LAB NOT AVAILABLE:", why)
        return 3
    sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
    names = [n for n in SCENARIOS if not args.only or n in args.only.split(",")]
    results = []
    for n in names:
        topo, na, nb, body = SCENARIOS[n]
        r = scenario(n, topo, na, nb, body, args.out)
        print(f"{'PASS' if r['passed'] else 'FAIL'} {n} ({r.get('elapsed_s')}s){' ' + r.get('error', '') if not r['passed'] else ''}")
        results.append(r)
    doc = {"schema": "G12-LAB-RESULTS/1", "available": True, "kernel": os.uname().release,
           "limits": ["kernel without IPv6 (EAFNOSUPPORT)", "no tc/netem: delay/jitter/reorder/dup/corrupt/bandwidth/MTU impairment unavailable",
                      "loss injected with iptables -m statistic only"],
           "results": results}
    with open(os.path.join(args.out, "lab_results.json"), "w") as fh:
        json.dump(doc, fh, indent=1, default=str)
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
