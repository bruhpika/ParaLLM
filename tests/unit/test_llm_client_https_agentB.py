"""Agent B (security): OpenAICompatibleClient base_url must never send the
API key over plaintext http (https required; http only for loopback)."""

import pytest

from pybamm_closed_loop.literature.extraction import OpenAICompatibleClient, _validate_base_url

KEY = "test-only-fake-key"
MODEL = "test-model"


@pytest.mark.parametrize(
    "url",
    [
        "https://api.openai.com/v1",
        "https://api.example.org/v1/",
    ],
)
def test_https_urls_accepted(url):
    _validate_base_url(url)
    client = OpenAICompatibleClient(base_url=url, api_key=KEY, model=MODEL)
    assert client.base_url.rstrip("/") == url.rstrip("/")


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8000/v1",
        "http://127.0.0.1:11434/v1",
        "http://127.7.7.7:9000",
        "http://[::1]:1234/v1",
    ],
)
def test_http_loopback_accepted(url):
    _validate_base_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://api.example.com/v1",
        "http://localhost.attacker.example/v1",
        "http://8.8.8.8/v1",
        "ftp://localhost/v1",
        "file:///etc",
    ],
)
def test_non_https_non_loopback_rejected(url):
    with pytest.raises(ValueError, match="non-https"):
        OpenAICompatibleClient(base_url=url, api_key=KEY, model=MODEL)


def test_missing_key_still_raises_runtime_error_first():
    with pytest.raises(RuntimeError):
        OpenAICompatibleClient(base_url="http://api.example.com/v1", model=MODEL)
