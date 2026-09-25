"""Thread-safe one-shot completion state machine for INV-18.

This module deliberately has no dependency on ``pk_core`` so the primitive can be
unit-tested in isolation.  Integration/audit glue remains in :mod:`component`.

States (INV18-FR-001..012, see REQUIREMENTS.json)::

    PENDING --resolve--------> VALUE     --take--> TAKEN
    PENDING --resolve_error--> ERROR     --take--> TAKEN
    PENDING --abandon--------> ABANDONED --take--> TAKEN (raises Abandoned)
    PENDING --cancel---------> CANCELLED --take--> TAKEN (raises Cancelled)

Terminal states never revert.  Every transition runs under one per-future lock,
which also provides the happens-before edge between the resolving thread and the
receiving thread (a value written before ``resolve`` returns is visible to the
receiver that observes it).
"""
from __future__ import annotations

import threading
from typing import Callable, Generic, TypeVar, cast

try:  # package import
    from .errors import FutureError
except ImportError:  # standalone load by file path (tests/test_future.py)
    import importlib.util as _ilu
    import pathlib as _pl
    import sys as _sys
    _name = "inv18_errors_standalone"
    if _name in _sys.modules:
        FutureError = _sys.modules[_name].FutureError
    else:
        _spec = _ilu.spec_from_file_location(_name, _pl.Path(__file__).with_name("errors.py"))
        _mod = _ilu.module_from_spec(_spec)
        _sys.modules[_name] = _mod
        _spec.loader.exec_module(_mod)  # type: ignore[union-attr]
        FutureError = _mod.FutureError

T = TypeVar("T")
_UNSET = object()

PENDING = "PENDING"
VALUE = "VALUE"
ERROR = "ERROR"
ABANDONED = "ABANDONED"
CANCELLED = "CANCELLED"
TERMINAL_STATES = (VALUE, ERROR, ABANDONED, CANCELLED)

MAX_ERROR_MESSAGE = 4096


class AlreadyResolved(FutureError):
    """Raised on a second resolution of the same future."""
    code = "FUTURE_ALREADY_RESOLVED"


class AlreadyTaken(FutureError):
    """Raised when a second receiver tries to take the value."""
    code = "FUTURE_ALREADY_TAKEN"


class Abandoned(FutureError):
    """Raised when the writer was dropped without resolving."""
    code = "FUTURE_ABANDONED"


class Cancelled(FutureError):
    """Raised when the receiver cancelled before resolution."""
    code = "FUTURE_CANCELLED"


class Future(Generic[T]):
    """A typed, thread-safe, one-shot completion.

    ``take()`` returns ``None`` while pending, raises :class:`Abandoned` /
    :class:`Cancelled` for those terminal states, or returns a tagged
    ``("ok", value)`` / ``("error", message)`` exactly once after resolution.
    ``wait(timeout)`` blocks until a terminal state; the timeout belongs to the
    caller and never changes the future's state.
    """

    __slots__ = ("value_type", "_value", "_error", "_taken", "_state", "_cond",
                 "_observer", "__weakref__")

    def __init__(self, value_type: type[T], *, observer: Callable[[str, "Future"], None] | None = None):
        if not isinstance(value_type, type):
            raise TypeError("value_type must be a type")
        self.value_type = value_type
        self._value: object = _UNSET
        self._error: str | None = None
        self._taken = False
        self._state = PENDING
        self._cond = threading.Condition(threading.Lock())
        self._observer = observer

    # -- introspection -------------------------------------------------
    @property
    def state(self) -> str:
        with self._cond:
            return self._state

    @property
    def resolved(self) -> bool:
        with self._cond:
            return self._state in (VALUE, ERROR)

    @property
    def taken(self) -> bool:
        with self._cond:
            return self._taken

    @property
    def abandoned(self) -> bool:
        with self._cond:
            return self._state == ABANDONED

    @property
    def cancelled(self) -> bool:
        with self._cond:
            return self._state == CANCELLED

    def _notify(self, event: str) -> None:
        obs = self._observer
        if obs is not None:
            try:
                obs(event, self)
            except Exception:  # observability must never break correctness (C056)
                pass

    def _check_writable(self) -> None:
        if self._state == PENDING:
            return
        if self._state == CANCELLED:
            raise Cancelled("future cancelled by its receiver")
        if self._state == ABANDONED:
            raise AlreadyResolved("future already abandoned")
        raise AlreadyResolved("future already resolved")

    # -- writer side ---------------------------------------------------
    def resolve(self, value: T) -> None:
        """Resolve successfully exactly once."""
        with self._cond:
            self._check_writable()            # state errors take precedence
            if not isinstance(value, self.value_type) or (
                isinstance(value, bool) and self.value_type is not bool
            ):
                raise TypeError(
                    f"{type(value).__name__} for a future of {self.value_type.__name__}"
                )
            self._value = value
            self._state = VALUE
            self._cond.notify_all()
        self._notify("resolve")

    def resolve_error(self, error: str) -> None:
        """Resolve with a non-empty error message exactly once."""
        with self._cond:
            self._check_writable()
            if not isinstance(error, str) or not error:
                raise TypeError(f"an error resolution needs a non-empty message, got {error!r}")
            if len(error) > MAX_ERROR_MESSAGE:
                raise ValueError(f"error message longer than {MAX_ERROR_MESSAGE} characters")
            self._error = error
            self._state = ERROR
            self._cond.notify_all()
        self._notify("resolve_error")

    def abandon(self) -> bool:
        """Mark an unresolved future abandoned; returns True if this call did it.

        Abandoning a resolved/cancelled future is a harmless no-op because the
        writer's obligation is already settled.  Repeated abandonment is idempotent.
        """
        with self._cond:
            if self._state != PENDING:
                return False
            self._state = ABANDONED
            self._cond.notify_all()
        self._notify("abandon")
        return True

    # -- receiver side -------------------------------------------------
    def cancel(self) -> bool:
        """Receiver gives up before resolution; returns True if this call did it.

        Cancellation differs from abandonment: it is initiated by the receiver,
        not caused by the writer disappearing.  A later resolve raises
        :class:`Cancelled` so the producer learns to stop.
        """
        with self._cond:
            if self._state != PENDING or self._taken:
                return False
            self._state = CANCELLED
            self._taken = True        # the receiver has consumed its ownership
            self._cond.notify_all()
        self._notify("cancel")
        return True

    def wait(self, timeout: float | None = None) -> bool:
        """Block until terminal; True if terminal, False on caller timeout."""
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must be >= 0")
        with self._cond:
            return self._cond.wait_for(lambda: self._state != PENDING, timeout)

    def take(self) -> tuple[str, T | str] | None:
        """Consume the resolved outcome at most once."""
        with self._cond:
            if self._taken:
                raise AlreadyTaken("future already taken by its receiver")
            if self._state == PENDING:
                return None
            self._taken = True
            state = self._state
            if state == ABANDONED:
                result = None
            elif state == ERROR:
                result = ("error", cast(str, self._error))
            else:
                result = ("ok", cast(T, self._value))
            # release payload references once consumed (memory reclamation, C067)
            self._value = _UNSET
            self._error = None
        self._notify("take")
        if state == ABANDONED:
            raise Abandoned("writer dropped without resolving")
        return result
