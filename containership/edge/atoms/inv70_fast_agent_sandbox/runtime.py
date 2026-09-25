"""Hardened bounded runtime for INV-70 - Fast agent sandbox.

This module intentionally has no dependency on ``pk_core`` so the execution
primitive can be tested in isolation.  It is a small deterministic stack
machine; it is *not* a native-code or Python-object sandbox.
"""
from __future__ import annotations

from collections.abc import Mapping
import math

DEFAULT_FUEL = 1_000
DEFAULT_MAX_STACK = 64
DEFAULT_MAX_MEMORY_BYTES = 64 * 1024
DEFAULT_MAX_VALUE_BYTES = 16 * 1024
DEFAULT_MAX_PROGRAM_INSTRUCTIONS = 4_096
MAX_CAPABILITY_NAME_LENGTH = 128
MAX_CAPABILITIES = 256
_CELL_OVERHEAD_BYTES = 16
_SAFE_SCALAR_TYPES = (type(None), bool, int, float, str, bytes)


class Trap(Exception):
    """Internal control-flow exception converted to a deterministic result."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class _ProgramError(ValueError):
    """Raised internally when bytecode shape or operands are invalid."""


def _is_non_negative_int(value: object) -> bool:
    return type(value) is int and value >= 0


def _is_safe_scalar(value: object) -> bool:
    # Exact-type checks deliberately reject subclasses whose magic methods can
    # execute arbitrary Python during arithmetic/comparison.
    return type(value) in _SAFE_SCALAR_TYPES


def _value_cost(value: object) -> int:
    """Return a deterministic conservative logical guest-memory charge."""
    t = type(value)
    if t is type(None):
        payload = 0
    elif t is bool:
        payload = 1
    elif t is int:
        payload = max(1, (value.bit_length() + 8) // 8)
    elif t is float:
        payload = 8
    elif t is str:
        # Four bytes/code point is a safe UTF-32 upper bound without allocating
        # an encoded copy of attacker-controlled text.
        payload = 4 * len(value)
    elif t is bytes:
        payload = len(value)
    else:  # pragma: no cover - guarded by _is_safe_scalar
        raise _ProgramError("invalid value")
    return _CELL_OVERHEAD_BYTES + payload


def _validate_value(value: object, max_value_bytes: int) -> None:
    if not _is_safe_scalar(value):
        raise Trap("invalid value")
    if type(value) is float and not math.isfinite(value):
        raise Trap("invalid value")
    if _value_cost(value) - _CELL_OVERHEAD_BYTES > max_value_bytes:
        raise Trap("value too large")


def _valid_capability_name(name: object) -> bool:
    if type(name) is not str or not 1 <= len(name) <= MAX_CAPABILITY_NAME_LENGTH:
        return False
    allowed = "._:/-"
    return all(ch.isascii() and (ch.isalnum() or ch in allowed) for ch in name)


def _canonicalize_program(program: object, max_program_instructions: int) -> tuple[tuple[object, ...], ...]:
    if type(program) not in (list, tuple):
        raise _ProgramError("invalid program")
    if len(program) > max_program_instructions:
        raise _ProgramError("program too large")

    expected_arity = {
        "push": 1,
        "add": 0,
        "mul": 0,
        "dup": 0,
        "jmp": 1,
        "jz": 1,
        "call": 1,
        "halt": 0,
    }
    out: list[tuple[object, ...]] = []
    program_len = len(program)
    for raw in program:
        if type(raw) not in (list, tuple) or not raw or type(raw[0]) is not str:
            raise _ProgramError("invalid instruction")
        inst = tuple(raw)
        op = inst[0]
        if op not in expected_arity or len(inst) != expected_arity[op] + 1:
            raise _ProgramError("invalid instruction")
        if op == "push" and not _is_safe_scalar(inst[1]):
            raise _ProgramError("invalid value")
        if op in ("jmp", "jz"):
            target = inst[1]
            if type(target) is not int or not 0 <= target < program_len:
                raise _ProgramError("invalid jump target")
        if op == "call" and not _valid_capability_name(inst[1]):
            raise _ProgramError("invalid capability")
        out.append(inst)
    return tuple(out)


def validate_program(program: object, *, max_program_instructions: int = DEFAULT_MAX_PROGRAM_INSTRUCTIONS) -> tuple[tuple[object, ...], ...]:
    """Validate and snapshot a program, returning immutable canonical bytecode.

    ``ValueError`` is raised for malformed bytecode/configuration. Runtime
    resource failures are reported by :func:`run` as deterministic traps.
    """
    if not _is_non_negative_int(max_program_instructions):
        raise ValueError("max_program_instructions must be a non-negative integer")
    try:
        return _canonicalize_program(program, max_program_instructions)
    except _ProgramError as exc:
        raise ValueError(str(exc)) from None


def _binary_result(op: str, left: object, right: object, max_value_bytes: int) -> object:
    """Evaluate the small set of explicitly safe arithmetic/transform forms."""
    lt, rt = type(left), type(right)
    numeric = (int, float)

    if op == "add":
        if lt in numeric and rt in numeric:
            if lt is int and rt is int:
                predicted_bits = max(left.bit_length(), right.bit_length()) + 1
                if predicted_bits > max_value_bytes * 8:
                    raise Trap("value too large")
            try:
                result = left + right
            except (ArithmeticError, OverflowError):
                raise Trap("arithmetic error") from None
        elif lt is str and rt is str:
            if (len(left) + len(right)) * 4 > max_value_bytes:
                raise Trap("value too large")
            result = left + right
        elif lt is bytes and rt is bytes:
            if len(left) + len(right) > max_value_bytes:
                raise Trap("value too large")
            result = left + right
        else:
            raise Trap("type error")
    else:  # mul
        if lt in numeric and rt in numeric:
            if lt is int and rt is int and left and right:
                predicted_bits = left.bit_length() + right.bit_length()
                if predicted_bits > max_value_bytes * 8:
                    raise Trap("value too large")
            try:
                result = left * right
            except (ArithmeticError, OverflowError):
                raise Trap("arithmetic error") from None
        elif lt in (str, bytes) and rt is int:
            if right < 0:
                repeat = 0
            else:
                repeat = right
            unit = (4 * len(left)) if lt is str else len(left)
            if unit and repeat > max_value_bytes // unit:
                raise Trap("value too large")
            result = left * repeat
        elif lt is int and rt in (str, bytes):
            if left < 0:
                repeat = 0
            else:
                repeat = left
            unit = (4 * len(right)) if rt is str else len(right)
            if unit and repeat > max_value_bytes // unit:
                raise Trap("value too large")
            result = left * repeat
        else:
            raise Trap("type error")

    _validate_value(result, max_value_bytes)
    if type(result) is float and not math.isfinite(result):
        # Non-finite floats are not memory-unsafe, but rejecting results avoids
        # platform/library-specific downstream semantics for NaN/Infinity.
        raise Trap("arithmetic error")
    return result


def run(
    program,
    fuel: int = DEFAULT_FUEL,
    max_stack: int = DEFAULT_MAX_STACK,
    caps=frozenset(),
    host: Mapping[str, object] | None = None,
    *,
    max_memory_bytes: int = DEFAULT_MAX_MEMORY_BYTES,
    max_value_bytes: int = DEFAULT_MAX_VALUE_BYTES,
    max_program_instructions: int = DEFAULT_MAX_PROGRAM_INSTRUCTIONS,
):
    """Execute bounded bytecode and return ``{"ok": ...}`` or ``{"trap": ...}``.

    Backward-compatible positional parameters remain ``program``, ``fuel``,
    ``max_stack``, ``caps`` and ``host``.  New hard limits are keyword-only.

    The VM accepts only inert scalar guest values (None/bool/int/float/str/bytes)
    and exact list/tuple instruction containers.  This blocks Python magic-method
    execution through guest operands.  Host callbacks are trusted capabilities;
    this function gates and bounds their inputs/results but cannot pre-empt a
    callback that itself blocks forever.
    """
    limits = {
        "fuel": fuel,
        "max_stack": max_stack,
        "max_memory_bytes": max_memory_bytes,
        "max_value_bytes": max_value_bytes,
        "max_program_instructions": max_program_instructions,
    }
    bad = [name for name, value in limits.items() if not _is_non_negative_int(value)]
    if bad:
        raise ValueError(f"{', '.join(bad)} must be non-negative integers")
    if max_value_bytes > max_memory_bytes:
        raise ValueError("max_value_bytes cannot exceed max_memory_bytes")

    try:
        code = _canonicalize_program(program, max_program_instructions)
    except _ProgramError as exc:
        return {"trap": str(exc), "fuel": 0}

    if type(caps) is str:
        raise ValueError("caps must be a collection of capability names, not a string")
    try:
        capset = frozenset(caps)
    except TypeError:
        raise ValueError("caps must be an iterable of capability names") from None
    if len(capset) > MAX_CAPABILITIES:
        raise ValueError(f"caps cannot contain more than {MAX_CAPABILITIES} names")
    if any(not _valid_capability_name(name) for name in capset):
        raise ValueError("caps contain an invalid capability name")
    if host is None:
        host = {}
    if not isinstance(host, Mapping):
        raise ValueError("host must be a mapping of capability names to callables")

    stack: list[object] = []
    memory_used = 0
    pc = 0
    used = 0

    def push(value: object) -> None:
        nonlocal memory_used
        _validate_value(value, max_value_bytes)
        if len(stack) >= max_stack:
            raise Trap("out of memory")
        charge = _value_cost(value)
        if memory_used + charge > max_memory_bytes:
            raise Trap("out of memory")
        stack.append(value)
        memory_used += charge

    def pop() -> object:
        nonlocal memory_used
        if not stack:
            raise Trap("stack underflow")
        value = stack.pop()
        memory_used -= _value_cost(value)
        return value

    try:
        while True:
            if used >= fuel:
                raise Trap("out of fuel")
            used += 1
            if not 0 <= pc < len(code):
                raise Trap("pc out of range")

            inst = code[pc]
            op = inst[0]
            pc += 1

            if op == "push":
                push(inst[1])
            elif op in ("add", "mul"):
                right = pop()
                left = pop()
                push(_binary_result(op, left, right, max_value_bytes))
            elif op == "dup":
                if not stack:
                    raise Trap("stack underflow")
                push(stack[-1])
            elif op == "jmp":
                pc = inst[1]
            elif op == "jz":
                value = pop()
                if value in (0, 0.0, False, None):
                    pc = inst[1]
            elif op == "call":
                name = inst[1]
                if name not in capset:
                    raise Trap(f"capability denied: {name}")
                try:
                    callback = host.get(name)
                except Exception as exc:
                    raise Trap(f"host lookup error: {type(exc).__name__}") from None
                if callback is None:
                    raise Trap(f"capability unbound: {name}")
                if not callable(callback):
                    raise Trap(f"capability invalid: {name}")
                argument = pop()
                try:
                    result = callback(argument)
                except Exception as exc:
                    # Do not leak exception messages (which can contain secrets).
                    raise Trap(f"host error: {type(exc).__name__}") from None
                push(result)
            elif op == "halt":
                return {"ok": stack[-1] if stack else None, "fuel": used}
            else:  # pragma: no cover - canonicalizer makes this unreachable
                raise Trap("invalid instruction")
    except Trap as exc:
        return {"trap": exc.reason, "fuel": used}
