"""What this host can and cannot do for the ship -- stated, never silent.

The ship is assembled and its batteries are first run on a POSIX host with a C
toolchain, `sh`, a JDK and a `fork`-capable Python. A Windows host without a C
compiler can still carry the ship, but four things differ, and each is handled
here rather than in the gates that stumble over them:

  no C toolchain   the three C engines (Small, Medium, Large) cannot be built and
                   the hull cannot build its runner: their gates are SKIPPED with
                   that reason (the QUORUM engine, the sort/seal/registry paths,
                   the .tif fabric and the hull's compile-only paths still work);
  no `sh`          the QUORUM VM's `compile` runs the bundled LCTL 1.6.1-RC1
                   column verifier through `sh START_LCTL_1_6_1.sh`, which only
                   execs `java -jar runtime/bin/lctl-hyperfederated.jar "$@"`; on
                   a host without `sh` the ship's N_XLARGE binding invokes the same
                   jar directly through java (recorded as a step, verdict
                   `lctl_column_verify=JVM_DIRECT`) and asks the VM to compile with
                   `--skip-lctl-verify`, so the same verification is done and said;
  no `fork`        the pacore fabric's multi-process profiles need the `fork`
                   start method; where the host has none the ship substitutes
                   `multi_thread_deterministic` and records the substitution;
  console encoding a Windows console is cp1252: the ship runs its Python in UTF-8
                   mode (uc.py re-executes itself with -X utf8 when the locale
                   encoding is not UTF-8; the .cmd launchers set PYTHONUTF8=1) so
                   the hull's verifier and the engines' toolchains, whose output
                   is UTF-8, cannot crash the ship's stdout or their pipes.

Every adaptation is recorded in the BUILD record, the VERIFY record and every
tick (`host` / `host_adaptations` / `host_note`), so a result obtained on a
limited host says so.
"""

from __future__ import annotations

import locale
import multiprocessing
import os
import platform
import shutil
import sys
from typing import Any, Dict, Optional, Tuple

_FACTS: Dict[str, Any] = {}


def facts(refresh: bool = False) -> Dict[str, Any]:
    """The host, once per process."""
    if _FACTS and not refresh:
        return _FACTS
    try:
        methods = list(multiprocessing.get_all_start_methods())
    except Exception:  # noqa: BLE001
        methods = []
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    f = {
        "platform": platform.platform(),
        "os": os.name,
        "python": sys.version.split()[0],
        "utf8_mode": bool(getattr(sys.flags, "utf8_mode", 0)),
        "locale_encoding": locale.getpreferredencoding(False),
        "cc": cc, "make": shutil.which("make"), "java": shutil.which("java"), "sh": shutil.which("sh"),
        "start_methods": methods,
        "fork": "fork" in methods,
        "c_toolchain": bool(cc and shutil.which("make")),
    }
    _FACTS.clear()
    _FACTS.update(f)
    return _FACTS


def limits() -> Dict[str, str]:
    """The host limits the ship works around, each with what would lift it."""
    f = facts()
    out: Dict[str, str] = {}
    if not f["c_toolchain"]:
        out["no_c_toolchain"] = ("no C compiler and/or make on PATH: the Small, Medium and Large engines cannot be built and "
                                 "the hull cannot build its runner (compile-only hull). Install a C toolchain (e.g. MSYS2/MinGW-w64 "
                                 "or Visual Studio Build Tools with `make`, or gcc+make on POSIX) and run BUILD again")
    if not f["sh"] or f["os"] == "nt":
        out["no_sh"] = (("no `sh` on PATH: " if not f["sh"] else "Windows host (START_LCTL_1_6_1.sh is a POSIX shell script): ")
                        + "the QUORUM engine's LCTL column verifier is invoked directly through java by the ship "
                        "(lctl_column_verify=JVM_DIRECT) instead of through START_LCTL_1_6_1.sh")
    if not f["fork"]:
        out["no_fork"] = ("Python has no `fork` start method here: multi-process fabric profiles are run as "
                          "multi_thread_deterministic and say so")
    if not f["java"]:
        out["no_java"] = "no java on PATH: the QUORUM engine compiles with --skip-lctl-verify (lctl_column_verify=SKIPPED_NO_JDK)"
    return out


def profile_for(requested: str) -> Tuple[str, Optional[str]]:
    """The execution profile the ship will actually use for `requested`, and why if it differs."""
    if requested in ("multi_process_deterministic", "multi_process_throughput") and not facts()["fork"]:
        return "multi_thread_deterministic", (f"host has no `fork` start method (start methods: {facts()['start_methods']}); "
                                              f"{requested} substituted by multi_thread_deterministic")
    return requested, None


def hull_execution() -> Tuple[bool, Optional[str]]:
    """Can the installed hull execute images on this host? (False, reason) if not."""
    from . import engines as E
    try:
        st = E.studio_status()
    except Exception as exc:  # noqa: BLE001
        return False, f"hull status unavailable: {type(exc).__name__}: {exc}"
    if not st.get("installed"):
        return False, st.get("error") or "hull not installed at _studio/ (run BUILD)"
    try:
        s = E.studio()
        r = s.status()
    except Exception as exc:  # noqa: BLE001
        return False, f"hull status unavailable: {type(exc).__name__}: {exc}"
    if r.get("runner_present"):
        return True, None
    mode = r.get("execution_mode") or "no runner"
    return False, (f"the hull cannot execute images on this host ({mode}: no runner built -- no C toolchain); "
                   f"compiling, sealing, importing and the .tif fabric images still work")


# --------------------------------------------------------------------------
# the N_XLARGE binding on a host without `sh`
# --------------------------------------------------------------------------

def _xlarge_no_sh_adapter(nodes_mod):
    """XLargeNodeAdapter that runs the LCTL column verifier directly through java.

    Everything else -- the QUORUM VM's compile, sign, verify and run steps, the
    snapshot, the result -- is the DF adapter's own code, called unchanged.
    """
    base = nodes_mod.XLargeNodeAdapter

    class XLargeNodeAdapterDirectJVM(base):  # type: ignore[misc,valid-type]
        HOST_ADAPTATION = ("no_sh" if not facts()["sh"] else "windows") + ": LCTL column verifier invoked directly through java; QUORUM compile with --skip-lctl-verify"

        def _execute_source(self, src_text, unit_id, workdir, max_steps=None):
            pre = []
            jar = os.path.join(self.root, "toolchain", "lctl_1_6_1_rc1", "runtime", "bin", "lctl-hyperfederated.jar")
            src = os.path.join(workdir, f"{unit_id}.lctlc")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write(src_text)
            if self.java and os.path.isfile(jar):
                # exactly what START_LCTL_1_6_1.sh does: exec java -jar "$ROOT/runtime/bin/lctl-hyperfederated.jar" "$@"
                self._step(pre, "lctl_column_verify", [self.java, "-jar", jar, "column-verify", src],
                           cwd=os.path.dirname(os.path.dirname(os.path.dirname(jar))))
                mode = "JVM_DIRECT"
            elif not self.java:
                mode = "SKIPPED_NO_JDK"
            else:
                mode = "SKIPPED_NO_VERIFIER"
            saved = self.lctl_tool
            # with no verifier script the DF adapter passes --skip-lctl-verify to the VM's compile,
            # which is what a host without `sh` needs; the verification above stands in for it
            self.lctl_tool = saved + ".not-runnable-without-sh"
            try:
                ex = base._execute_source(self, src_text, unit_id, workdir, max_steps=max_steps)
            finally:
                self.lctl_tool = saved
            ex["steps"] = pre + list(ex.get("steps") or [])
            extra = dict(ex.get("extra") or {})
            extra["lctl_column_verify"] = mode
            extra["host_adaptation"] = self.HOST_ADAPTATION
            ex["extra"] = extra
            return ex

    return XLargeNodeAdapterDirectJVM


def adapt_nodes(nodes_mod) -> Dict[str, Any]:
    """Apply the host adaptations to the bound `dfabric.nodes` module; say what was done."""
    out: Dict[str, Any] = {"host": {k: facts()[k] for k in ("platform", "python", "utf8_mode", "cc", "make", "java", "sh", "fork")},
                           "limits": limits(), "adaptations": {}}
    if (not facts()["sh"] or facts()["os"] == "nt") and "N_XLARGE" in getattr(nodes_mod, "ADAPTERS", {}):
        cls = nodes_mod.ADAPTERS["N_XLARGE"]
        if not getattr(cls, "HOST_ADAPTATION", None):
            nodes_mod.ADAPTERS["N_XLARGE"] = _xlarge_no_sh_adapter(nodes_mod)
        out["adaptations"]["N_XLARGE"] = nodes_mod.ADAPTERS["N_XLARGE"].HOST_ADAPTATION
    if not facts()["fork"]:
        out["adaptations"]["execution_profiles"] = "multi_process_* -> multi_thread_deterministic (no fork start method)"
    return out


def record() -> Dict[str, Any]:
    """The host block every BUILD/VERIFY/tick record carries."""
    return {"host": {k: facts()[k] for k in ("platform", "python", "utf8_mode", "locale_encoding", "cc", "make", "java", "sh", "fork")},
            "limits": limits()}
