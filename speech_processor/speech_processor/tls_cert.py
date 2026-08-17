#!/usr/bin/env python3

# Copyright (c) 2024, RoboVerse community
# SPDX-License-Identifier: BSD-3-Clause

"""
Self-signed TLS cert for browser-facing HTTP/WS servers (mic_bridge_node,
cam_bridge_node, etc.).

Browsers only grant getUserMedia() (microphone/webcam access) from a "secure
context": localhost, or HTTPS. A LAN client (e.g. a laptop reaching the
robot/host over Wi-Fi at its IP) is plain HTTP and NOT localhost, so
getUserMedia() is silently unavailable there -- confirmed the hard way: the
old plain-HTTP mic bridge worked fine from the same machine running Docker
Desktop (http://localhost:8888, exempt from the secure-context rule) but
had no way to grant mic access from a second machine on the LAN.

A self-signed cert makes HTTPS/WSS available for that case. There's no
public hostname to get a real CA-signed cert for on a LAN robot deployment,
so the browser will still show a one-time "connection is not private"
warning to click through (or permanently trust) per host:port -- that's
an accepted tradeoff, not a bug.

Cached under /tmp so a hot-patch process restart (kill + relaunch within
the same container) reuses the same cert and doesn't force browsers to
re-warn; a full container recreate regenerates it.
"""

from __future__ import annotations

import os
import socket
import ssl
import subprocess

_CERT_DIR = "/tmp/go2_tls"
_CERT_FILE = os.path.join(_CERT_DIR, "cert.pem")
_KEY_FILE = os.path.join(_CERT_DIR, "key.pem")


def _detect_local_ips() -> list[str]:
    """Best-effort local IPv4 addresses, for the cert's subjectAltName.

    Not required for the cert to work (browsers still allow clicking through
    a SAN mismatch), just avoids the scarier "wrong site" variant of the
    warning when the detected IP happens to match how the page was reached.
    """
    ips: set[str] = {"127.0.0.1"}
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ips.add(s.getsockname()[0])
    except OSError:
        pass
    return sorted(ips)


def _generate_cert() -> None:
    os.makedirs(_CERT_DIR, exist_ok=True)
    san = ",".join(["DNS:localhost"] + [f"IP:{ip}" for ip in _detect_local_ips()])
    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", _KEY_FILE, "-out", _CERT_FILE,
            "-days", "3650", "-nodes",
            "-subj", "/CN=go2-robot-sdk",
            "-addext", f"subjectAltName={san}",
        ],
        check=True, capture_output=True, timeout=15,
    )


def get_server_context() -> ssl.SSLContext | None:
    """Returns a TLS server context, generating a cached self-signed cert on
    first use. Returns None (caller should fall back to plain HTTP/WS) if
    openssl isn't available or cert generation otherwise fails -- a missing
    dev-convenience feature is better than a crashed node.
    """
    try:
        if not (os.path.exists(_CERT_FILE) and os.path.exists(_KEY_FILE)):
            _generate_cert()
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=_CERT_FILE, keyfile=_KEY_FILE)
        return ctx
    except (OSError, subprocess.SubprocessError, ssl.SSLError):
        return None
