"""M17 - host-import capability contract (+ the M18 WASI policy adapter).

Every import a module requests is classified from the bytes.  An import that is
not in the contract is refused (fail closed).  Classes:

* ``pure``              - result is a function of arguments only;
* ``io-deterministic``  - side effects but no nondeterministic results;
* ``nondeterministic``  - may return host-varying data (clock, random, ...).

A contract entry may imply a registered ISA feature (``wall-clock``) so that
host-level nondeterminism is subject to the same profile policy as
instruction-level features.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .errors import Code, InvalidModule

CONTRACT_SCHEMA = "PK_HOST_IMPORT_CONTRACT/1"
CLASSES = ("pure", "io-deterministic", "nondeterministic")
KIND_NAMES = {0: "func", 1: "table", 2: "memory", 3: "global"}


@dataclass(frozen=True)
class ImportRule:
    klass: str
    implies_feature: str | None
    kinds: frozenset[int]


@dataclass(frozen=True)
class HostContract:
    revision: str
    rules: Mapping[tuple[str, str], ImportRule]
    module_wildcards: Mapping[str, ImportRule]

    def classify(self, imports) -> tuple[frozenset[str], frozenset[str]]:
        """Return (import classes used, features implied); refuse unknowns."""
        classes, feats = set(), set()
        for mod, name, kind in imports:
            rule = self.rules.get((mod, name)) or self.module_wildcards.get(mod)
            if rule is None:
                raise InvalidModule(Code.HOST_IMPORT_REFUSED,
                                    f"import {mod}.{name} is not in the host contract", section="import")
            if kind not in rule.kinds:
                raise InvalidModule(Code.HOST_IMPORT_REFUSED,
                                    f"import {mod}.{name} kind {KIND_NAMES.get(kind)} not allowed",
                                    section="import")
            classes.add(rule.klass)
            if rule.implies_feature:
                feats.add(rule.implies_feature)
        return frozenset(classes), frozenset(feats)


def load_contract(raw: bytes, known_features: frozenset[str]) -> HostContract:
    import hashlib
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise InvalidModule(Code.REGISTRY_INVALID, f"host contract not JSON: {exc}") from None
    if not isinstance(doc, dict) or set(doc) != {"schema", "imports"} or doc["schema"] != CONTRACT_SCHEMA:
        raise InvalidModule(Code.REGISTRY_INVALID, "host contract schema/fields invalid")
    rules, wild = {}, {}
    for key, r in doc["imports"].items():
        if not isinstance(r, dict) or set(r) != {"class", "implies_feature", "kinds"}:
            raise InvalidModule(Code.REGISTRY_INVALID, f"host rule {key}: fields invalid")
        if r["class"] not in CLASSES:
            raise InvalidModule(Code.REGISTRY_INVALID, f"host rule {key}: bad class")
        if r["implies_feature"] is not None and r["implies_feature"] not in known_features:
            raise InvalidModule(Code.REGISTRY_INVALID, f"host rule {key}: unregistered feature")
        kinds = frozenset(k for k, v in KIND_NAMES.items() if v in r["kinds"])
        if len(kinds) != len(r["kinds"]):
            raise InvalidModule(Code.REGISTRY_INVALID, f"host rule {key}: bad kinds")
        rule = ImportRule(r["class"], r["implies_feature"], kinds)
        if "." not in key:
            raise InvalidModule(Code.REGISTRY_INVALID, f"host rule {key}: expected module.name")
        mod, name = key.split(".", 1)
        if name == "*":
            wild[mod] = rule
        else:
            rules[(mod, name)] = rule
    canon = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    return HostContract("hostc:sha256:" + hashlib.sha256(canon).hexdigest(),
                        MappingProxyType(rules), MappingProxyType(wild))


W = "wasi_snapshot_preview1"
DEFAULT_CONTRACT_DOC = {
    "schema": CONTRACT_SCHEMA,
    "imports": {
        # M18 WASI adapter: deny-by-default, only these preview1 calls are known.
        f"{W}.fd_write": {"class": "io-deterministic", "implies_feature": None, "kinds": ["func"]},
        f"{W}.fd_read": {"class": "io-deterministic", "implies_feature": None, "kinds": ["func"]},
        f"{W}.fd_close": {"class": "io-deterministic", "implies_feature": None, "kinds": ["func"]},
        f"{W}.proc_exit": {"class": "pure", "implies_feature": None, "kinds": ["func"]},
        f"{W}.args_get": {"class": "pure", "implies_feature": None, "kinds": ["func"]},
        f"{W}.args_sizes_get": {"class": "pure", "implies_feature": None, "kinds": ["func"]},
        f"{W}.environ_get": {"class": "pure", "implies_feature": None, "kinds": ["func"]},
        f"{W}.environ_sizes_get": {"class": "pure", "implies_feature": None, "kinds": ["func"]},
        f"{W}.clock_time_get": {"class": "nondeterministic", "implies_feature": "wall-clock", "kinds": ["func"]},
        f"{W}.clock_res_get": {"class": "nondeterministic", "implies_feature": "wall-clock", "kinds": ["func"]},
        f"{W}.random_get": {"class": "nondeterministic", "implies_feature": None, "kinds": ["func"]},
        f"{W}.sched_yield": {"class": "nondeterministic", "implies_feature": None, "kinds": ["func"]},
        "env.memory": {"class": "pure", "implies_feature": None, "kinds": ["memory"]},
        "env.__indirect_function_table": {"class": "pure", "implies_feature": None, "kinds": ["table"]},
    },
}


def default_contract(known_features: frozenset[str]) -> HostContract:
    return load_contract(json.dumps(DEFAULT_CONTRACT_DOC).encode(), known_features)
