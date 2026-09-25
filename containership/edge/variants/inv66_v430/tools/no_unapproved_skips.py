#!/usr/bin/env python3
"""Fail if the unittest log contains skips other than the waived pk_core conformance skips (W-003)."""
import re
import sys

APPROVED = re.compile(r"pk_core not importable|reference jsonschema not installed")
log = open(sys.argv[1]).read()
skips = re.findall(r"\.\.\. skipped '([^']*)'", log)
bad = [s for s in skips if not APPROVED.search(s)]
print({"skips": len(skips), "unapproved": bad})
sys.exit(1 if bad or "FAILED" in log else 0)
