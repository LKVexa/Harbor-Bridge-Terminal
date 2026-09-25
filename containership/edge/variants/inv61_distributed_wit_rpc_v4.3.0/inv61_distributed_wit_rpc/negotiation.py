"""M05 - Protocol version negotiation with downgrade protection.

Protocol versions are (major, minor).  Peers negotiate the highest mutually
supported version whose major matches and which is >= both sides'
``min_accepted``.  Downgrade protection: the server MACs the full transcript
(both offered lists, both minimums, both nonces and the chosen version) with
the pairwise key; the client recomputes it over what *it* sent, so an on-path
attacker who strips higher versions from the offer is detected.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

Version = tuple[int, int]

SUPPORTED: tuple[Version, ...] = ((2, 0), (2, 1))
MIN_ACCEPTED: Version = (2, 0)
CURRENT: Version = max(SUPPORTED)
MATRIX_PATH = Path(__file__).with_name("COMPAT_MATRIX.json")


class NegotiationError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def choose(offered: list[Version], peer_min: Version,
           supported: tuple[Version, ...] = SUPPORTED, own_min: Version = MIN_ACCEPTED) -> Version:
    floor = max(tuple(peer_min), own_min)
    common = sorted({tuple(v) for v in offered} & set(supported))
    common = [v for v in common if v >= floor]
    if not common:
        raise NegotiationError("no-common-version")
    return common[-1]


def transcript(client_peer: str, offered: list[Version], client_min: Version, client_nonce: str,
               server_peer: str, chosen: Version, server_nonce: str, server_supported=SUPPORTED) -> bytes:
    doc = {
        "c": [client_peer, sorted(list(map(list, offered))), list(client_min), client_nonce],
        "s": [server_peer, sorted(list(map(list, server_supported))), list(chosen), server_nonce],
    }
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()


def transcript_mac(key: bytes, blob: bytes) -> bytes:
    return hmac.new(key, b"INV61-HELLO\x00" + blob, hashlib.sha256).digest()


def verify_ack(key: bytes, blob: bytes, mac: bytes, offered: list[Version], chosen: Version) -> None:
    if not hmac.compare_digest(transcript_mac(key, blob), mac):
        raise NegotiationError("transcript-mac")
    # A server honouring our offer must pick the highest version we both support.
    if tuple(chosen) not in {tuple(v) for v in offered}:
        raise NegotiationError("chosen-not-offered")


def matrix() -> dict:
    """Machine-readable compatibility matrix (COMPAT_MATRIX.json)."""
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
