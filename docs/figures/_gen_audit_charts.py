import json, statistics
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root = Path(r"C:\Users\russe\OneDrive\Desktop\Harbor-Bridge-Terminal")
audit = json.loads((root / "fleet" / "QNODE_LOAD_AUDIT.json").read_text(encoding="utf-8"))
figdir = root / "docs" / "figures"
figdir.mkdir(parents=True, exist_ok=True)

nodes = audit["nodes"]
ids = [n["id"] for n in nodes]
info_ms = [n["load"]["probes"]["info"]["ms"] for n in nodes]
self_ms = [n["load"]["probes"]["selftest"]["ms"] for n in nodes]
bell_ms = [n["load"]["probes"]["bell"]["ms"] for n in nodes]
files = [n["inventory"]["files"] for n in nodes]
bytes_mb = [n["inventory"]["bytes"] / (1024*1024) for n in nodes]

# Fig 1: timing scatter / bar by probe type (boxplot)
fig, ax = plt.subplots(figsize=(8, 4.5), dpi=140)
bp = ax.boxplot([info_ms, self_ms, bell_ms], tick_labels=["info", "selftest", "bell"], patch_artist=True)
colors = ["#2a9d8f", "#e9c46a", "#e76f51"]
for patch, c in zip(bp["boxes"], colors):
    patch.set_facecolor(c)
    patch.set_alpha(0.75)
ax.set_ylabel("Latency (ms)")
ax.set_title("Qnode load-probe latency distribution (N=50)\nSource: fleet/QNODE_LOAD_AUDIT.json @ 2026-09-25 13:23:42 PDT")
ax.grid(True, axis="y", alpha=0.3)
# annotate stats
stats_txt = []
for name, arr in [("info", info_ms), ("selftest", self_ms), ("bell", bell_ms)]:
    stats_txt.append(f"{name}: med={statistics.median(arr):.0f} ms  min={min(arr)}  max={max(arr)}")
ax.text(0.02, 0.98, "\n".join(stats_txt), transform=ax.transAxes, va="top", fontsize=8,
        family="monospace", bbox=dict(boxstyle="round", facecolor="white", alpha=0.85))
fig.tight_layout()
fig.savefig(figdir / "fig-qnode-load-latency-boxplot.png")
plt.close()

# Fig 2: per-node stacked? or line of total probe time
fig, ax = plt.subplots(figsize=(11, 4.2), dpi=140)
x = list(range(1, 51))
ax.bar(x, info_ms, label="info", color="#2a9d8f", width=0.8)
ax.bar(x, self_ms, bottom=info_ms, label="selftest", color="#e9c46a", width=0.8)
bottom2 = [a+b for a,b in zip(info_ms, self_ms)]
ax.bar(x, bell_ms, bottom=bottom2, label="bell", color="#e76f51", width=0.8)
ax.set_xlabel("Qnode index (QN-01 … QN-50)")
ax.set_ylabel("Latency (ms)")
ax.set_title("Per-Qnode load probe stack (info + selftest + bell)\nAll 50/50 PASS — fleet/QNODE_LOAD_AUDIT.json")
ax.legend(loc="upper right")
ax.set_xlim(0.5, 50.5)
ax.grid(True, axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig(figdir / "fig-qnode-load-latency-stacked.png")
plt.close()

# Fig 3: pass-rate summary bars
fig, ax = plt.subplots(figsize=(7, 3.8), dpi=140)
labels = ["Inventory", "Load probe", "Overall carry", "Independence", "Fleet align"]
vals = [50, 50, 50, 1 if audit["independence"]["ok"] else 0, 1 if audit["fleet"]["ok"] else 0]
# normalize independence/fleet to 50 scale for display? Better two panels.
# Simple: inventory/load/overall as 50/50, and separate pass flags
ax.barh(["Fleet alignment", "Independence", "Overall (50)", "Load probe (50)", "Inventory (50)"],
        [50 if audit["fleet"]["ok"] else 0,
         50 if audit["independence"]["ok"] else 0,
         audit["counts"]["overall_pass"],
         audit["counts"]["load_pass"],
         audit["counts"]["inventory_pass"]],
        color=["#264653", "#2a9d8f", "#e9c46a", "#f4a261", "#e76f51"][::-1])
ax.set_xlim(0, 55)
ax.set_xlabel("Pass count (independence/fleet shown as 50 when PASS)")
ax.set_title(f"Qnode load audit summary — {audit['date_pt']}\nFailures: {len(audit['failures'])}")
for i, v in enumerate([50 if audit["fleet"]["ok"] else 0,
         50 if audit["independence"]["ok"] else 0,
         audit["counts"]["overall_pass"],
         audit["counts"]["load_pass"],
         audit["counts"]["inventory_pass"]]):
    ax.text(v + 0.5, i, str(v), va="center", fontsize=9)
fig.tight_layout()
fig.savefig(figdir / "fig-qnode-audit-summary.png")
plt.close()

# Fig 4: file count / size
fig, ax = plt.subplots(figsize=(8, 3.8), dpi=140)
ax.scatter(files, bytes_mb, c="#264653", s=28, alpha=0.7)
ax.set_xlabel("Files per Qnode copy")
ax.set_ylabel("Size (MB)")
ax.set_title("Qnode full-copy inventory footprint (N=50)")
ax.grid(True, alpha=0.3)
# annotate QN-01 outlier if any
for n, f, b in zip(ids, files, bytes_mb):
    if f != statistics.mode(files):
        ax.annotate(n, (f, b), textcoords="offset points", xytext=(5,5), fontsize=8)
fig.tight_layout()
fig.savefig(figdir / "fig-qnode-footprint-scatter.png")
plt.close()

# Write timing stats JSON for the note
stats = {
  "source": "fleet/QNODE_LOAD_AUDIT.json",
  "date_pt": audit["date_pt"],
  "n": 50,
  "info_ms": {"min": min(info_ms), "max": max(info_ms), "median": statistics.median(info_ms), "mean": round(statistics.mean(info_ms),1)},
  "selftest_ms": {"min": min(self_ms), "max": max(self_ms), "median": statistics.median(self_ms), "mean": round(statistics.mean(self_ms),1)},
  "bell_ms": {"min": min(bell_ms), "max": max(bell_ms), "median": statistics.median(bell_ms), "mean": round(statistics.mean(bell_ms),1)},
  "files": {"min": min(files), "max": max(files), "mode": statistics.mode(files)},
  "bytes": {"min": min(n["inventory"]["bytes"] for n in nodes), "max": max(n["inventory"]["bytes"] for n in nodes)},
  "selftest_tests_per_node": 35,
  "counts": audit["counts"],
}
(root / "docs" / "verification" / "audit-timing-stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
print("Wrote figures:", sorted(p.name for p in figdir.glob("fig-*.png")))
print(json.dumps(stats, indent=2))
