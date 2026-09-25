#!/usr/bin/env python3
"""Unikernel Containership entry point: `python3 uc.py <command>` from this directory."""
import locale, os, subprocess, sys
sys.dont_write_bytecode = True  # the hull and hold are carried byte-identical; never write .pyc into them
# The ship, the hull's verifier and the engines' toolchains speak UTF-8. On a host whose locale encoding is not
# UTF-8 (a Windows console is cp1252) this interpreter re-executes itself once in UTF-8 mode, and every tool the
# ship starts inherits it, so a non-ASCII character in a report can never crash a step or a pipe.
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if (not getattr(sys.flags, "utf8_mode", 0) and locale.getpreferredencoding(False).lower().replace("-", "") != "utf8"
        and os.environ.get("UC_UTF8_REEXEC") != "1"):
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", UC_UTF8_REEXEC="1")
    raise SystemExit(subprocess.call([sys.executable, "-X", "utf8", "-B", os.path.abspath(__file__), *sys.argv[1:]], env=env))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(errors="backslashreplace")   # whatever the console is, printing never raises
    except Exception:  # noqa: BLE001
        pass
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ship"))
from unikernel.cli import main
raise SystemExit(main())
