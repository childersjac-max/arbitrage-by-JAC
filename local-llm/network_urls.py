"""Resolve LAN URLs for phone / tablet access on the same Wi-Fi."""

from __future__ import annotations

import socket


def get_lan_ipv4_addresses() -> list[str]:
    """Return likely LAN IPv4 addresses (non-loopback), best guess first."""
    found: list[str] = []
    seen: set[str] = set()

    def add(ip: str) -> None:
        if ip.startswith("127.") or ip in seen:
            return
        seen.add(ip)
        found.append(ip)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            add(sock.getsockname()[0])
    except OSError:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            add(info[4][0])
    except OSError:
        pass

    return found


def phone_access_urls(port: int, *, scheme: str = "http") -> list[str]:
    """Full URLs to open on a phone on the same network."""
    return [f"{scheme}://{ip}:{port}" for ip in get_lan_ipv4_addresses()]


def resolve_ui_bind(host: str, port: int, *, lan_enabled: bool) -> tuple[str, str, list[str]]:
    """
    Return (bind_host, local_browser_url, phone_urls).

    When LAN is enabled, bind to 0.0.0.0 and list http://<lan-ip>:port for phones.
    """
    host = (host or "127.0.0.1").strip()
    lan = lan_enabled or host in {"0.0.0.0", "::"}

    if lan:
        bind_host = "0.0.0.0"
        local_url = f"http://127.0.0.1:{port}"
        phones = phone_access_urls(port)
        return bind_host, local_url, phones

    local_url = f"http://{host}:{port}"
    return host, local_url, []
