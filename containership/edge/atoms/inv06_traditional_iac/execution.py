"""Execution adapter, provider lifecycle and sandbox (MC-015, MC-018, MC-019/020 contract, MC-035).

* ``TerraformRunner`` invokes a *pinned* engine binary only after verifying its
  SHA-256 against an allowlist, with a scrubbed environment, a dedicated
  working directory, ``-input=false -no-color -json`` style deterministic
  arguments, plugin-download disabled (``TF_PLUGIN_CACHE_MAY_BREAK_DEPENDENCY_LOCK_FILE``
  unset, ``-plugin-dir`` required) and a hard timeout.  It parses the
  machine-readable ``terraform show -json`` plan format, never console text.
  The package does not ship Terraform; if no approved binary is configured
  the runner refuses (``EngineUnavailable``).
* ``ProviderRegistry`` holds the provider allowlist: name → exact version →
  SHA-256; anything unlisted, unpinned or mismatched is refused.
* ``Provider`` is the adapter protocol that cloud (MC-019) and
  datacenter/bare-metal (MC-020) adapters implement; ``InMemoryProvider`` is
  the conformance reference used by the contract tests.  Concrete
  authenticated cloud adapters are *not* bundled.
* ``sandbox_env`` / ``SandboxPolicy`` define the minimal ambient authority an
  execution gets: an allowlisted environment, no inherited secrets, a private
  temp dir and optional POSIX resource limits.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from .security import verify_artifact
from .state import IacError


class EngineUnavailable(IacError):
    code = "PK_IAC_ENGINE_UNAVAILABLE"


class EngineFailed(IacError):
    code = "PK_IAC_ENGINE_FAILED"


class ProviderRefused(IacError):
    code = "PK_IAC_PROVIDER_REFUSED"


class UnsupportedPlatform(IacError):
    code = "PK_IAC_UNSUPPORTED_PLATFORM"


# ------------------------------------------------------------------ sandbox
ENV_ALLOWLIST = ("PATH", "LANG", "LC_ALL", "TZ", "SYSTEMROOT", "TEMP", "TMP")


@dataclass
class SandboxPolicy:
    env_allow: tuple[str, ...] = ENV_ALLOWLIST
    extra_env: dict[str, str] = field(default_factory=dict)
    cpu_seconds: int = 600
    address_space_bytes: int = 4 * 1024 ** 3
    max_open_files: int = 1024
    timeout: float = 900.0


def sandbox_env(policy: SandboxPolicy, workdir: pathlib.Path) -> dict[str, str]:
    env = {k: os.environ[k] for k in policy.env_allow if k in os.environ}
    env.update({
        "HOME": str(workdir),
        "TMPDIR": str(workdir / "tmp"),
        "TF_IN_AUTOMATION": "1",
        "TF_INPUT": "0",
        "CHECKPOINT_DISABLE": "1",  # no phone-home
    })
    for k, v in policy.extra_env.items():
        if k.upper().startswith(("AWS_", "AZURE_", "GOOGLE_", "ARM_")):
            raise ProviderRefused("provider credentials must be injected by the credential broker, not ambient env", details={"var": k})
        env[k] = v
    return env


def _preexec(policy: SandboxPolicy):  # pragma: no cover - exercised only on POSIX with real engine
    if sys.platform.startswith("win"):
        return None
    import resource

    def fn() -> None:
        os.setsid()
        resource.setrlimit(resource.RLIMIT_CPU, (policy.cpu_seconds, policy.cpu_seconds))
        resource.setrlimit(resource.RLIMIT_AS, (policy.address_space_bytes, policy.address_space_bytes))
        resource.setrlimit(resource.RLIMIT_NOFILE, (policy.max_open_files, policy.max_open_files))

    return fn


# ----------------------------------------------------------- provider pins
class ProviderRegistry:
    def __init__(self, pins: Mapping[str, Mapping[str, str]]) -> None:
        # pins: "registry/namespace/name" -> {"version": "x.y.z", "sha256": "..."}
        for name, pin in pins.items():
            if not pin.get("version") or any(c in pin["version"] for c in "~><=^* "):
                raise ProviderRefused("provider must be pinned to an exact version", details={"provider": name})
            if len(pin.get("sha256", "")) != 64:
                raise ProviderRefused("provider pin requires sha256", details={"provider": name})
        self.pins = {k: dict(v) for k, v in pins.items()}

    def check_lock(self, lock: Mapping[str, Mapping[str, str]]) -> None:
        """``lock`` is the resolved provider set (name → version/sha256) from the engine lock file."""
        for name, got in lock.items():
            pin = self.pins.get(name)
            if pin is None:
                raise ProviderRefused("provider not on allowlist", details={"provider": name})
            if got.get("version") != pin["version"] or got.get("sha256", "").lower() != pin["sha256"].lower():
                raise ProviderRefused("provider version/digest does not match pin", details={"provider": name, "pinned": pin, "resolved": dict(got)})

    def verify_binary(self, name: str, path: str | os.PathLike[str]) -> None:
        pin = self.pins.get(name)
        if pin is None:
            raise ProviderRefused("provider not on allowlist", details={"provider": name})
        verify_artifact(path, expected_sha256=pin["sha256"])


# --------------------------------------------------------- engine runner
def parse_terraform_plan_json(doc: Mapping[str, Any]) -> dict[str, Any]:
    """Map ``terraform show -json`` output to ``{create, update, delete, replace}`` address lists."""
    if not isinstance(doc, Mapping) or "format_version" not in doc:
        raise EngineFailed("not a terraform JSON plan document")
    major = str(doc["format_version"]).split(".")[0]
    if major != "1":
        raise EngineFailed("unsupported terraform JSON format version", details={"format_version": doc["format_version"]})
    out = {"create": [], "update": [], "delete": [], "replace": [], "noop": []}
    for rc in doc.get("resource_changes", []) or []:
        actions = tuple(rc.get("change", {}).get("actions", []))
        addr = rc.get("address")
        if not isinstance(addr, str):
            raise EngineFailed("resource change without address")
        if actions in (("create",),):
            out["create"].append(addr)
        elif actions == ("update",):
            out["update"].append(addr)
        elif actions == ("delete",):
            out["delete"].append(addr)
        elif set(actions) == {"delete", "create"}:
            out["replace"].append(addr)
        elif actions in (("no-op",), ("read",)):
            out["noop"].append(addr)
        else:
            raise EngineFailed("unrecognised action set", details={"address": addr, "actions": list(actions)})
    return {k: sorted(v) for k, v in out.items()}


class TerraformRunner:
    def __init__(self, binary: str | os.PathLike[str] | None, *, expected_sha256: str | None, version: str,
                 plugin_dir: str | os.PathLike[str] | None, sandbox: SandboxPolicy | None = None) -> None:
        if not binary or not expected_sha256:
            raise EngineUnavailable("no approved, pinned engine binary configured")
        if not plugin_dir:
            raise EngineUnavailable("a local plugin directory is required; runtime provider downloads are prohibited")
        self.binary = pathlib.Path(binary)
        if not self.binary.is_file():
            raise EngineUnavailable("engine binary not found", details={"binary": str(binary)})
        verify_artifact(self.binary, expected_sha256=expected_sha256)
        self.version, self.plugin_dir = version, pathlib.Path(plugin_dir)
        self.sandbox = sandbox or SandboxPolicy()

    def command(self, verb: str, workdir: pathlib.Path, extra: list[str] | None = None) -> list[str]:
        base = {
            "init": ["init", "-input=false", "-no-color", "-backend=false", f"-plugin-dir={self.plugin_dir}", "-lockfile=readonly"],
            "plan": ["plan", "-input=false", "-no-color", "-lock=true", "-out=plan.tfplan", "-detailed-exitcode"],
            "show": ["show", "-json", "plan.tfplan"],
            "apply": ["apply", "-input=false", "-no-color", "-auto-approve", "plan.tfplan"],
            "version": ["version", "-json"],
        }
        if verb not in base:
            raise EngineFailed("unsupported engine verb", details={"verb": verb})
        return [str(self.binary), f"-chdir={workdir}", *base[verb], *(extra or [])]

    def run(self, verb: str, workdir: str | os.PathLike[str]) -> dict[str, Any]:
        workdir = pathlib.Path(workdir)
        (workdir / "tmp").mkdir(parents=True, exist_ok=True)
        cmd = self.command(verb, workdir)
        env = sandbox_env(self.sandbox, workdir)
        try:
            cp = subprocess.run(cmd, cwd=workdir, env=env, capture_output=True, timeout=self.sandbox.timeout,
                                preexec_fn=_preexec(self.sandbox), check=False)
        except subprocess.TimeoutExpired as exc:
            raise EngineFailed("engine timed out", details={"verb": verb, "timeout": self.sandbox.timeout}) from exc
        record = {"cmd": cmd, "returncode": cp.returncode, "stdout_bytes": len(cp.stdout), "stderr_tail": cp.stderr[-2000:].decode("utf-8", "replace")}
        ok_codes = {0, 2} if verb == "plan" else {0}
        if cp.returncode not in ok_codes:
            raise EngineFailed("engine command failed", details=record)
        if verb in ("show", "version"):
            record["json"] = json.loads(cp.stdout)
        return record


# --------------------------------------------------------- provider adapters
class Provider(Protocol):
    name: str

    def read(self, resource_id: str) -> Any: ...
    def create(self, resource_id: str, value: Any) -> None: ...
    def update(self, resource_id: str, value: Any) -> None: ...
    def delete(self, resource_id: str) -> None: ...
    def list(self) -> dict[str, Any]: ...


class InMemoryProvider:
    """Conformance reference provider; also used to inject faults in tests."""

    def __init__(self, name: str = "memory", initial: Mapping[str, Any] | None = None) -> None:
        self.name = name
        self._r: dict[str, Any] = json.loads(json.dumps(dict(initial or {})))
        self.fail_on: dict[str, Exception] = {}
        self.calls: list[tuple[str, str]] = []

    def _maybe_fail(self, op: str, rid: str) -> None:
        self.calls.append((op, rid))
        exc = self.fail_on.get(f"{op}:{rid}") or self.fail_on.get(op)
        if exc:
            raise exc

    def read(self, resource_id: str) -> Any:
        self._maybe_fail("read", resource_id)
        return json.loads(json.dumps(self._r.get(resource_id)))

    def create(self, resource_id: str, value: Any) -> None:
        self._maybe_fail("create", resource_id)
        if resource_id in self._r:
            raise ProviderRefused("resource already exists", details={"resource": resource_id})
        self._r[resource_id] = json.loads(json.dumps(value))

    def update(self, resource_id: str, value: Any) -> None:
        self._maybe_fail("update", resource_id)
        if resource_id not in self._r:
            raise ProviderRefused("resource missing", details={"resource": resource_id})
        self._r[resource_id] = json.loads(json.dumps(value))

    def delete(self, resource_id: str) -> None:
        self._maybe_fail("delete", resource_id)
        self._r.pop(resource_id, None)

    def list(self) -> dict[str, Any]:
        return json.loads(json.dumps(self._r))


def execute_plan(plan: Mapping[str, Any], provider: Provider, *, desired: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
    """Drive a provider through a validated plan in graph order.

    Stops at the first provider failure and returns what completed, so the
    caller can reconcile (drift scan) rather than guessing.  State is only
    committed by the caller when every step succeeded.
    """
    from .graph import ordered_plan

    order = ordered_plan(plan, desired, current)
    done: list[tuple[str, str]] = []
    try:
        for rid in order["destroy"]:
            provider.delete(rid)
            done.append(("delete", rid))
        for rid in order["apply"]:
            if rid in plan["create"]:
                provider.create(rid, plan["create"][rid])
                done.append(("create", rid))
            else:
                provider.update(rid, plan["update"][rid])
                done.append(("update", rid))
    except Exception as exc:  # noqa: BLE001
        return {"complete": False, "done": done, "error": {"type": type(exc).__name__, **(exc.as_dict() if isinstance(exc, IacError) else {"message": str(exc)})}}
    return {"complete": True, "done": done, "error": None}


SUPPORTED_PLATFORMS = {("linux", "3.10"), ("linux", "3.11"), ("linux", "3.12"), ("linux", "3.13"),
                       ("win32", "3.11"), ("win32", "3.12"), ("darwin", "3.11"), ("darwin", "3.12")}
VALIDATED_PLATFORMS = {("linux", "3.11")}  # updated only from retained test-farm evidence


def check_platform(*, strict: bool = False) -> dict[str, Any]:
    key = (sys.platform if not sys.platform.startswith("linux") else "linux", f"{sys.version_info.major}.{sys.version_info.minor}")
    status = "validated" if key in VALIDATED_PLATFORMS else "declared" if key in SUPPORTED_PLATFORMS else "unsupported"
    if status == "unsupported" or (strict and status != "validated"):
        raise UnsupportedPlatform("platform/runtime combination not supported", details={"platform": key[0], "python": key[1], "status": status})
    return {"platform": key[0], "python": key[1], "status": status}
