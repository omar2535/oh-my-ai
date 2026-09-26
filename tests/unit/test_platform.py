import pytest

from omai import platform
from omai.install import parse_list


def test_wsl_detected_from_kernel_release(tmp_path, monkeypatch):
    monkeypatch.setattr(platform.sys, "platform", "linux")
    release = tmp_path / "osrelease"
    release.write_text("6.6.87.2-microsoft-standard-WSL2\n")
    assert platform.os_kind(release) == "wsl"
    release.write_text("6.8.0-45-generic\n")
    assert platform.os_kind(release) == "linux"


def test_wsl_opens_windows_browser_first_and_escapes_ampersands():
    argvs = platform.opener_argvs("https://x.test/a?b=1&c=2", "wsl")
    assert argvs[0][:3] == ["cmd.exe", "/c", "start"]
    assert argvs[0][-1] == "https://x.test/a?b=1^&c=2"
    assert argvs[1][0] == "powershell.exe"


@pytest.mark.parametrize(
    "text, urls",
    [
        (
            "Open this URL in your browser: https://claude.ai/oauth/authorize?x=1&y=2\n",
            ["https://claude.ai/oauth/authorize?x=1&y=2"],
        ),
        ("Visit https://auth.openai.com/codex/device and enter ABCD-1234.", ["https://auth.openai.com/codex/device"]),
        ("\x1b[1mhttps://omp.sh/launch\x1b[0m", ["https://omp.sh/launch"]),
        ("no links here", []),
    ],
)
def test_find_urls(text, urls):
    assert platform.find_urls(text) == urls


def test_open_url_prints_and_uses_available_opener(fake_home):
    printed = []
    assert platform.open_url("https://x.test/login", "linux", echo=printed.append)
    assert "https://x.test/login" in printed[0]
    assert fake_home.calls("xdg-open") == [["https://x.test/login"]]


@pytest.mark.parametrize(
    "text, items",
    [("[]", []), ("- ~/.agents/skills\n- /opt/skills\n", ["~/.agents/skills", "/opt/skills"]), ("['~/a']", ["~/a"])],
)
def test_parse_list_from_harness_config_output(text, items):
    assert parse_list(text) == items
