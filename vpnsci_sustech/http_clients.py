"""HTTP client helpers for Phase 2 publisher transports."""

from dataclasses import dataclass
import time

import requests


class SiteRateLimiter:
    def __init__(self, min_interval_seconds: float = 10.0):
        self.min_interval_seconds = min_interval_seconds
        self._last_request_at: dict[str, float] = {}

    def wait(self, site: str):
        now = time.monotonic()
        last = self._last_request_at.get(site)
        if last is not None:
            elapsed = now - last
            if elapsed < self.min_interval_seconds:
                time.sleep(self.min_interval_seconds - elapsed)
                now = time.monotonic()
        self._last_request_at[site] = now


@dataclass(frozen=True)
class HttpClientInfo:
    engine: str
    impersonation_enabled: bool


class RequestsHttpClient:
    def __init__(self, session=None):
        self.session = session or requests.Session()
        self.engine = "requests"

    def get(self, url: str, **kwargs):
        return self.session.get(url, **kwargs)


class CurlCffiHttpClient:
    def __init__(self, session):
        self.session = session
        self.engine = "curl_cffi"

    def get(self, url: str, **kwargs):
        return self.session.get(url, **kwargs)


def create_http_client(prefer_impersonation: bool = False) -> HttpClientInfo:
    if prefer_impersonation:
        try:
            from curl_cffi import requests as curl_requests
            return CurlCffiHttpClient(curl_requests.Session(impersonate="chrome124"))
        except Exception:
            pass
    return RequestsHttpClient()
