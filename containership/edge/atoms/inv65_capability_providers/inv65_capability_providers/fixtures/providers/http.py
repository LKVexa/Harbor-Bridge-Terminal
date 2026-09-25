"""wasi:http outgoing-handler fixture: allowed hosts come from the link config;
no real network I/O (responses are synthesised)."""
from __future__ import annotations

from urllib.parse import urlsplit

from ...errors.mapping import ProviderFault
from .base import FaultyMixin


class HttpBackend(FaultyMixin):
    operations = ("request",)

    def invoke(self, op, config, secret, payload):
        self._faults()
        if op != "request":
            raise ProviderFault("PK_PROVIDER_INVALID_LINK", "unsupported http op")
        url = str(payload.get("url", ""))
        host = urlsplit(url).hostname or ""
        allowed = config.get("allowed_hosts", [])
        if urlsplit(url).scheme != "https" or host not in allowed:
            raise ProviderFault("PK_PROVIDER_FORBIDDEN", "destination not allowed by link config")
        return {"status": 200, "host": host, "bucket": config["bucket"], "as": config["user"],
                "authenticated": secret is not None}
