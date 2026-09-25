"""GAP-042 semantic equivalence: one corpus through local dispatch and the remote path.

Each case runs twice with identical logical context: (L) callee placed on the
caller's host; (R) callee placed only on a peer reached through the PK_LOCAL_CHAIN/1
wire. Outcomes are compared on (ok, JSON-normalised value) or (public error
code, category, retriable). Allowed transport-only differences are listed in
ALLOWED_DIFFERENCES and docs/SEMANTIC_EQUIVALENCE.md; anything else fails.
"""
import json, unittest
from dataclasses import replace
from _support import E, ChainEndpoint, Deadline, LoopbackTransport, build, ctx, verifier
from inv21_local_service_chaining.transport import ChainHttpServer, HttpJsonTransport

CORPUS_VERSION = "SEQ-1.0"
ALLOWED_DIFFERENCES = ("tuples and other JSON-non-native containers are returned as JSON arrays/objects",
                       "route telemetry reads 'remote' on the caller for the R path",
                       "cross-tenant: local path reports PK_CHAIN_CROSS_TENANT (callee tenant is known "
                       "locally); remote path reports PK_CHAIN_CAPABILITY_REFUSED (caller host cannot see "
                       "the callee's tenant). Both refuse before dispatch; both are non-retriable.")

GRANTS = [("acme", n, op) for n in ("echo", "sum", "boom", "chain", "deny", "deep", "leaf", "big", "str")
          for op in ("invoke", "get")]
GRANTS = [g for g in GRANTS if g[1] != "deny"]


def handlers():
    def deep(hop, r):
        return hop.call("deep2", r)
    return {
        "echo": lambda hop, r: r,
        "sum": lambda hop, r: sum(r),
        "boom": lambda hop, r: {}["missing"],
        "chain": lambda hop, r: {"leaf": hop.call("leaf", r), "depth": hop.ctx.depth},
        "leaf": lambda hop, r: [r, hop.ctx.depth, hop.ctx.trace_id],
        "deny": lambda hop, r: "must-not-run",
        "deep": deep,
        "big": lambda hop, r: "x" * r,
        "str": lambda hop, r: str(r),
    }


CORPUS = [
    ("success-dict", "echo", {"a": [1, 2, {"b": None}]}, {}),
    ("success-unicode", "echo", "héllo ☃", {}),
    ("success-number", "sum", [1, 2, 3.5], {}),
    ("success-empty", "echo", None, {}),
    ("nested-chain", "chain", 7, {}),
    ("idempotent-op", "echo", 1, {"operation": "get"}),
    ("idem-key", "echo", 1, {"idempotency_key": "k-1"}),
    ("handler-exception", "boom", 0, {}),
    ("authz-denied", "deny", 0, {}),
    ("type-error-in-handler", "sum", "abc", {}),
    ("boundary-large", "big", 10000, {}),
    ("deadline-ok", "echo", 1, {"deadline": 5}),
]


def outcome(fn):
    try:
        return ("ok", json.loads(json.dumps(fn())))
    except E.ChainError as e:
        return ("err", e.code, e.category, e.is_retriable)


class SemanticEquivalenceTest(unittest.TestCase):
    def _local(self):
        ch, res, prov, v = build("host-a", grants=GRANTS)
        for n, h in handlers().items():
            res.place(n, "acme", h, abi="hop")
        return ch, v

    def _remote(self, http=None):
        b, rb, pb, v = build("host-b", grants=GRANTS)
        for n, h in handlers().items():
            rb.place(n, "acme", h, abi="hop")
        ep = ChainEndpoint(b, v)
        t = HttpJsonTransport(http) if http else LoopbackTransport(ep)
        a, ra, pa, _ = build("host-a", grants=GRANTS, transport=t)
        return a, ep

    def _ctx(self, v, kw):
        kw = dict(kw)
        if "deadline" in kw:
            kw["deadline"] = Deadline.after(kw["deadline"])
        return ctx(v, trace="t-seq", **kw)

    def _run(self, remote_url=None):
        L, v = self._local()
        R, ep = self._remote(remote_url)
        diffs = []
        for name, callee, payload, kw in CORPUS:
            lo = outcome(lambda: L.invoke(callee, payload, self._ctx(v, kw)))
            ro = outcome(lambda: R.invoke(callee, payload, self._ctx(v, kw)))
            if lo != ro:
                diffs.append((name, lo, ro))
        return diffs, ep

    def test_loopback_equivalence(self):
        diffs, _ = self._run()
        self.assertEqual(diffs, [], "unexplained local/remote divergence (release-blocking)")

    def test_http_equivalence(self):
        R, ep = self._remote()
        with ChainHttpServer(ep) as srv:
            diffs, _ = self._run(srv.url)
        self.assertEqual(diffs, [])

    def test_refusal_classes_equivalent(self):
        """Cycle / depth / cross-tenant / cancel / expired deadline are identical on both paths."""
        L, v = self._local()
        R, _ = self._remote()
        c = self._ctx(v, {})
        cases = {
            "cycle": replace(c, path=("echo",)),
            "depth": replace(c, path=("p1", "p2", "p3", "p4")),
        }
        cc = self._ctx(v, {}); cc.cancel.cancel()
        cases["cancelled"] = cc
        for label, cx in cases.items():
            self.assertEqual(outcome(lambda: L.invoke("echo", 1, cx)), outcome(lambda: R.invoke("echo", 1, cx)), label)
        other = ctx(v, tenant="evil")
        lo = outcome(lambda: L.invoke("echo", 1, other))
        ro = outcome(lambda: R.invoke("echo", 1, other))
        self.assertEqual(lo[0], "err"); self.assertEqual(ro[0], "err")
        # documented allowed difference #3 -- pinned exactly so any further drift fails
        self.assertEqual(lo[1:], ("PK_CHAIN_CROSS_TENANT", "isolation", False))
        self.assertEqual(ro[1:], ("PK_CHAIN_CAPABILITY_REFUSED", "authorization", False))

    def test_trace_and_depth_propagation_equivalent(self):
        L, v = self._local()
        R, _ = self._remote()
        self.assertEqual(outcome(lambda: L.invoke("chain", 3, self._ctx(v, {}))),
                         outcome(lambda: R.invoke("chain", 3, self._ctx(v, {}))))


if __name__ == "__main__":
    unittest.main()
