"""Phase 2 site policy and support matrix."""

from dataclasses import dataclass

PHASE2_MIN_INTERVAL_SECONDS = 10.0
PHASE2_MAX_DOWNLOADS_PER_RUN = 10


@dataclass(frozen=True)
class SitePolicy:
    site: str
    status: str
    keep_existing_download_path: bool
    needs_validation_first: bool
    publisher_native_search: bool
    curl_cffi_candidate: bool
    browser_cdp_candidate: bool
    browser_cdp_preferred: bool


_SITE_POLICIES = {
    "sciencedirect": SitePolicy(
        site="sciencedirect",
        status="working",
        keep_existing_download_path=False,
        needs_validation_first=False,
        publisher_native_search=True,
        curl_cffi_candidate=True,
        browser_cdp_candidate=True,
        browser_cdp_preferred=True,
    ),
    "springerlink": SitePolicy(
        site="springerlink",
        status="working",
        keep_existing_download_path=True,
        needs_validation_first=False,
        publisher_native_search=False,
        curl_cffi_candidate=True,
        browser_cdp_candidate=True,
        browser_cdp_preferred=False,
    ),
    "wiley": SitePolicy(
        site="wiley",
        status="working",
        keep_existing_download_path=True,
        needs_validation_first=False,
        publisher_native_search=False,
        curl_cffi_candidate=True,
        browser_cdp_candidate=True,
        browser_cdp_preferred=False,
    ),
}


def get_site_policy(site: str) -> SitePolicy:
    key = site.strip().lower()
    if key not in _SITE_POLICIES:
        raise KeyError(f"Unknown site policy: {site}")
    return _SITE_POLICIES[key]
