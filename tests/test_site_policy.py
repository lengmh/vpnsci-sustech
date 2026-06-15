import unittest

from vpnsci_sustech.site_policy import (
    CNKI_MAX_DOWNLOADS_PER_RUN,
    CNKI_MIN_INTERVAL_SECONDS,
    PHASE2_MIN_INTERVAL_SECONDS,
    PHASE2_MAX_DOWNLOADS_PER_RUN,
    get_site_policy,
)


class SitePolicyTests(unittest.TestCase):
    def test_sciencedirect_policy_is_working_and_has_phase2_backups(self):
        policy = get_site_policy("sciencedirect")
        self.assertEqual(policy.status, "working")
        self.assertTrue(policy.publisher_native_search)
        self.assertTrue(policy.curl_cffi_candidate)
        self.assertTrue(policy.browser_cdp_candidate)

    def test_springer_policy_prefers_existing_path(self):
        policy = get_site_policy("springerlink")
        self.assertEqual(policy.status, "working")
        self.assertFalse(policy.browser_cdp_preferred)
        self.assertTrue(policy.keep_existing_download_path)

    def test_wiley_policy_is_working_and_keeps_existing_download_path(self):
        policy = get_site_policy("wiley")
        self.assertEqual(policy.status, "working")
        self.assertTrue(policy.keep_existing_download_path)

    def test_ieee_policy(self):
        policy = get_site_policy("ieee")
        self.assertEqual(policy.status, "working")
        self.assertTrue(policy.keep_existing_download_path)
        self.assertFalse(policy.needs_validation_first)
        self.assertTrue(policy.publisher_native_search)
        self.assertTrue(policy.curl_cffi_candidate)
        self.assertTrue(policy.browser_cdp_candidate)
        self.assertFalse(policy.browser_cdp_preferred)

    def test_phase2_limits_are_stricter_than_default_runtime(self):
        self.assertEqual(PHASE2_MIN_INTERVAL_SECONDS, 10.0)
        self.assertEqual(PHASE2_MAX_DOWNLOADS_PER_RUN, 10)

    def test_cnki_policy_is_experimental_and_browser_gated(self):
        policy = get_site_policy("cnki")
        self.assertEqual(policy.status, "experimental")
        self.assertTrue(policy.needs_validation_first)
        self.assertTrue(policy.publisher_native_search)
        self.assertFalse(policy.curl_cffi_candidate)
        self.assertTrue(policy.browser_cdp_candidate)
        self.assertTrue(policy.browser_cdp_preferred)
        self.assertEqual(CNKI_MIN_INTERVAL_SECONDS, 20.0)
        self.assertEqual(CNKI_MAX_DOWNLOADS_PER_RUN, 5)
