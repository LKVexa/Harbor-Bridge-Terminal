"""Trusted time with reboot-safe anti-rollback (GAP04-C02).

Time is integer seconds from a *trusted source* (signed time token from the
control plane, NTS, Roughtime, or a secure RTC) extrapolated with the process
monotonic clock between anchors. A persisted high-water mark (HWM) makes time
non-decreasing across restarts, VM snapshot restore, and RTC tampering:

* source < HWM - tolerance            -> rollback detected, fail closed (E0300)
* |source - extrapolated| > max_drift -> jump/spoof suspected, fail closed
* after reboot with no trusted anchor -> fail closed (default) or, if the
  operator enabled ``allow_rtc_after_reboot``, accept an RTC reading >= HWM at
  reduced confidence (the node caps authority at the ``freeze`` tier).
* HWM is persisted at most every ``persist_interval`` seconds; on restart the
  HWM is advanced by that interval so a crash can never rewind time.
"""
from __future__ import annotations

import secrets
import time as _time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from . import canonical, crypto
from .errors import TrustedTimeError
from .trust import TrustStore

TIME_TOKEN_VERSION = "PK_TIME_TOKEN/1"


@dataclass
class TrustedClock:
    hwm: int = 0
    tolerance_s: int = 2
    max_drift_s: int = 30
    persist_interval_s: int = 10
    allow_rtc_after_reboot: bool = False
    monotonic: Callable[[], float] = _time.monotonic
    rtc: Callable[[], int] = lambda: int(_time.time())
    on_persist: Callable[[int], None] = lambda t: None
    _anchor: tuple[int, float] | None = field(default=None, init=False)
    _persisted: int = field(default=0, init=False)
    _pending_nonce: str | None = field(default=None, init=False)
    confidence: str = field(default="none", init=False)

    @classmethod
    def restored(cls, persisted_hwm: int, **kw) -> "TrustedClock":
        c = cls(**kw)
        c.hwm = persisted_hwm + c.persist_interval_s  # crash may have lost up to one interval
        c._persisted = persisted_hwm
        return c

    # -- anchoring ---------------------------------------------------------
    def _accept(self, t: int, conf: str) -> int:
        if t < self.hwm - self.tolerance_s:
            raise TrustedTimeError("trusted time rollback detected", details={"source": t, "hwm": self.hwm})
        if self._anchor is not None:
            est = self._extrapolate()
            if abs(t - est) > self.max_drift_s:
                raise TrustedTimeError("time source jump exceeds drift bound", details={"source": t, "estimate": est})
        t = max(t, self.hwm)
        self._anchor = (t, self.monotonic())
        self.confidence = conf
        self._advance(t)
        return t

    def anchor_trusted(self, t: int) -> int:
        """Anchor from an already-authenticated source (NTS/Roughtime adapter)."""
        return self._accept(int(t), "trusted")

    def challenge(self) -> str:
        self._pending_nonce = secrets.token_hex(16)
        return self._pending_nonce

    def anchor_signed(self, token: Mapping[str, Any], trust: TrustStore) -> int:
        """Anchor from a control-plane signed time token bound to our challenge nonce."""
        if self._pending_nonce is None or token.get("nonce") != self._pending_nonce:
            raise TrustedTimeError("time token nonce mismatch / replay")
        if token.get("version") != TIME_TOKEN_VERSION:
            raise TrustedTimeError("unsupported time token version")
        t = token.get("time")
        if not isinstance(t, int) or isinstance(t, bool):
            raise TrustedTimeError("time token malformed")
        try:
            key = trust.resolve(token["key_id"], token["issuer"], token["alg"], "time", t)
        except Exception as e:
            raise TrustedTimeError(f"time token signer untrusted: {e}") from None
        body = {k: v for k, v in token.items() if k != "sig"}
        if not crypto.verify(key.public_key, canonical.dumps(body), token.get("sig", "")):
            raise TrustedTimeError("time token signature invalid")
        self._pending_nonce = None
        return self._accept(t, "trusted")

    def anchor_rtc(self) -> int:
        if not self.allow_rtc_after_reboot:
            raise TrustedTimeError("no trusted time anchor since boot and RTC fallback disabled")
        return self._accept(int(self.rtc()), "rtc")

    # -- reading -----------------------------------------------------------
    def _extrapolate(self) -> int:
        t0, m0 = self._anchor  # type: ignore[misc]
        dm = self.monotonic() - m0
        if dm < 0:
            raise TrustedTimeError("monotonic clock went backwards")
        return t0 + int(dm)

    def _advance(self, t: int) -> None:
        if t > self.hwm:
            self.hwm = t
        if self.hwm - self._persisted >= self.persist_interval_s or self._persisted == 0:
            self.on_persist(self.hwm)
            self._persisted = self.hwm

    def now(self) -> int:
        if self._anchor is None:
            raise TrustedTimeError("trusted time not anchored")
        t = max(self._extrapolate(), self.hwm)
        self._advance(t)
        return t

    def status(self) -> dict:
        return {"anchored": self._anchor is not None, "confidence": self.confidence, "hwm": self.hwm}


def sign_time_token(t: int, nonce: str, issuer: str, key_id: str, seed: bytes) -> dict:
    body = {"version": TIME_TOKEN_VERSION, "time": t, "nonce": nonce, "issuer": issuer, "key_id": key_id, "alg": "Ed25519"}
    return dict(body, sig=crypto.sign(seed, canonical.dumps(body)))
