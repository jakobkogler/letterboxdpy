import base64
import gzip
import hashlib
import json
import re
from dataclasses import dataclass
from http.client import responses as http_reasons
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import curl_cffi.requests
import pytest
from bs4 import BeautifulSoup

CASSETTES_DIR = Path(__file__).parent / "cassettes"


def pytest_addoption(parser):
    parser.addoption(
        "--vcr-record",
        default="once",
        choices=["once", "all", "none"],
        help=(
            "once: record if no cassette, replay if exists (default)\n"
            "all:  always re-record (overwrite cassettes)\n"
            "none: replay only, fail if cassette missing"
        ),
    )


def _strip_scripts(content: bytes, content_type: str) -> bytes:
    if "html" not in content_type.lower():
        return content
    try:
        soup = BeautifulSoup(content, "html.parser")
    except Exception:
        return content

    # TODO: might be useful as script might contain JSON data.
    for tag in soup.find_all("script"):
        tag.decompose()
    for tag in soup.find_all("noscript"):
        tag.decompose()
    for tag in soup.find_all("link"):
        tag.decompose()
    for tag in soup.find_all("path"):
        tag.decompose()
    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            if attr.lower().startswith("on"):
                del tag[attr]

    return soup.encode(formatter="minimal")


def _url_to_cassette_path(method: str, url: str) -> Path:
    """Generate a readable, unique filename from method + URL."""
    parsed = urlparse(url)

    # Build readable part: host + path
    readable = parsed.netloc + parsed.path
    readable = re.sub(r"[^a-zA-Z0-9\-_]", "_", readable)
    readable = re.sub(r"_+", "_", readable).strip("_")
    readable = readable[:120]

    # Short hash for uniqueness (includes method, full URL with query)
    url_hash = hashlib.sha256(f"{method}:{url}".encode()).hexdigest()[:12]

    return CASSETTES_DIR / f"{readable}_{url_hash}.json.gz"


@dataclass
class CassetteResponse:
    status_code: int
    content: bytes
    headers: dict
    url: str
    reason: str = ""
    encoding: str = "utf-8"
    cookies: dict | None = None
    history: list | None = None

    def __post_init__(self):
        if not self.reason:
            self.reason = http_reasons.get(self.status_code, "Unknown")
        if self.cookies is None:
            self.cookies = {}
        if self.history is None:
            self.history = []

    @property
    def text(self):
        return self.content.decode(self.encoding, errors="replace")

    @property
    def ok(self):
        return 200 <= self.status_code < 400

    def raise_for_status(self):
        if not self.ok:
            raise Exception(f"HTTP {self.status_code} {self.reason}: {self.url}")

    def json(self):
        return json.loads(self.text)

    def __getattr__(self, name):
        raise AttributeError(
            f"CassetteResponse has no attribute '{name}' — "
            f"add it to the dataclass to record/replay it"
        )


def _save_cassette(path: Path, method: str, request_url: str, resp) -> None:
    content_type = resp.headers.get("content-type", "")
    content = _strip_scripts(resp.content, content_type)
    entry = {
        "method": method,
        "request_url": request_url,
        "response_url": str(getattr(resp, "url", request_url)),
        "status_code": resp.status_code,
        "reason": getattr(resp, "reason", ""),
        "content_b64": base64.b64encode(content).decode("ascii"),
        "headers": dict(resp.headers),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    raw_json = json.dumps(entry, indent=2, ensure_ascii=False).encode("utf-8")
    path.write_bytes(gzip.compress(raw_json, compresslevel=9))


def _load_cassette(path: Path) -> CassetteResponse:
    entry = json.loads(gzip.decompress(path.read_bytes()))
    return CassetteResponse(
        status_code=entry["status_code"],
        content=base64.b64decode(entry["content_b64"]),
        headers=entry["headers"],
        url=entry.get("response_url", entry.get("url", "")),
        reason=entry.get("reason", ""),
    )


@pytest.fixture(autouse=True)
def curl_vcr(request, monkeypatch):
    mode = request.config.getoption("--vcr-record")
    original_request = curl_cffi.requests.Session.request

    def caching_request(
        self,
        method: Literal[
            "GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "TRACE", "PATCH", "QUERY"
        ],
        url: str,
        **kwargs,
    ):
        if method != "GET":
            pytest.fail(f"Cassette cannot record request of type {method}")

        cassette = _url_to_cassette_path(method, url)

        should_replay = (mode == "once" and cassette.exists()) or mode == "none"

        if should_replay:
            if not cassette.exists():
                pytest.fail(
                    f"Cassette not found: {cassette}\n"
                    f"URL: {method} {url}\n"
                    f"Run with --vcr-record=once or --vcr-record=all to record it."
                )
            return _load_cassette(cassette)

        # Record
        resp = original_request(self, method, url, **kwargs)
        _save_cassette(cassette, method, url, resp)
        return resp

    monkeypatch.setattr(curl_cffi.requests.Session, "request", caching_request)
