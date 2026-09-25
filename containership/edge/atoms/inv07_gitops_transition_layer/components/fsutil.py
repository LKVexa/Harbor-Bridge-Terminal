"""Small file helpers that always close handles (Windows cannot replace or
delete a file another handle still holds open)."""
from __future__ import annotations

import json


def read_bytes(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
