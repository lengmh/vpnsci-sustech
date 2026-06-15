import unittest
from unittest import mock

from vpnsci_sustech import http_clients


class HttpClientTests(unittest.TestCase):
    def test_phase2_site_rate_limiter_sleeps_to_ten_seconds(self):
        limiter = http_clients.SiteRateLimiter(min_interval_seconds=10.0)
        with mock.patch.object(http_clients.time, "monotonic", side_effect=[100.0, 103.0, 110.0]), mock.patch.object(
            http_clients.time, "sleep"
        ) as sleep_mock:
            limiter.wait("sciencedirect")
            limiter.wait("sciencedirect")

        sleep_mock.assert_called_once()
        self.assertAlmostEqual(sleep_mock.call_args.args[0], 7.0, places=6)

    def test_requests_client_is_used_when_curl_cffi_unavailable(self):
        with mock.patch.dict("sys.modules", {"curl_cffi": None}):
            client = http_clients.create_http_client(prefer_impersonation=True)
        self.assertEqual(client.engine, "requests")
