"""Latest-version lookup (read-only) with a cache in omai state."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import httpx
from packaging.version import InvalidVersion, Version

from omai.context import Ctx
from omai.registry import HarnessDef, LatestSource
from omai.state import age_hours, now_iso

_PREFIX = re.compile(r"^(?:rust-)?v(?=\d)")


def normalize(version: str) -> str:
    return _PREFIX.sub("", version.strip())


def is_newer(latest: str | None, installed: str | None) -> bool:
    if not latest or not installed:
        return False
    try:
        return Version(normalize(latest)) > Version(normalize(installed))
    except InvalidVersion:
        return normalize(latest) != normalize(installed)


def _dig(data, path: str):
    for part in path.split("."):
        data = data[int(part)] if isinstance(data, list) else data[part]
    return data


def fetch_latest(client: httpx.Client, source: LatestSource, values: dict[str, str]) -> str:
    ref = source.ref
    for key, value in values.items():
        ref = ref.replace("{" + key + "}", value)
    match source.kind:
        case "npm":
            raw = client.get(f"https://registry.npmjs.org/{ref}/latest").raise_for_status().json()["version"]
        case "pypi":
            raw = client.get(f"https://pypi.org/pypi/{ref}/json").raise_for_status().json()["info"]["version"]
        case "github_release":
            data = client.get(f"https://api.github.com/repos/{ref}/releases/latest").raise_for_status().json()
            raw = data[source.field or "tag_name"]
        case "github_tag":
            data = client.get(f"https://api.github.com/repos/{ref}/tags").raise_for_status().json()
            if not data:
                raise ValueError(f"{ref} has no tags")
            raw = data[0]["name"]
        case "url_text":
            raw = client.get(ref).raise_for_status().text
        case "url_json":
            raw = _dig(client.get(ref).raise_for_status().json(), source.field or "version")
        case _:
            raise ValueError(f"unknown latest source kind {source.kind}")
    raw = str(raw).strip()
    if source.regex:
        found = re.search(source.regex, raw)
        if not found:
            raise ValueError(f"latest version not found in {raw!r}")
        raw = found.group(1)
    return normalize(raw)


def describe_error(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code} from {exc.request.url.host}"
    if isinstance(exc, httpx.HTTPError):
        return f"network error ({type(exc).__name__})"
    return f"{type(exc).__name__}: {exc}"


@dataclass
class Latest:
    version: str | None
    error: str | None = None


def refresh(ctx: Ctx, harnesses: list[HarnessDef]) -> dict[str, Latest]:
    """Fetch latest versions in parallel and store them in the state cache."""

    def one(harness: HarnessDef) -> tuple[str, Latest]:
        try:
            with ctx.http() as client:
                return harness.id, Latest(fetch_latest(client, harness.latest, ctx.vars(harness)))
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
            return harness.id, Latest(None, describe_error(exc))

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = dict(pool.map(one, harnesses))
    items = ctx.state.checks.setdefault("items", {})
    for hid, latest in results.items():
        previous = items.get(hid, {})
        items[hid] = {"latest": latest.version or previous.get("latest"), "error": latest.error}
    ctx.state.checks["fetched_at"] = now_iso()
    ctx.state.save()
    return {hid: Latest(items[hid]["latest"], items[hid]["error"]) for hid in results}


def cached(ctx: Ctx) -> dict[str, Latest]:
    items = ctx.state.checks.get("items", {})
    return {hid: Latest(v.get("latest"), v.get("error")) for hid, v in items.items()}


def cache_stale(ctx: Ctx) -> bool:
    age = age_hours(ctx.state.checks.get("fetched_at"))
    return age is None or age >= ctx.config.ttl_hours
