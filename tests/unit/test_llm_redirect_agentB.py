"""Agent B (security): redirects must never forward the Authorization
header to a different origin (urllib forwards it by default)."""

import urllib.error
import urllib.request

import pytest

from pybamm_closed_loop.literature.extraction import _NoAuthLeakRedirectHandler


def _req(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        data=b"{}",
        headers={"Authorization": "Bearer secret", "Content-Type": "application/json"},
        method="POST",
    )


def handler() -> _NoAuthLeakRedirectHandler:
    return _NoAuthLeakRedirectHandler()


def test_cross_host_redirect_strips_authorization():
    out = handler().redirect_request(
        _req("https://api.origin.com/v1"), None, 302, "Found", {},
        "https://evil.example.org/v1",
    )
    assert out is not None
    assert "Authorization" not in out.headers


def test_same_host_secure_redirect_keeps_authorization():
    out = handler().redirect_request(
        _req("https://api.origin.com/v1"), None, 302, "Found", {},
        "https://api.origin.com/v1/retry",
    )
    assert out is not None
    assert out.headers.get("Authorization") == "Bearer secret"


def test_scheme_downgrade_same_host_redirect_strips_authorization():
    out = handler().redirect_request(
        _req("https://api.origin.com/v1"), None, 302, "Found", {},
        "http://api.origin.com/v1",
    )
    assert out is not None
    assert "Authorization" not in out.headers


def test_cross_port_redirect_strips_authorization():
    out = handler().redirect_request(
        _req("https://api.origin.com/v1"), None, 302, "Found", {},
        "https://api.origin.com:8080/v1",
    )
    assert out is not None
    assert "Authorization" not in out.headers


def test_non_redirectable_request_still_raises_like_stdlib():
    # urllib raises HTTPError when the redirect method combination is not
    # redirectable (e.g. 307 + POST): parity with unmodified stdlib.
    with pytest.raises(urllib.error.HTTPError):
        handler().redirect_request(
            _req("https://api.origin.com/v1"), None, 307, "Temp", {},
            "https://evil.example.org/v1",
        )
