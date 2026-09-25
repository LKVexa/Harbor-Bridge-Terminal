"""C069: capacity/saturation model driven by measured numbers.

Inputs: benchmarks/results/latest.json (bytes/element, ns/element) and a config document.
Outputs performance/capacity-model.json: worst-case memory per stream and per tenant at the
configured ceilings, max streams per GiB, CPU share at a target element rate, and the
saturation point where credit stalls are expected (arrival rate > measured throughput)."""
import json
from _tools_pkg import ROOT, mod

K = mod("configuration")


def model(doc, bench, element_bytes=64):
    bpe = bench["memory"]["bytes_per_element"] + element_bytes
    s = doc["stream"]; q = doc["tenants"].get("default", {})
    per_stream = s["max_buffer"] * bpe
    tp = bench["throughput_eps"]["median"]
    return {"tier": doc.get("tier"), "assumed_element_payload_bytes": element_bytes,
            "worst_case_bytes_per_stream": per_stream,
            "worst_case_bytes_per_tenant": min(q.get("max_streams", 64) * per_stream, q.get("max_buffered", 65536) * bpe),
            "worst_case_bytes_instance": doc["overload"]["global_buffer_budget"] * bpe,
            "streams_per_gib_at_full_buffer": int((1 << 30) // per_stream),
            "saturation_elements_per_s_single_core": tp,
            "cpu_core_share_at_100k_eps": round(100_000 / tp, 3),
            "stall_expected_when": "sustained writer arrival rate > reader grant rate or > saturation rate"}


def main():
    bench = json.loads((ROOT / "benchmarks" / "results" / "latest.json").read_text())
    out = {"source_benchmark": bench["timestamp"], "environment": bench["environment"], "tiers": {}}
    for ov in [None] + sorted((ROOT / "config" / "overlays").glob("*.json")):
        doc = K.load_layers(ov) if ov else K.load_layers()
        out["tiers"][ov.stem if ov else "defaults"] = model(doc, bench)
    (ROOT / "performance" / "capacity-model.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out["tiers"], indent=1))


if __name__ == "__main__":
    main()
