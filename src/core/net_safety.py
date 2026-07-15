"""
Outbound URL safety (SSRF mitigation for webhooks, browser tool, ecosystem).

Blocks private/link-local/loopback destinations unless SUPERAI_ALLOW_PRIVATE_URLS=1.
"""

from __future__ import annotations

import ipaddress
import os
import socket
from typing import Optional
from urllib.parse import urlparse


def _truthy(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def is_private_or_reserved(ip: ipaddress._BaseAddress) -> bool:  # type: ignore[name-defined]
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_public_http_url(
    url: str,
    *,
    require_https: bool = False,
    allow_private: Optional[bool] = None,
) -> Optional[str]:
    """
    Return None if URL is acceptable for outbound fetch/post; else error string.
    """
    u = (url or "").strip()
    if not u:
        return "empty URL"
    parsed = urlparse(u)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        return "Only http(s) URLs allowed"
    if require_https and scheme != "https" and not _truthy("SUPERAI_ALLOW_HTTP_WEBHOOK"):
        return "HTTPS required for outbound webhooks (set SUPERAI_ALLOW_HTTP_WEBHOOK=1 to override)"
    host = parsed.hostname
    if not host:
        return "URL missing host"
    if allow_private is None:
        allow_private = _truthy("SUPERAI_ALLOW_PRIVATE_URLS")
    if allow_private:
        return None
    # Block obvious metadata hostnames even before DNS
    low = host.lower().rstrip(".")
    if low in {"localhost", "metadata.google.internal"} or low.endswith(".local"):
        return f"Blocked host: {host}"
    try:
        # Resolve all A/AAAA records
        infos = socket.getaddrinfo(host, parsed.port or (443 if scheme == "https" else 80))
    except socket.gaierror as e:
        return f"DNS resolution failed: {e}"
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if is_private_or_reserved(ip):
            return f"Blocked private/reserved destination: {host} -> {addr}"
    return None


def assert_public_http_url(url: str, **kwargs) -> str:
    err = validate_public_http_url(url, **kwargs)
    if err:
        raise ValueError(err)
    return url
