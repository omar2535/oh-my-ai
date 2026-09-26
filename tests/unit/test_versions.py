import httpx
import pytest

from omai.registry import LatestSource
from omai.versions import fetch_latest, is_newer, normalize


@pytest.mark.parametrize(
    "raw, expected",
    [("rust-v0.157.1", "0.157.1"), ("v2.1.283", "2.1.283"), (" 2.1.283\n", "2.1.283"), ("version", "version")],
)
def test_normalize(raw, expected):
    assert normalize(raw) == expected


@pytest.mark.parametrize(
    "latest, installed, newer",
    [
        ("2.1.283", "2.1.278", True),
        ("2.1.274", "2.1.278", False),  # stable channel behind an installed latest build
        ("0.21.5", "0.21.4", True),
        ("1.0.12", "0.16.2", True),
        ("18.3.2", "18.3.2", False),
        ("abc", "abd", True),  # non-PEP 440 falls back to inequality
        (None, "1.0", False),
        ("1.0", None, False),
    ],
)
def test_is_newer(latest, installed, newer):
    assert is_newer(latest, installed) is newer


def client(routes):
    def handler(request):
        return routes.get(str(request.url), httpx.Response(404))

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_github_release_field_and_regex():
    url = "https://api.github.com/repos/NousResearch/hermes-agent/releases/latest"
    c = client({url: httpx.Response(200, json={"tag_name": "v2026.9.24", "name": "Hermes Agent v0.21.5 (v2026.9.24)"})})
    source = LatestSource("github_release", "NousResearch/hermes-agent", field="name", regex=r"v(\d+\.\d+\.\d+)")
    assert fetch_latest(c, source, {}) == "0.21.5"


def test_url_text_substitutes_release_channel():
    base = "https://downloads.claude.ai/claude-code-releases/"
    c = client({base + "stable": httpx.Response(200, text="2.1.274\n")})
    source = LatestSource("url_text", base + "{release_channel}")
    assert fetch_latest(c, source, {"release_channel": "stable"}) == "2.1.274"


def test_github_tag_strips_prefix():
    c = client({"https://api.github.com/repos/o/r/tags": httpx.Response(200, json=[{"name": "rust-v0.157.1"}])})
    assert fetch_latest(c, LatestSource("github_tag", "o/r"), {}) == "0.157.1"


def test_http_errors_raise():
    with pytest.raises(httpx.HTTPStatusError):
        fetch_latest(client({}), LatestSource("npm", "@openai/codex"), {})
