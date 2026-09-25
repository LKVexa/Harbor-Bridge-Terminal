"""Canonical tenant/site/environment partition identity (component 25)."""
from __future__ import annotations

import re
from dataclasses import dataclass

_PART = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
ESTATE = "estate"  # certifications are estate-wide per the GAP-15 contract


class PartitionError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


@dataclass(frozen=True, order=True)
class Partition:
    """``tenant/environment/site`` — every component must be canonical lower-case DNS-label form.

    Ambiguous caller variants (``Prod``, `` prod``, ``prod_``) are rejected rather
    than normalised, so the same logical partition has exactly one spelling.
    """

    tenant: str
    environment: str
    site: str

    def __post_init__(self) -> None:
        for name in ("tenant", "environment", "site"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _PART.match(value):
                raise PartitionError("E_PARTITION_INVALID", f"{name} {value!r} is not a canonical label")

    @property
    def key(self) -> str:
        return f"{self.tenant}/{self.environment}/{self.site}"

    @classmethod
    def parse(cls, key: str) -> "Partition":
        if not isinstance(key, str) or key.count("/") != 2:
            raise PartitionError("E_PARTITION_INVALID", "expected tenant/environment/site")
        return cls(*key.split("/"))

    def as_dict(self) -> dict:
        return {"tenant": self.tenant, "environment": self.environment, "site": self.site}
