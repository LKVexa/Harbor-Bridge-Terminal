"""Regenerate golden/negative contract fixtures from real executions (P2-21).
Golden = actual serialized outputs of this build.  Negative = a golden instance with
one targeted mutation that the schema MUST reject.  Deterministic (fixed clocks)."""
import copy, io, json, os, tempfile
import _path  # noqa
import polling as P, audit, pollog, config, clock

OUT = _path.PKG / "tests" / "fixtures"


def golden():
    ps = P.PollSet("t/c/i"); a, b = P.Pollable("net", "t/c/i"), P.Pollable("timer", "t/c/i"); b.signal()
    g = {"pk_poll.schema.json": ps.poll([a, b], timeout_ticks=5)}
    try:
        ps.poll([P.Pollable("x", "other")], timeout_ticks=1)
    except P.ForeignPollable as e:
        g["pk_poll_error.schema.json"] = e.as_dict()
    g["pk_poll_metrics.schema.json"] = ps.metrics_snapshot()
    g["pk_pollable.schema.json"] = {"schema": "PK_POLLABLE/1", "name": "net", "owner": "t/c/i"}
    buf = io.StringIO(); pollog.StructLogger(buf, clock=lambda: 1.0).log("INFO", "poll", "poll.ready", tenant="t", correlation_id="c")
    g["pk_poll_log.schema.json"] = json.loads(buf.getvalue())
    d = tempfile.mkdtemp(); pth = os.path.join(d, "a.jsonl")
    audit.AuditSink(pth, b"k" * 32, clock=lambda: 1.0).append("poll.deprecated_use", correlation_id="c")
    g["pk_poll_audit.schema.json"] = json.loads(open(pth).read())
    g["pk_poll_config.schema.json"] = config.BASE_CONFIG
    g["pk_clock_config.schema.json"] = clock.DEFAULT_CLOCK_CONFIG
    return g


MUTATIONS = [("drop_required", lambda d: d.pop("schema")), ("wrong_schema_const", lambda d: d.__setitem__("schema", "PK_POLL/2")),
             ("extra_property", lambda d: d.__setitem__("zz_unexpected", 1))]


def main():
    (OUT / "golden").mkdir(parents=True, exist_ok=True); (OUT / "negative").mkdir(parents=True, exist_ok=True)
    for sch, inst in golden().items():
        stem = sch.replace(".schema.json", "")
        (OUT / "golden" / f"{stem}.json").write_text(json.dumps({"schema_file": sch, "instance": inst}, indent=1, sort_keys=True) + "\n")
        for name, mut in MUTATIONS:
            bad = copy.deepcopy(inst); mut(bad)
            (OUT / "negative" / f"{stem}__{name}.json").write_text(json.dumps({"schema_file": sch, "mutation": name, "instance": bad}, indent=1, sort_keys=True) + "\n")
    extra = {"pk_poll__negative_index": ("pk_poll.schema.json", {**golden()["pk_poll.schema.json"], "ready_indexes": [-1]}),
             "pk_poll_error__unregistered_code": ("pk_poll_error.schema.json", {**golden()["pk_poll_error.schema.json"], "code": "PK_POLL_MADE_UP"}),
             "pk_poll__not_deprecated": ("pk_poll.schema.json", {**golden()["pk_poll.schema.json"], "deprecated": False})}
    for n, (sch, inst) in extra.items():
        (OUT / "negative" / f"{n}.json").write_text(json.dumps({"schema_file": sch, "mutation": n, "instance": inst}, indent=1, sort_keys=True) + "\n")
    print(len(list((OUT / "golden").iterdir())), len(list((OUT / "negative").iterdir())))


if __name__ == "__main__":
    main()
