"""Bounded 1-bit communication fabric for the Unikernel Containership.

This module deliberately implements **1-bit communication, not 1-bit cognition**.
Local arithmetic, residual/error-feedback state, scale estimation, monitoring and
collective reduction stay full precision. Only the sign stream on the compressed
wire is one bit per scalar, with an explicit floating-point magnitude sideband.

The implementation is a local containership adaptation of the attached JYRM
1BNCF v3.1.0 series. It is not a claim that JYRM, NCCL, JA21, QAM, FXSpot or a
neural model is present in this repository.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from collections import deque
import hashlib
import json
import math
import statistics
import struct
import time
import zlib
from typing import Deque, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple


class OneBitError(ValueError):
    """Fail-closed validation or state-machine error."""


WIRE_VERSION = 1
ONE_MAGIC = b"UC1B"
FP_MAGIC = b"UCFP"
# magic, version, flags, header-bytes, sequence, source, destination, count, scale, crc32
ONE_HEADER = struct.Struct("<4sBBHQIIIdI")
# magic, version, flags, header-bytes, sequence, source, destination, count, crc32
FP_HEADER = struct.Struct("<4sBBHQIIII")
ONE_HEADER_BYTES = ONE_HEADER.size
FP_HEADER_BYTES = FP_HEADER.size
MAX_SCALARS = 65_536
MAX_PACKET_BYTES = FP_HEADER_BYTES + MAX_SCALARS * 4
TIFF_PACKET_LIMIT = 464  # native BRO1 guest payload capacity in the carried hull
MAX_TIFF_ONEBIT_SCALARS = (TIFF_PACKET_LIMIT - ONE_HEADER_BYTES) * 8
MAX_ROUTE_RECIPIENTS = 4096
MAX_CHANNELS = 4096
LSB0 = "lsb0"
SIGN_CONVENTION = "1=nonnegative,0=negative; zero is encoded as 1"
MODES = ("FULL_PRECISION", "WARMUP", "ONE_BIT", "RECOVERY")


def _u(value, bits: int, name: str) -> int:
    if type(value) is not int or not 0 <= value < (1 << bits):
        raise OneBitError(f"{name} must be an unsigned {bits}-bit integer")
    return value


def _finite(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OneBitError(f"{name} must be a finite number")
    x = float(value)
    if not math.isfinite(x):
        raise OneBitError(f"{name} must be a finite number")
    return x


def values(values: Sequence[float], *, allow_empty: bool = False) -> List[float]:
    if not isinstance(values, (list, tuple)):
        raise OneBitError("values must be a list or tuple")
    if len(values) > MAX_SCALARS:
        raise OneBitError("communication block exceeds scalar budget")
    if not values and not allow_empty:
        raise OneBitError("communication block must not be empty")
    return [_finite(v, f"values[{i}]") for i, v in enumerate(values)]


def pack_signs(signs: Sequence[int]) -> bytes:
    if not isinstance(signs, (list, tuple)) or len(signs) > MAX_SCALARS:
        raise OneBitError("invalid sign vector")
    out = bytearray((len(signs) + 7) // 8)
    for i, s in enumerate(signs):
        if type(s) is not int or s not in (0, 1):
            raise OneBitError("sign stream values must be 0 or 1")
        if s:
            out[i >> 3] |= 1 << (i & 7)
    return bytes(out)


def unpack_signs(payload: bytes, count: int) -> List[int]:
    _u(count, 32, "count")
    if count > MAX_SCALARS:
        raise OneBitError("sign count exceeds scalar budget")
    need = (count + 7) // 8
    if not isinstance(payload, (bytes, bytearray, memoryview)) or len(payload) != need:
        raise OneBitError("packed sign payload length mismatch")
    raw = bytes(payload)
    if count and count % 8:
        # LSB-first; unused high bits in the last byte must be canonical zero.
        mask = 0xFF ^ ((1 << (count % 8)) - 1)
        if raw[-1] & mask:
            raise OneBitError("non-zero tail bits in packed sign stream")
    return [1 if raw[i >> 3] & (1 << (i & 7)) else 0 for i in range(count)]


def estimate_scale(block: Sequence[float]) -> float:
    vv = values(block)
    return math.fsum(abs(x) for x in vv) / len(vv)


def sign_quantize(block: Sequence[float], *, scale: Optional[float] = None) -> Dict[str, object]:
    vv = values(block)
    s = estimate_scale(vv) if scale is None else _finite(scale, "scale")
    if s < 0:
        raise OneBitError("scale must be non-negative")
    if s == 0.0 and any(x != 0.0 for x in vv):
        raise OneBitError("zero scale cannot represent a non-zero block")
    signs = [1 if x >= 0.0 else 0 for x in vv]
    reconstructed = [s if bit else -s for bit in signs] if s else [0.0] * len(vv)
    err = [x - y for x, y in zip(vv, reconstructed)]
    signal2 = math.fsum(x * x for x in vv)
    error2 = math.fsum(x * x for x in err)
    nrmse = math.sqrt(error2 / signal2) if signal2 else 0.0
    return {
        "scale": s,
        "signs": signs,
        "payload": pack_signs(signs),
        "reconstructed": reconstructed,
        "residual": err,
        "normalized_rmse": nrmse,
        "bit_balance": math.fsum(signs) / len(signs),
    }


def _crc_packet(header_struct: struct.Struct, parts: Tuple[object, ...], payload: bytes) -> Tuple[bytes, int]:
    header0 = header_struct.pack(*parts, 0)
    crc = zlib.crc32(header0 + payload) & 0xFFFFFFFF
    return header_struct.pack(*parts, crc) + payload, crc


def encode_onebit(block: Sequence[float], *, sequence: int, source: int = 0, destination: int = 0,
                  scale: Optional[float] = None) -> Dict[str, object]:
    vv = values(block)
    sequence = _u(sequence, 64, "sequence")
    source = _u(source, 32, "source")
    destination = _u(destination, 32, "destination")
    q = sign_quantize(vv, scale=scale)
    parts = (ONE_MAGIC, WIRE_VERSION, 0, ONE_HEADER_BYTES, sequence, source, destination, len(vv), float(q["scale"]))
    packet, crc = _crc_packet(ONE_HEADER, parts, q["payload"])
    if len(packet) > MAX_PACKET_BYTES:
        raise OneBitError("1-bit packet exceeds byte budget")
    baseline = FP_HEADER_BYTES + 4 * len(vv)
    return {
        **q,
        "packet": packet,
        "sequence": sequence,
        "source": source,
        "destination": destination,
        "count": len(vv),
        "crc32": crc,
        "wire_bytes": len(packet),
        "header_bytes": ONE_HEADER_BYTES,
        "payload_bytes": len(q["payload"]),
        "fp32_wire_bytes": baseline,
        "compression_ratio_vs_fp32": baseline / len(packet),
        "effective_bits_per_scalar": (len(packet) * 8) / len(vv),
        "packet_sha256": hashlib.sha256(packet).hexdigest(),
    }


def decode_onebit(packet: bytes) -> Dict[str, object]:
    if not isinstance(packet, (bytes, bytearray, memoryview)):
        raise OneBitError("packet must be bytes")
    raw = bytes(packet)
    if not ONE_HEADER_BYTES <= len(raw) <= MAX_PACKET_BYTES:
        raise OneBitError("1-bit packet length outside budget")
    try:
        magic, version, flags, hlen, sequence, source, destination, count, scale, crc = ONE_HEADER.unpack_from(raw)
    except struct.error as exc:
        raise OneBitError("truncated 1-bit header") from exc
    if magic != ONE_MAGIC or version != WIRE_VERSION or flags != 0 or hlen != ONE_HEADER_BYTES:
        raise OneBitError("unsupported 1-bit packet header")
    if count > MAX_SCALARS:
        raise OneBitError("1-bit packet count exceeds scalar budget")
    if not math.isfinite(scale) or scale < 0:
        raise OneBitError("invalid 1-bit scale sideband")
    payload = raw[ONE_HEADER_BYTES:]
    if len(payload) != (count + 7) // 8:
        raise OneBitError("1-bit payload length/count mismatch")
    header0 = ONE_HEADER.pack(magic, version, flags, hlen, sequence, source, destination, count, scale, 0)
    expected = zlib.crc32(header0 + payload) & 0xFFFFFFFF
    if crc != expected:
        raise OneBitError("1-bit packet CRC mismatch")
    signs = unpack_signs(payload, count)
    vals = [scale if bit else -scale for bit in signs] if scale else [0.0] * count
    return {
        "kind": "one_bit",
        "version": version,
        "sequence": sequence,
        "source": source,
        "destination": destination,
        "count": count,
        "scale": scale,
        "signs": signs,
        "values": vals,
        "crc32": crc,
        "wire_bytes": len(raw),
        "payload_bytes": len(payload),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def encode_fp32(block: Sequence[float], *, sequence: int, source: int = 0, destination: int = 0) -> Dict[str, object]:
    vv = values(block)
    sequence = _u(sequence, 64, "sequence")
    source = _u(source, 32, "source")
    destination = _u(destination, 32, "destination")
    try:
        payload = struct.pack("<" + "f" * len(vv), *vv)
    except (OverflowError, struct.error) as exc:
        raise OneBitError("value is outside finite FP32 transport range") from exc
    # Reject conversion to FP32 infinity; local cognition may use wider precision,
    # but the declared full-precision reference wire for this profile is FP32.
    decoded = list(struct.unpack("<" + "f" * len(vv), payload))
    if any(not math.isfinite(x) for x in decoded):
        raise OneBitError("value overflowed the FP32 reference transport")
    parts = (FP_MAGIC, WIRE_VERSION, 0, FP_HEADER_BYTES, sequence, source, destination, len(vv))
    packet, crc = _crc_packet(FP_HEADER, parts, payload)
    if len(packet) > MAX_PACKET_BYTES:
        raise OneBitError("FP32 packet exceeds byte budget")
    return {
        "packet": packet,
        "values": decoded,
        "sequence": sequence,
        "source": source,
        "destination": destination,
        "count": len(vv),
        "crc32": crc,
        "wire_bytes": len(packet),
        "payload_bytes": len(payload),
        "header_bytes": FP_HEADER_BYTES,
        "packet_sha256": hashlib.sha256(packet).hexdigest(),
    }


def decode_fp32(packet: bytes) -> Dict[str, object]:
    if not isinstance(packet, (bytes, bytearray, memoryview)):
        raise OneBitError("packet must be bytes")
    raw = bytes(packet)
    if not FP_HEADER_BYTES <= len(raw) <= MAX_PACKET_BYTES:
        raise OneBitError("FP32 packet length outside budget")
    try:
        magic, version, flags, hlen, sequence, source, destination, count, crc = FP_HEADER.unpack_from(raw)
    except struct.error as exc:
        raise OneBitError("truncated FP32 header") from exc
    if magic != FP_MAGIC or version != WIRE_VERSION or flags != 0 or hlen != FP_HEADER_BYTES:
        raise OneBitError("unsupported FP32 packet header")
    if count > MAX_SCALARS or len(raw) != FP_HEADER_BYTES + count * 4:
        raise OneBitError("FP32 payload length/count mismatch")
    payload = raw[FP_HEADER_BYTES:]
    header0 = FP_HEADER.pack(magic, version, flags, hlen, sequence, source, destination, count, 0)
    if crc != (zlib.crc32(header0 + payload) & 0xFFFFFFFF):
        raise OneBitError("FP32 packet CRC mismatch")
    vals = list(struct.unpack("<" + "f" * count, payload))
    if any(not math.isfinite(x) for x in vals):
        raise OneBitError("non-finite value in FP32 payload")
    return {
        "kind": "fp32", "version": version, "sequence": sequence, "source": source,
        "destination": destination, "count": count, "values": vals, "crc32": crc,
        "wire_bytes": len(raw), "payload_bytes": len(payload), "sha256": hashlib.sha256(raw).hexdigest(),
    }


def decode_packet(packet: bytes) -> Dict[str, object]:
    if not isinstance(packet, (bytes, bytearray, memoryview)) or len(packet) < 4:
        raise OneBitError("truncated packet")
    magic = bytes(packet[:4])
    if magic == ONE_MAGIC:
        return decode_onebit(packet)
    if magic == FP_MAGIC:
        return decode_fp32(packet)
    raise OneBitError("unknown communication packet magic")


@dataclass(frozen=True)
class ControllerConfig:
    warmup_blocks: int = 8
    stability_window: int = 6
    stability_cv: float = 0.08
    recovery_blocks: int = 4
    max_error_ratio: float = 1.25
    min_bit_balance: float = 0.01
    max_bit_balance: float = 0.99
    lower_scale_ratio: float = 0.25
    upper_scale_ratio: float = 4.0
    max_scale_step_ratio: float = 0.50
    momentum_beta: float = 0.90
    residual_enabled: bool = True

    def validate(self) -> "ControllerConfig":
        if type(self.warmup_blocks) is not int or not 2 <= self.warmup_blocks <= 4096:
            raise OneBitError("warmup_blocks must be 2..4096")
        if type(self.stability_window) is not int or not 2 <= self.stability_window <= self.warmup_blocks:
            raise OneBitError("stability_window must be 2..warmup_blocks")
        if type(self.recovery_blocks) is not int or not 1 <= self.recovery_blocks <= 4096:
            raise OneBitError("recovery_blocks must be 1..4096")
        for name in ("stability_cv", "max_error_ratio", "min_bit_balance", "max_bit_balance",
                     "lower_scale_ratio", "upper_scale_ratio", "max_scale_step_ratio", "momentum_beta"):
            _finite(getattr(self, name), name)
        if not 0 <= self.stability_cv <= 1 or not 0 < self.max_error_ratio <= 100:
            raise OneBitError("invalid stability/error thresholds")
        if not 0 <= self.min_bit_balance < self.max_bit_balance <= 1:
            raise OneBitError("invalid bit-balance thresholds")
        if not 0 < self.lower_scale_ratio <= 1 <= self.upper_scale_ratio:
            raise OneBitError("invalid scale bounds")
        if not 0 <= self.max_scale_step_ratio <= 10:
            raise OneBitError("invalid max_scale_step_ratio")
        if not 0 <= self.momentum_beta < 1:
            raise OneBitError("momentum_beta must be in [0,1)")
        return self


@dataclass
class ChannelState:
    sequence: int = 0
    mode: str = "WARMUP"
    residual: List[float] = field(default_factory=list)
    momentum: List[float] = field(default_factory=list)
    warmup_scales: List[float] = field(default_factory=list)
    reference_scale: Optional[float] = None
    last_scale: Optional[float] = None
    recovery_remaining: int = 0
    transitions: List[Dict[str, object]] = field(default_factory=list)
    packets: int = 0
    onebit_packets: int = 0
    full_precision_packets: int = 0
    wire_bytes: int = 0
    logical_scalars: int = 0
    last_metrics: Dict[str, object] = field(default_factory=dict)

    def validate(self) -> "ChannelState":
        _u(self.sequence, 64, "state.sequence")
        if self.mode not in MODES:
            raise OneBitError("invalid controller mode")
        if len(self.residual) > MAX_SCALARS or len(self.momentum) > MAX_SCALARS:
            raise OneBitError("controller state exceeds scalar budget")
        self.residual = values(self.residual, allow_empty=True)
        self.momentum = values(self.momentum, allow_empty=True)
        self.warmup_scales = [_finite(x, "warmup_scale") for x in self.warmup_scales[-4096:]]
        if self.reference_scale is not None and _finite(self.reference_scale, "reference_scale") < 0:
            raise OneBitError("reference scale must be non-negative")
        if self.last_scale is not None and _finite(self.last_scale, "last_scale") < 0:
            raise OneBitError("last scale must be non-negative")
        if type(self.recovery_remaining) is not int or not 0 <= self.recovery_remaining <= 4096:
            raise OneBitError("invalid recovery counter")
        return self


def _cv(seq: Sequence[float]) -> float:
    if not seq:
        return math.inf
    mean = math.fsum(seq) / len(seq)
    if mean == 0:
        return 0.0 if all(x == 0 for x in seq) else math.inf
    var = math.fsum((x - mean) ** 2 for x in seq) / len(seq)
    return math.sqrt(var) / abs(mean)


def _l2_ratio(error: Sequence[float], signal: Sequence[float]) -> float:
    e = math.fsum(x * x for x in error)
    s = math.fsum(x * x for x in signal)
    return math.sqrt(e / s) if s else 0.0


class CommunicationController:
    """Full-precision warmup/recovery plus guarded 1-bit communication.

    A controller is intentionally per logical channel. Receiver-side ordering is
    enforced by ``receive`` when an expected sequence is supplied.
    """

    def __init__(self, config: Optional[ControllerConfig] = None, state: Optional[ChannelState] = None):
        self.config = (config or ControllerConfig()).validate()
        self.state = (state or ChannelState()).validate()

    def _transition(self, mode: str, reason: str) -> None:
        if mode not in MODES:
            raise OneBitError("invalid transition target")
        if self.state.mode != mode:
            self.state.transitions.append({"from": self.state.mode, "to": mode, "sequence": self.state.sequence, "reason": reason})
            self.state.transitions = self.state.transitions[-256:]
            self.state.mode = mode

    def _observe_scale(self, scale: float) -> Tuple[bool, float]:
        s = self.state
        s.warmup_scales.append(scale)
        s.warmup_scales = s.warmup_scales[-self.config.warmup_blocks:]
        w = s.warmup_scales[-self.config.stability_window:]
        cv = _cv(w)
        stable = len(s.warmup_scales) >= self.config.warmup_blocks and len(w) >= self.config.stability_window and cv <= self.config.stability_cv
        return stable, cv

    def _adaptive_scale(self, fresh: float) -> Tuple[float, Dict[str, float]]:
        s, c = self.state, self.config
        ref = s.reference_scale if s.reference_scale is not None else fresh
        if ref == 0.0:
            bounded = 0.0 if fresh == 0.0 else fresh
            ratio = 1.0 if fresh == 0.0 else None
        else:
            lo, hi = ref * c.lower_scale_ratio, ref * c.upper_scale_ratio
            bounded = min(max(fresh, lo), hi)
            ratio = fresh / ref
        if s.last_scale is not None and s.last_scale > 0:
            delta = s.last_scale * c.max_scale_step_ratio
            bounded = min(max(bounded, max(0.0, s.last_scale - delta)), s.last_scale + delta)
        return bounded, {"reference": ref, "fresh": fresh, "fresh_reference_ratio": ratio, "selected": bounded}

    def _prepare_state_vectors(self, count: int) -> None:
        s = self.state
        if s.residual and len(s.residual) != count:
            # A shape change is an explicit reset boundary; stale residuals must not
            # silently cross block geometry.
            s.residual = []
            s.momentum = []
        if not s.residual:
            s.residual = [0.0] * count
        if not s.momentum:
            s.momentum = [0.0] * count

    def transmit(self, block: Sequence[float], *, source: int = 0, destination: int = 0) -> Dict[str, object]:
        vv = values(block)
        s, c = self.state, self.config
        _u(s.sequence, 64, "state.sequence")
        if s.sequence == (1 << 64) - 1:
            raise OneBitError("sequence counter exhausted")
        seq = s.sequence
        fresh_scale = estimate_scale(vv)
        stable, stability_cv = self._observe_scale(fresh_scale)
        self._prepare_state_vectors(len(vv))
        mode_before = s.mode
        fallback_reason = None

        if s.mode in ("FULL_PRECISION", "WARMUP", "RECOVERY"):
            fp = encode_fp32(vv, sequence=seq, source=source, destination=destination)
            result = {**fp, "transport": "fp32", "mode_before": mode_before, "stability_cv": stability_cv,
                      "reference_scale": s.reference_scale, "fallback": False}
            if s.mode == "WARMUP" and stable:
                s.reference_scale = math.fsum(s.warmup_scales) / len(s.warmup_scales)
                s.last_scale = s.reference_scale
                self._transition("ONE_BIT", "warmup scale statistics converged")
            elif s.mode == "RECOVERY":
                s.recovery_remaining = max(0, s.recovery_remaining - 1)
                if s.recovery_remaining == 0 and stable:
                    if s.reference_scale is None:
                        s.reference_scale = math.fsum(s.warmup_scales) / len(s.warmup_scales)
                    self._transition("ONE_BIT", "recovery window completed with stable scale statistics")
            s.full_precision_packets += 1
        elif s.mode == "ONE_BIT":
            adjusted = [x + r for x, r in zip(vv, s.residual)] if c.residual_enabled else list(vv)
            # Momentum remains high precision local state; it is observed/checkpointed,
            # not itself quantized into cognition.
            s.momentum = [c.momentum_beta * m + (1.0 - c.momentum_beta) * x for m, x in zip(s.momentum, adjusted)]
            selected, scale_stats = self._adaptive_scale(estimate_scale(adjusted))
            one = encode_onebit(adjusted, sequence=seq, source=source, destination=destination, scale=selected)
            reconstructed = one["reconstructed"]
            residual = [x - y for x, y in zip(adjusted, reconstructed)]
            error_ratio = _l2_ratio(residual, adjusted)
            balance = float(one["bit_balance"])
            scale_ratio = scale_stats["fresh_reference_ratio"]
            if error_ratio > c.max_error_ratio:
                fallback_reason = "compression error exceeded threshold"
            elif not c.min_bit_balance <= balance <= c.max_bit_balance and any(x != 0 for x in adjusted):
                fallback_reason = "bit-balance saturation exceeded threshold"
            elif scale_ratio is not None and math.isfinite(scale_ratio) and not c.lower_scale_ratio / 2 <= scale_ratio <= c.upper_scale_ratio * 2:
                fallback_reason = "scale drift exceeded emergency bounds"
            if fallback_reason:
                # Fail closed for quality: transmit the original full-precision block.
                fp = encode_fp32(vv, sequence=seq, source=source, destination=destination)
                s.residual = [0.0] * len(vv)
                s.recovery_remaining = c.recovery_blocks
                self._transition("RECOVERY", fallback_reason)
                result = {**fp, "transport": "fp32", "mode_before": mode_before, "stability_cv": stability_cv,
                          "fallback": True, "fallback_reason": fallback_reason, "onebit_probe": {
                              "error_ratio": error_ratio, "bit_balance": balance, **scale_stats,
                              "would_be_wire_bytes": one["wire_bytes"]}}
                s.full_precision_packets += 1
            else:
                s.residual = residual
                s.last_scale = selected
                result = {**one, "transport": "one_bit", "mode_before": mode_before, "stability_cv": stability_cv,
                          "fallback": False, "compression_error_ratio": error_ratio, "scale_stats": scale_stats,
                          "residual_norm": math.sqrt(math.fsum(r * r for r in residual))}
                s.onebit_packets += 1
        else:  # defensive even though ChannelState.validate gates this
            raise OneBitError("unsupported controller mode")

        s.sequence += 1
        s.packets += 1
        s.wire_bytes += int(result["wire_bytes"])
        s.logical_scalars += len(vv)
        result["mode_after"] = s.mode
        result["sequence"] = seq
        result["logical_scalars"] = len(vv)
        result["communication_only_compressed"] = result["transport"] == "one_bit"
        s.last_metrics = {k: v for k, v in result.items() if k not in {"packet", "payload", "values", "reconstructed", "residual", "signs"}}
        return result

    def receive(self, packet: bytes, *, expected_sequence: Optional[int] = None,
                source: Optional[int] = None, destination: Optional[int] = None) -> Dict[str, object]:
        r = decode_packet(packet)
        if expected_sequence is not None and r["sequence"] != _u(expected_sequence, 64, "expected_sequence"):
            raise OneBitError("stale, duplicate or out-of-order sequence")
        if source is not None and r["source"] != _u(source, 32, "source"):
            raise OneBitError("packet source does not match route")
        if destination is not None and r["destination"] != _u(destination, 32, "destination"):
            raise OneBitError("packet destination does not match route")
        return r

    def checkpoint(self) -> Dict[str, object]:
        self.state.validate()
        body = {"schema": "UC/1BIT_CHANNEL/1", "config": asdict(self.config), "state": asdict(self.state)}
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        body["sha256"] = hashlib.sha256(encoded).hexdigest()
        return body

    @classmethod
    def from_checkpoint(cls, record: Mapping[str, object]) -> "CommunicationController":
        if not isinstance(record, Mapping) or record.get("schema") != "UC/1BIT_CHANNEL/1":
            raise OneBitError("unsupported 1-bit checkpoint schema")
        cfg_raw, state_raw = record.get("config"), record.get("state")
        if not isinstance(cfg_raw, Mapping) or not isinstance(state_raw, Mapping):
            raise OneBitError("invalid checkpoint structure")
        body = {"schema": record["schema"], "config": dict(cfg_raw), "state": dict(state_raw)}
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        if record.get("sha256") != hashlib.sha256(encoded).hexdigest():
            raise OneBitError("1-bit checkpoint digest mismatch")
        try:
            cfg = ControllerConfig(**dict(cfg_raw)).validate()
            state = ChannelState(**dict(state_raw)).validate()
        except TypeError as exc:
            raise OneBitError("unknown or missing checkpoint fields") from exc
        return cls(cfg, state)

    def metrics(self) -> Dict[str, object]:
        s = self.state
        return {
            "mode": s.mode, "sequence": s.sequence, "packets": s.packets,
            "onebit_packets": s.onebit_packets, "full_precision_packets": s.full_precision_packets,
            "wire_bytes": s.wire_bytes, "logical_scalars": s.logical_scalars,
            "effective_bits_per_scalar": (s.wire_bytes * 8 / s.logical_scalars) if s.logical_scalars else None,
            "reference_scale": s.reference_scale, "last_scale": s.last_scale,
            "residual_bytes_estimate": len(s.residual) * 8,
            "momentum_bytes_estimate": len(s.momentum) * 8,
            "transitions": list(s.transitions), "last": dict(s.last_metrics),
        }


class RouteTable:
    def __init__(self, routes: Optional[Mapping[int, Sequence[int]]] = None):
        self._routes: Dict[int, Tuple[int, ...]] = {}
        for source, recipients in (routes or {}).items():
            self.set(source, recipients)

    def set(self, source: int, recipients: Sequence[int]) -> None:
        src = _u(source, 32, "source")
        if not isinstance(recipients, (list, tuple)) or len(recipients) > MAX_ROUTE_RECIPIENTS:
            raise OneBitError("invalid recipient map")
        rr = tuple(_u(x, 32, "recipient") for x in recipients)
        if len(rr) != len(set(rr)):
            raise OneBitError("recipient map contains duplicates")
        self._routes[src] = rr

    def recipients(self, source: int) -> Tuple[int, ...]:
        return self._routes.get(_u(source, 32, "source"), ())

    def as_dict(self) -> Dict[str, List[int]]:
        return {str(k): list(v) for k, v in sorted(self._routes.items())}


class MemoryBackend:
    """Bounded local queue backend; a backend abstraction, not network transport."""
    def __init__(self, byte_budget: int = 4 * 1024 * 1024):
        if type(byte_budget) is not int or not 1024 <= byte_budget <= 64 * 1024 * 1024:
            raise OneBitError("memory backend budget must be 1 KiB..64 MiB")
        self.byte_budget = byte_budget
        self.bytes = 0
        self.queues: Dict[int, Deque[bytes]] = {}

    def send(self, destination: int, packet: bytes) -> None:
        dst = _u(destination, 32, "destination")
        raw = bytes(packet)
        decode_packet(raw)  # integrity before enqueue
        if self.bytes + len(raw) > self.byte_budget:
            raise OneBitError("memory backend backpressure: byte budget exceeded")
        self.queues.setdefault(dst, deque()).append(raw)
        self.bytes += len(raw)

    def receive(self, destination: int) -> bytes:
        dst = _u(destination, 32, "destination")
        q = self.queues.get(dst)
        if not q:
            raise OneBitError("no packet available for destination")
        raw = q.popleft(); self.bytes -= len(raw)
        return raw


def average_reduce(blocks: Sequence[Sequence[float]]) -> List[float]:
    if not isinstance(blocks, (list, tuple)) or not blocks:
        raise OneBitError("reduce requires at least one block")
    vv = [values(b) for b in blocks]
    n = len(vv[0])
    if any(len(b) != n for b in vv):
        raise OneBitError("collective block sizes differ")
    # Full precision local compute after communication reconstruction.
    return [math.fsum(b[i] for b in vv) / len(vv) for i in range(n)]


def compressed_average(blocks: Sequence[Sequence[float]], *, sequence: int = 0) -> Dict[str, object]:
    vv = [values(b) for b in blocks]
    packets, reconstructed, wire = [], [], 0
    for i, b in enumerate(vv):
        r = encode_onebit(b, sequence=sequence, source=i, destination=0)
        packets.append(r["packet"]); reconstructed.append(decode_onebit(r["packet"])["values"]); wire += r["wire_bytes"]
    full = average_reduce(vv); approx = average_reduce(reconstructed)
    err = [a - b for a, b in zip(full, approx)]
    return {
        "packets": packets, "full_precision_reduce": full, "compressed_reduce": approx,
        "normalized_error": _l2_ratio(err, full), "wire_bytes": wire,
        "fp32_wire_bytes": sum(FP_HEADER_BYTES + 4 * len(b) for b in vv),
    }


def ab_compare(block: Sequence[float], *, sequence: int = 0, source: int = 0, destination: int = 0) -> Dict[str, object]:
    vv = values(block)
    fp = encode_fp32(vv, sequence=sequence, source=source, destination=destination)
    one = encode_onebit(vv, sequence=sequence, source=source, destination=destination)
    fpv = decode_fp32(fp["packet"])["values"]
    onev = decode_onebit(one["packet"])["values"]
    delta = [a - b for a, b in zip(fpv, onev)]
    return {
        "count": len(vv), "fp32_wire_bytes": fp["wire_bytes"], "onebit_wire_bytes": one["wire_bytes"],
        "compression_ratio": fp["wire_bytes"] / one["wire_bytes"],
        "effective_bits_per_scalar": one["wire_bytes"] * 8 / len(vv),
        "normalized_reconstruction_error": _l2_ratio(delta, fpv),
        "fp32_sha256": fp["packet_sha256"], "onebit_sha256": one["packet_sha256"],
        "sign_convention": SIGN_CONVENTION, "bit_order": LSB0,
    }


def benchmark(block: Sequence[float], *, rounds: int = 100) -> Dict[str, object]:
    vv = values(block)
    if type(rounds) is not int or not 1 <= rounds <= 10000:
        raise OneBitError("benchmark rounds must be 1..10000")
    t0 = time.perf_counter_ns(); wire = 0
    for i in range(rounds):
        wire += len(encode_onebit(vv, sequence=i)["packet"])
    t1 = time.perf_counter_ns()
    elapsed = max(1, t1 - t0)
    return {
        "rounds": rounds, "scalars_per_round": len(vv), "elapsed_ns": elapsed,
        "mean_encode_ns": elapsed / rounds,
        "scalars_per_second": (rounds * len(vv)) / (elapsed / 1e9),
        "wire_bytes_total": wire,
        "note": "single-process Python microbenchmark; not a service-level or SIMD/GPU claim",
    }


def replay(blocks: Sequence[Sequence[float]], *, config: Optional[ControllerConfig] = None) -> Dict[str, object]:
    """Run the same deterministic sequence twice and compare wire hashes/state hashes."""
    if not isinstance(blocks, (list, tuple)) or not blocks or len(blocks) > 4096:
        raise OneBitError("replay requires 1..4096 blocks")
    checked = [values(b) for b in blocks]
    def run_once():
        ctl = CommunicationController(config)
        packets=[]
        for b in checked:
            r=ctl.transmit(b)
            packets.append(hashlib.sha256(r["packet"]).hexdigest())
        cp=ctl.checkpoint()
        return packets, cp["sha256"], ctl.metrics()
    a=run_once(); b=run_once()
    return {"packet_hashes_equal":a[0]==b[0], "state_hashes_equal":a[1]==b[1],
            "packet_hashes":a[0], "checkpoint_sha256":a[1], "metrics":a[2],
            "deterministic":a[0]==b[0] and a[1]==b[1]}


def capability_record() -> Dict[str, object]:
    return {
        "schema": "UC/1BIT_CAPABILITIES/1",
        "wire_version": WIRE_VERSION,
        "rule": "1-bit communication, not 1-bit cognition",
        "sign_convention": SIGN_CONVENTION,
        "bit_order": LSB0,
        "onebit_header_bytes": ONE_HEADER_BYTES,
        "fp32_header_bytes": FP_HEADER_BYTES,
        "max_scalars": MAX_SCALARS,
        "tiff_native_payload_bytes": TIFF_PACKET_LIMIT,
        "max_onebit_scalars_per_tiff_tile": MAX_TIFF_ONEBIT_SCALARS,
        "compression": "sign payload + FP64 scale sideband; local residual/momentum remain full precision",
        "integrity": "CRC32 per packet plus SHA-256 evidence hashes",
        "local_backends": ["memory"],
        "network": "not implemented; containership NETWORK=deny remains unchanged",
        "gpu": "not implemented",
        "external_adapters": "JYRM/NCCL/JA21/QAM/FXSpot/Junkyard adapters are not claimed",
    }
