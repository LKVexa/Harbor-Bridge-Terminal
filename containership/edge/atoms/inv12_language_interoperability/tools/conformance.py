"""MC-024 cross-language conformance matrix + MC-029 differential tester.

Implementations: python (canon reference), rust, go, javascript fixtures.

1. Golden conformance: every implementation encodes every valid golden value to
   the exact golden image, decodes every golden image to the golden CJV value,
   and rejects every invalid image with the golden error code.
2. Producer -> consumer matrix: every producer's images are decoded by every
   consumer (16 pairs) and compared to the golden value.
3. Differential: N random schema-typed values (seeded) and M mutated images are
   pushed through all implementations; any divergence (value, image, or error
   code) is reported with its seed.

Usage: python tools/conformance.py [--random N] [--mutations M] [--seed S] [--out FILE]
"""
import argparse
import json
import pathlib
import random
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from canon import cjv, layout, types as ty  # noqa: E402
from canon.generators import gen_type, gen_value, mutate  # noqa: E402

CORPUS = ROOT / "fixtures/corpus/vectors.json"


def build():
    bins = {}
    if shutil.which("cargo"):
        subprocess.run(["cargo", "build", "-q", "--release", "--offline"], cwd=ROOT / "fixtures/rust", check=True)
        bins["rust"] = [str(ROOT / "fixtures/rust/target/release/inv12rs")]
    if shutil.which("go"):
        out = pathlib.Path(tempfile.gettempdir()) / "inv12go"
        subprocess.run(["go", "build", "-o", str(out), "."], cwd=ROOT / "fixtures/go", check=True)
        bins["go"] = [str(out)]
    if shutil.which("node"):
        bins["javascript"] = ["node", str(ROOT / "fixtures/js/inv12.mjs")]
    return bins


def py_encode(vec):
    out = {}
    for v in vec["valid"]:
        t = ty.from_descriptor(v["descriptor"])
        try:
            val = cjv.from_cjv(v["value"], t)
            img, root = layout.encode(val, t, validated=t.kind in ("own", "borrow"))
            out[v["id"]] = {"image": img.hex(), "root": root}
        except Exception as e:  # noqa: BLE001
            out[v["id"]] = {"err": getattr(e, "code", type(e).__name__)}
    return out


def py_decode(vec, images):
    out = {}
    for v in vec["valid"] + vec["invalid"]:
        src = images.get(v["id"])
        if src is None:
            continue
        if "err" in src:
            out[v["id"]] = {"err": "PRODUCER_FAILED"}
            continue
        t = ty.from_descriptor(v["descriptor"])
        try:
            out[v["id"]] = {"ok": cjv.to_cjv(layout.decode(bytes.fromhex(src["image"]), src["root"], t), t)}
        except Exception as e:  # noqa: BLE001
            out[v["id"]] = {"err": getattr(e, "code", type(e).__name__)}
    return out


def run(bins, lang, mode, vec_path, img_path=None, vec=None, images=None):
    if lang == "python":
        return py_encode(vec) if mode == "encode" else py_decode(vec, images)
    cmd = bins[lang] + [mode, str(vec_path)] + ([str(img_path)] if img_path else [])
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if p.returncode:
        raise RuntimeError(f"{lang} {mode} failed: {p.stderr[-500:]}")
    return json.loads(p.stdout)


def matrix(bins, vec, vec_path, tmp):
    langs = ["python"] + sorted(bins)
    golden_imgs = {v["id"]: {"image": v["image"], "root": v["root"]} for v in vec["valid"] + vec["invalid"]}
    gpath = tmp / "golden_images.json"
    gpath.write_text(json.dumps(golden_imgs))
    report = {"languages": langs, "golden": {}, "pairs": {}, "failures": []}
    produced = {}
    for lang in langs:
        enc = run(bins, lang, "encode", vec_path, vec=vec)
        produced[lang] = enc
        dec = run(bins, lang, "decode", vec_path, gpath, vec=vec, images=golden_imgs)
        e_ok = sum(enc[v["id"]].get("image") == v["image"] for v in vec["valid"])
        d_ok = sum(dec[v["id"]].get("ok", "\0") == v["value"] for v in vec["valid"])
        r_ok = sum(dec[v["id"]].get("err") == v["error"] for v in vec["invalid"])
        for v in vec["valid"]:
            if enc[v["id"]].get("image") != v["image"]:
                report["failures"].append({"lang": lang, "id": v["id"], "stage": "encode"})
            if dec[v["id"]].get("ok", "\0") != v["value"]:
                report["failures"].append({"lang": lang, "id": v["id"], "stage": "decode"})
        for v in vec["invalid"]:
            if dec[v["id"]].get("err") != v["error"]:
                report["failures"].append({"lang": lang, "id": v["id"], "stage": "reject",
                                           "got": dec[v["id"]]})
        report["golden"][lang] = {"encode_exact": f"{e_ok}/{len(vec['valid'])}",
                                  "decode_exact": f"{d_ok}/{len(vec['valid'])}",
                                  "reject_exact": f"{r_ok}/{len(vec['invalid'])}"}
    for p in langs:
        ipath = tmp / f"images_{p}.json"
        ipath.write_text(json.dumps(produced[p]))
        for c in langs:
            dec = run(bins, c, "decode", vec_path, ipath, vec=vec, images=produced[p])
            ok = sum(dec[v["id"]].get("ok", "\0") == v["value"] for v in vec["valid"])
            report["pairs"][f"{p}->{c}"] = f"{ok}/{len(vec['valid'])}"
            if ok != len(vec["valid"]):
                report["failures"].append({"pair": f"{p}->{c}", "passed": ok})
    return report


def differential(bins, n, m, seed, tmp):
    rng = random.Random(seed)
    valid, invalid = [], []
    for i in range(n):
        t = gen_type(rng, 3)
        v = gen_value(rng, t)
        img, root = layout.encode(v, t)
        valid.append({"id": f"r{i}", "descriptor": ty.descriptor(t), "value": cjv.to_cjv(v, t),
                      "image": img.hex(), "root": root})
        for j in range(m):
            invalid.append({"id": f"r{i}m{j}", "descriptor": ty.descriptor(t),
                            "image": mutate(rng, img).hex(), "root": root, "error": None})
    vec = {"valid": valid, "invalid": invalid}
    vpath = tmp / "random_vectors.json"
    vpath.write_text(json.dumps(vec))
    imgs = {v["id"]: {"image": v["image"], "root": v["root"]} for v in valid + invalid}
    ipath = tmp / "random_images.json"
    ipath.write_text(json.dumps(imgs))
    langs = ["python"] + sorted(bins)
    results = {lang: run(bins, lang, "decode", vpath, ipath, vec=vec, images=imgs) for lang in langs}
    encs = {lang: run(bins, lang, "encode", vpath, vec=vec) for lang in langs}
    divergences = []
    for v in valid + invalid:
        outs = {lang: json.dumps(results[lang][v["id"]], sort_keys=True) for lang in langs}
        if len(set(outs.values())) != 1:
            divergences.append({"id": v["id"], "outputs": {k: json.loads(x) for k, x in outs.items()}})
    for v in valid:
        imgs_ = {lang: encs[lang][v["id"]].get("image") for lang in langs}
        if len(set(imgs_.values())) != 1 or imgs_["python"] != v["image"]:
            divergences.append({"id": v["id"], "stage": "encode"})
        if results["python"][v["id"]].get("ok", "\0") != v["value"]:
            divergences.append({"id": v["id"], "stage": "roundtrip"})
    rejected = sum("err" in results["python"][v["id"]] for v in invalid)
    return {"seed": seed, "random_values": n, "mutations": len(invalid), "mutations_rejected_by_all": rejected,
            "languages": langs, "divergences": divergences[:50], "divergence_count": len(divergences)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--random", type=int, default=300)
    ap.add_argument("--mutations", type=int, default=5)
    ap.add_argument("--seed", type=int, default=20260922)
    ap.add_argument("--out", default=str(ROOT / "evidence/conformance.json"))
    a = ap.parse_args()
    t0 = time.time()
    bins = build()
    vec = json.loads(CORPUS.read_text())
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        rep = {"matrix": matrix(bins, vec, CORPUS, tmp),
               "differential": differential(bins, a.random, a.mutations, a.seed, tmp)}
    rep["seconds"] = round(time.time() - t0, 2)
    ok = not rep["matrix"]["failures"] and rep["differential"]["divergence_count"] == 0 \
        and len(rep["matrix"]["languages"]) == 4
    rep["verdict"] = "PASS" if ok else "FAIL"
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verdict": rep["verdict"], "golden": rep["matrix"]["golden"],
                      "pairs": rep["matrix"]["pairs"],
                      "differential": {k: rep["differential"][k] for k in
                                       ("random_values", "mutations", "mutations_rejected_by_all",
                                        "divergence_count")}}, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
