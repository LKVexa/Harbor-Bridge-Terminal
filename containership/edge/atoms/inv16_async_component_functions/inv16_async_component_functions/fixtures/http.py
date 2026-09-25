"""SURROGATE INV-20 HTTP world: request lifecycle mapped onto INV-16 call lifecycle."""
from __future__ import annotations

from ..runtime import (AlreadyTerminal, AsyncFunctions, CallCancelled, CallTrapped, CancelCode,
                       CancelReason, ConcurrencyLimitReached, ReentrancyRefused)

SURROGATE = True
INV20_FIXTURE_VERSION = "surrogate-1"

STATUS_MAP = {  # error/status mapping spec
    "completed": 200, "ReentrancyRefused": 429, "ConcurrencyLimitReached": 503,
    "deadline": 504, "disconnect": 499, "trapped": 500,
}


class ResponseAlreadySent(RuntimeError):
    pass


class Response:
    def __init__(self):
        self.status: int | None = None
        self.body: object = None
        self.writes = 0

    def send(self, status: int, body=None):
        if self.status is not None:
            raise ResponseAlreadySent("second terminal response")
        self.status, self.body = status, body
        self.writes += 1


class HttpWorld:
    def __init__(self, fns: AsyncFunctions):
        self.fns = fns

    def accept(self, handler: str, traceparent: str | None = None):
        resp = Response()
        try:
            call = self.fns.invoke(handler, traceparent=traceparent)
        except ReentrancyRefused:
            resp.send(STATUS_MAP["ReentrancyRefused"])
            return None, resp
        except ConcurrencyLimitReached:
            resp.send(STATUS_MAP["ConcurrencyLimitReached"])
            return None, resp
        self.fns.add_terminal_listener(call.call_id, lambda cid, o, v, r: self._finish(resp, o, v, r))
        return call, resp

    def _finish(self, resp: Response, outcome, value, reason):
        if resp.status is not None:
            return
        if outcome.value == "completed":
            resp.send(200, value)
        elif outcome.value == "trapped":
            resp.send(500)
        else:
            code = reason.code.value if reason else "disconnect"
            resp.send(STATUS_MAP.get(code, 499))

    def disconnect(self, call):
        try:
            self.fns.cancel(call.call_id, CancelReason(CancelCode.DISCONNECT, "", "http"))
        except AlreadyTerminal:
            pass

    def deadline(self, call):
        try:
            self.fns.cancel(call.call_id, CancelReason(CancelCode.DEADLINE, "", "http"))
        except AlreadyTerminal:
            pass

    def handler_done(self, call, value):
        try:
            return self.fns.complete(call.call_id, value)
        except (CallCancelled, CallTrapped):
            return None
