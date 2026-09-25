"""Regenerate the human-readable production-exit summary purely from machine evidence (C100).

  python tools/exit_summary.py  -> conformance/PRODUCTION_EXIT_SUMMARY.md
"""
from __future__ import annotations

import json
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]


def main() -> int:
    gate = json.loads((PKG / "conformance/PK_GATE_RESULTS.json").read_text())
    ledger = json.loads((PKG / "CLOSURE_LEDGER.json").read_text())
    audit = json.loads((PKG / "AUDIT_MATRIX.json").read_text())
    lines = [f"# INV-35 {gate['version']} production-exit summary (generated — do not edit)", "",
             f"* Verdict: **{gate['verdict']}**", f"* Tree digest: `{gate['tree_digest']}`",
             f"* Generated: {gate['generated_at']}", f"* Evidence sealed: {gate['seal'].get('sealed')}",
             f"* Audit rows: {audit['counts']}", f"* Work packages: {ledger['closure_counts']}", "",
             "## Gates", "", "| Gate | OK |", "|---|---|"]
    lines += [f"| {k} | {'yes' if v.get('ok') else 'no'} |" for k, v in gate["gates"].items()]
    lines += ["", "## Blockers", ""]
    lines += [f"- [{b['gate']}] {b['detail']}" for b in gate["blockers"]] or ["- none"]
    (PKG / "conformance/PRODUCTION_EXIT_SUMMARY.md").write_text("\n".join(lines) + "\n")
    print("SUMMARY=WRITTEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
