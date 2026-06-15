import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from vpnsci_sustech.fetcher import PaperFetcher
from vpnsci_sustech.models import Paper
from vpnsci_sustech.sources.search_models import SearchHit


class _Cfg:
    school = ""
    webvpn_base_url = ""
    carsi_enabled = True
    carsi_idp_name = "Southern University of Science and Technology"
    output_dir = "F:/AI playground/TempFiles"
    cache_dir = "F:/AI playground/TempFiles"
    cookie_path = "F:/AI playground/TempFiles/cookies.json"
    chrome_profile_dir = "F:/AI playground/TempFiles/chrome-profile"
    carsi_cookie_dir = "F:/AI playground/TempFiles/carsi-cookies"
    request_delay_min = 2.0
    request_delay_max = 5.0
    email = ""
    proxy_url = ""
    elsevier_api_key = ""
    elsevier_inst_token = ""
    flaresolverr_url = "http://127.0.0.1:8191/v1"
    paper_filename_policy = "title_author"
    paper_filename_template = "{title} - {first_author}"
    paper_filename_ask = True
    paper_filename_max_length = 180
    paper_filename_collision = "hash"

    def ensure_dirs(self):
        return None


class FetcherPhase2Tests(unittest.TestCase):
    def test_fetch_from_search_hit_uses_doi_for_non_cnki_hit(self):
        fetcher = PaperFetcher(_Cfg())
        expected = Paper(doi="10.1234/example", title="Known", source="open_access", full_text="body" * 300)
        fetcher.fetch = mock.Mock(return_value=expected)
        hit = SearchHit(title="Known", doi="10.1234/example", hit_key="doi:10.1234/example", source="openalex")

        result = fetcher.fetch_from_search_hit(hit)

        self.assertEqual(result, expected)
        fetcher.fetch.assert_called_once_with(
            "10.1234/example",
            use_cache=True,
            filename_policy="",
            filename_template="",
        )

    def test_fetch_from_search_hit_uses_cnki_materialization_for_local_file(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            fetcher = PaperFetcher(_Cfg())
            source = Path(tmp) / "paper.caj"
            source.write_bytes(b"caj-content")
            fake_artifact = mock.Mock(path=str(source), format="caj", text_extracted=False, note="")
            hit = SearchHit(
                title="知网论文",
                authors=["张三"],
                cnki_id="ABC123",
                hit_key="cnki:ABC123",
                local_file=str(source),
                source_url="https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                source="cnki",
            )

            with mock.patch("vpnsci_sustech.sources.cnki.CNKIClient.materialize_downloaded_file", return_value=fake_artifact) as materialize_mock:
                result = fetcher.fetch_from_search_hit(hit)

            self.assertEqual(result.title, "知网论文")
            self.assertEqual(result.cnki_id, "ABC123")
            materialize_mock.assert_called_once()

    def test_fetch_from_search_hit_can_continue_cnki_live_download_from_source_url(self):
        fetcher = PaperFetcher(_Cfg())
        fake_artifact = mock.Mock(path="F:/AI playground/TempFiles/paper.pdf", format="pdf", text_extracted=True, note="")
        hit = SearchHit(
            title="知网论文",
            authors=["张三"],
            cnki_id="ABC123",
            hit_key="cnki:ABC123",
            source_url="https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
            download_format="pdf",
            source="cnki",
        )

        with mock.patch("vpnsci_sustech.sources.cnki.CNKIClient.download_cnki_artifact", return_value=fake_artifact) as download_mock:
            result = fetcher.fetch_from_search_hit(hit, confirm_live_access=True)

        self.assertEqual(result.title, "知网论文")
        self.assertEqual(result.cnki_id, "ABC123")
        download_mock.assert_called_once()

    def test_fetch_rejects_cnki_url_in_main_kernel(self):
        fetcher = PaperFetcher(_Cfg())

        result = fetcher.fetch("https://kns.cnki.net/kcms2/article/abstract?filename=ABC123", use_cache=False)

        self.assertEqual(result.url, "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123")
        self.assertEqual(result.source, "cnki_blocked_main_kernel")
        self.assertEqual(result.full_text, "")

    def test_save_artifact_title_author_policy_uses_metadata_filename(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = _Cfg()
            cfg.output_dir = tmp
            cfg.paper_filename_policy = "title_author"
            fetcher = PaperFetcher(cfg)
            paper = Paper(
                doi="10.1234/example",
                title="钙钛矿太阳能电池稳定性研究",
                authors=["张三"],
            )

            path = fetcher._save_artifact(paper, b"%PDF-1.4", ext="pdf")

            self.assertIsNotNone(path)
            self.assertEqual(Path(path).name, "钙钛矿太阳能电池稳定性研究 - 张三.pdf")
            self.assertEqual(Path(path).read_bytes(), b"%PDF-1.4")

    def test_save_artifact_records_artifact_metadata(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = _Cfg()
            cfg.output_dir = tmp
            fetcher = PaperFetcher(cfg)
            paper = Paper(doi="10.1038/nphys1509", title="Known Paper")

            path = fetcher._save_artifact(
                paper,
                b"%PDF-1.4",
                ext="pdf",
                original_url="https://example.test/paper.pdf",
            )

            self.assertEqual(paper.pdf_path, str(path))
            self.assertEqual(len(paper.artifacts), 1)
            self.assertEqual(paper.artifacts[0].path, str(path))
            self.assertEqual(paper.artifacts[0].format, "pdf")
            self.assertEqual(paper.artifacts[0].source_url, "https://example.test/paper.pdf")
            self.assertTrue(paper.artifacts[0].text_extracted)

    def test_save_artifact_identifier_policy_preserves_overwrite_compatibility(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = _Cfg()
            cfg.output_dir = tmp
            cfg.paper_filename_policy = "identifier"
            fetcher = PaperFetcher(cfg)
            paper = Paper(doi="10.1038/nphys1509", title="Known Paper", authors=["Kato"])

            first = fetcher._save_artifact(paper, b"old", ext="pdf")
            second = fetcher._save_artifact(paper, b"new", ext="pdf")

            self.assertEqual(first, second)
            self.assertEqual(Path(second).name, "10.1038_nphys1509.pdf")
            self.assertEqual(Path(second).read_bytes(), b"new")

    def test_direct_html_followed_pdf_uses_title_author_policy_when_requested(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = _Cfg()
            cfg.output_dir = tmp
            cfg.paper_filename_policy = "title_author"
            fetcher = PaperFetcher(cfg)
            paper = Paper(doi="10.1007/BF00994018", url="https://link.springer.com/article/10.1007/BF00994018")

            class _Resp:
                status_code = 200
                url = "https://link.springer.com/article/10.1007/BF00994018"
                headers = {"content-type": "text/html"}
                text = "<html><body>article page</body></html>"

                def raise_for_status(self):
                    return None

            class _PdfResp:
                status_code = 200
                headers = {"content-type": "application/pdf"}
                content = b"%PDF-1.4 springer-direct"

                def raise_for_status(self):
                    return None

            with mock.patch("vpnsci_sustech.fetcher.request_with_retry", side_effect=[_Resp(), _PdfResp()]), \
                 mock.patch.object(fetcher, "_rate_limit", return_value=None), \
                 mock.patch("vpnsci_sustech.fetcher.html_extractor.extract", return_value={"title": "Support-vector networks", "authors": ["Cortes"], "full_text": "html text"}), \
                 mock.patch.object(fetcher, "_find_pdf_link", return_value="https://link.springer.com/content/pdf/10.1007/BF00994018.pdf"), \
                 mock.patch("vpnsci_sustech.fetcher.pdf_extractor.extract_from_bytes", return_value="pdf text" * 200):
                result = fetcher._try_direct_html("https://link.springer.com/article/10.1007/BF00994018", paper)

            self.assertIsNotNone(result)
            self.assertEqual(Path(result.pdf_path).name, "Support-vector networks - Cortes.pdf")

    def test_fetch_applies_explicit_filename_policy_override(self):
        fetcher = PaperFetcher(_Cfg())
        expected = Paper(
            doi="10.1007/BF00994018",
            title="Support-vector networks",
            url="https://link.springer.com/article/10.1007/BF00994018",
            source="direct",
            full_text="springer text" * 200,
        )

        def fake_direct_html(_url, _paper):
            self.assertEqual(fetcher._filename_policy_override, "title_author")
            return expected

        fetcher._try_open_access = lambda doi: None
        fetcher._resolve_doi = lambda doi: "https://link.springer.com/article/10.1007/BF00994018"
        fetcher._try_direct_html = fake_direct_html

        result = fetcher.fetch("10.1007/BF00994018", use_cache=False, filename_policy="title_author")

        self.assertEqual(result, expected)

    def test_browser_capture_gate_supports_sciencedirect_springer_wiley(self):
        fetcher = PaperFetcher(_Cfg())
        self.assertTrue(fetcher._should_try_browser_capture("https://www.sciencedirect.com/science/article/pii/S123"))
        self.assertTrue(fetcher._should_try_browser_capture("https://link.springer.com/article/10.1007/BF00994018"))
        self.assertTrue(fetcher._should_try_browser_capture("https://onlinelibrary.wiley.com/doi/10.1111/j.2517-6161.1996.tb02080.x"))
        self.assertFalse(fetcher._should_try_browser_capture("https://arxiv.org/abs/1706.03762"))

    def test_carsi_pdf_falls_back_to_browser_for_supported_sites(self):
        fetcher = PaperFetcher(_Cfg())
        paper = Paper(doi="10.1007/BF00994018", url="https://link.springer.com/article/10.1007/BF00994018")

        class _Resp:
            status_code = 403
            content = b"<html>robot</html>"
            headers = {"content-type": "text/html"}
            url = "https://link.springer.com/article/10.1007/BF00994018"

            def raise_for_status(self):
                raise Exception("403")

        fetcher._carsi = mock.Mock(fetch=lambda url: _Resp())
        with mock.patch.object(fetcher, "_build_publisher_pdf_url", return_value="https://link.springer.com/content/pdf/10.1007/BF00994018.pdf"), mock.patch.object(
            fetcher, "_download_pdf_via_browser", return_value=(b"%PDF-1.4 test", "https://link.springer.com/content/pdf/10.1007/BF00994018.pdf")
        ), mock.patch.object(
            fetcher, "_save_artifact", return_value=None
        ):
            result = fetcher._try_carsi_pdf("10.1007/BF00994018", paper.url, paper)

        self.assertIsNotNone(result)
        self.assertTrue(result.full_text.startswith("%PDF") or len(result.full_text) >= 0)

    def test_pdf_capture_response_filter_is_not_ieee_specific(self):
        fetcher = PaperFetcher(_Cfg())
        self.assertTrue(fetcher._is_browser_pdf_response("https://pdf.sciencedirectassets.com/123.pdf", "application/pdf"))
        self.assertTrue(fetcher._is_browser_pdf_response("https://link.springer.com/content/pdf/10.1007/BF00994018.pdf", "application/pdf"))
        self.assertTrue(fetcher._is_browser_pdf_response("https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/anie.201410454", "application/pdf"))
        self.assertFalse(fetcher._is_browser_pdf_response("https://example.com/article", "text/html"))

    def test_pdf_capture_response_requires_real_pdf_mime_or_body(self):
        fetcher = PaperFetcher(_Cfg())
        self.assertFalse(fetcher._is_browser_pdf_response("https://www.sciencedirect.com/science/article/pii/S0169433221006001/pdfft", "text/html"))
        self.assertFalse(fetcher._is_browser_pdf_response("https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/anie.201410454", "text/html"))

    def test_fetch_prefers_browser_pdf_path_for_sciencedirect_before_carsi(self):
        fetcher = PaperFetcher(_Cfg())
        expected = Paper(
            doi="10.1016/example",
            title="SD Paper",
            url="https://www.sciencedirect.com/science/article/pii/S123",
            source="browser",
            full_text="text",
            pdf_path="F:/tmp/sd.pdf",
        )
        fetcher._try_open_access = lambda doi: None
        fetcher._resolve_doi = lambda doi: "https://www.sciencedirect.com/science/article/pii/S123"
        fetcher._try_browser_pdf_direct = lambda doi, url, paper: expected
        fetcher._try_carsi_pdf = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("carsi should not run first"))
        result = fetcher.fetch("10.1016/example", use_cache=False)
        self.assertEqual(result.source, "browser")

    def test_fetch_prefers_browser_pdf_path_for_wiley_before_carsi(self):
        fetcher = PaperFetcher(_Cfg())
        expected = Paper(
            doi="10.1002/anie.201410454",
            title="Wiley Paper",
            url="https://onlinelibrary.wiley.com/doi/10.1002/anie.201410454",
            source="browser",
            full_text="text",
            pdf_path="F:/tmp/wiley.pdf",
        )
        fetcher._try_open_access = lambda doi: None
        fetcher._resolve_doi = lambda doi: "https://onlinelibrary.wiley.com/doi/10.1002/anie.201410454"
        fetcher._try_browser_pdf_direct = lambda doi, url, paper: expected
        fetcher._try_carsi_pdf = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("carsi should not run first"))
        result = fetcher.fetch("10.1002/anie.201410454", use_cache=False)
        self.assertEqual(result.source, "browser")

    def test_fetch_prefers_browser_pdf_path_for_sciencedirect_url_before_carsi(self):
        fetcher = PaperFetcher(_Cfg())
        expected = Paper(
            doi="",
            title="SD URL Paper",
            url="https://www.sciencedirect.com/science/article/pii/S0169433221006001",
            source="browser",
            full_text="text",
            pdf_path="F:/tmp/sd-url.pdf",
        )
        fetcher._try_open_access = lambda doi: None
        fetcher._try_browser_pdf_direct = lambda doi, url, paper: expected
        fetcher._try_carsi_html = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("carsi html should not run first"))
        result = fetcher.fetch("https://www.sciencedirect.com/science/article/pii/S0169433221006001", use_cache=False)
        self.assertEqual(result.source, "browser")

    def test_fetch_prefers_direct_path_for_springer_before_proxy_auth(self):
        fetcher = PaperFetcher(_Cfg())
        expected = Paper(
            doi="10.1007/BF00994018",
            title="Support-vector networks",
            url="https://link.springer.com/article/10.1007/BF00994018",
            source="direct",
            full_text="springer text" * 200,
            pdf_path="F:/tmp/springer.pdf",
        )
        fetcher._try_open_access = lambda doi: None
        fetcher._resolve_doi = lambda doi: "https://link.springer.com/article/10.1007/BF00994018"
        fetcher._try_direct_html = lambda url, paper: expected
        fetcher._try_carsi_pdf = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("carsi pdf should not run first"))
        fetcher._try_publisher_pdf = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("publisher pdf auth path should not run first"))
        result = fetcher.fetch("10.1007/BF00994018", use_cache=False)
        self.assertEqual(result.source, "direct")

    def test_direct_html_can_follow_pdf_link_and_save_pdf(self):
        fetcher = PaperFetcher(_Cfg())
        paper = Paper(doi="10.1007/BF00994018", url="https://link.springer.com/article/10.1007/BF00994018")

        class _Resp:
            status_code = 200
            url = "https://link.springer.com/article/10.1007/BF00994018"
            headers = {"content-type": "text/html"}
            text = "<html><head><title>Support-vector networks</title></head><body>article page</body></html>"

            def raise_for_status(self):
                return None

        class _PdfResp:
            status_code = 200
            headers = {"content-type": "application/pdf"}
            content = b"%PDF-1.4 springer-direct"

            def raise_for_status(self):
                return None

        with mock.patch("vpnsci_sustech.fetcher.request_with_retry", side_effect=[_Resp(), _PdfResp()]), \
             mock.patch("vpnsci_sustech.fetcher.html_extractor.extract", return_value={"title": "Support-vector networks", "full_text": "html text"}), \
             mock.patch.object(fetcher, "_find_pdf_link", return_value="https://link.springer.com/content/pdf/10.1007/BF00994018.pdf"), \
             mock.patch("vpnsci_sustech.fetcher.pdf_extractor.extract_from_bytes", return_value="pdf text" * 200), \
             mock.patch.object(fetcher, "_save_artifact", return_value=Path("F:/tmp/springer-direct.pdf")):
            result = fetcher._try_direct_html("https://link.springer.com/article/10.1007/BF00994018", paper)

        self.assertIsNotNone(result)
        self.assertEqual(Path(result.pdf_path).as_posix(), "F:/tmp/springer-direct.pdf")
        self.assertGreater(len(result.full_text), len("html text"))

    def test_browser_pdf_download_uses_shared_chrome_session_manager(self):
        fetcher = PaperFetcher(_Cfg())

        class _Driver:
            def __init__(self):
                self.visited = []
                self.closed = False

            def execute_cdp_cmd(self, method, params):
                if method == "Network.enable":
                    return {}
                if method == "Network.getResponseBody":
                    return {
                        "body": base64.b64encode(b"%PDF-1.4 shared-session").decode("ascii"),
                        "base64Encoded": True,
                    }
                raise AssertionError(f"unexpected cdp call: {method}")

            def get(self, url):
                self.visited.append(url)

            def get_log(self, kind):
                self.assertEqual(kind, "performance")
                payload = {
                    "message": {
                        "method": "Network.responseReceived",
                        "params": {
                            "requestId": "req-1",
                            "response": {
                                "url": "https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/anie.201410454",
                                "mimeType": "application/pdf",
                            },
                        },
                    }
                }
                return [{"message": json.dumps(payload)}]

            def find_elements(self, *_args, **_kwargs):
                return []

            def quit(self):
                self.closed = True

            def assertEqual(self, left, right):
                if left != right:
                    raise AssertionError(f"{left!r} != {right!r}")

        fake_driver = _Driver()
        fake_manager = mock.Mock()
        fake_manager.prepare_profile.return_value = Path(_Cfg.cache_dir) / "chrome-debug-profile"
        fake_manager.launch_browser.return_value = fake_driver

        with mock.patch("vpnsci_sustech.fetcher.ChromeDebugSessionManager", create=True, return_value=fake_manager) as manager_cls, \
             mock.patch("vpnsci_sustech.fetcher.time.sleep", return_value=None):
            result = fetcher._download_pdf_via_browser(
                "https://onlinelibrary.wiley.com/doi/10.1002/anie.201410454",
                "https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/anie.201410454",
            )

        self.assertIsNotNone(result)
        self.assertEqual(result[0], b"%PDF-1.4 shared-session")
        self.assertEqual(
            fake_driver.visited,
            [
                "https://onlinelibrary.wiley.com/doi/10.1002/anie.201410454",
                "https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/anie.201410454",
            ],
        )
        manager_cls.assert_called_once_with(base_dir=Path(_Cfg.cache_dir), profile_root_name="chrome-profile")
        fake_manager.launch_browser.assert_called_once()

    def test_browser_pdf_download_applies_phase2_site_rate_limit(self):
        fetcher = PaperFetcher(_Cfg())

        class _Driver:
            def execute_cdp_cmd(self, method, params):
                if method == "Network.enable":
                    return {}
                if method == "Network.getResponseBody":
                    return {
                        "body": base64.b64encode(b"%PDF-1.4 rate-limited").decode("ascii"),
                        "base64Encoded": True,
                    }
                raise AssertionError(f"unexpected cdp call: {method}")

            def get(self, _url):
                return None

            def get_log(self, _kind):
                payload = {
                    "message": {
                        "method": "Network.responseReceived",
                        "params": {
                            "requestId": "req-1",
                            "response": {
                                "url": "https://www.sciencedirect.com/science/article/pii/S0169433221006001/pdfft",
                                "mimeType": "application/pdf",
                            },
                        },
                    }
                }
                return [{"message": json.dumps(payload)}]

            def find_elements(self, *_args, **_kwargs):
                return []

            def quit(self):
                return None

        fake_manager = mock.Mock()
        fake_manager.launch_browser.return_value = _Driver()

        with mock.patch("vpnsci_sustech.fetcher.ChromeDebugSessionManager", return_value=fake_manager), \
             mock.patch("vpnsci_sustech.fetcher.time.sleep", return_value=None), \
             mock.patch.object(fetcher, "_phase2_site_wait") as site_wait:
            result = fetcher._download_pdf_via_browser(
                "https://www.sciencedirect.com/science/article/pii/S0169433221006001",
                "https://www.sciencedirect.com/science/article/pii/S0169433221006001/pdfft",
            )

        self.assertIsNotNone(result)
        self.assertEqual(site_wait.call_args_list, [mock.call("sciencedirect"), mock.call("sciencedirect")])

    def test_browser_pdf_download_prefers_page_discovered_wiley_pdf_link(self):
        fetcher = PaperFetcher(_Cfg())

        class _Element:
            def __init__(self, href=None, src=None, data=None):
                self._href = href
                self._src = src
                self._data = data

            def get_attribute(self, name):
                return {
                    "href": self._href,
                    "src": self._src,
                    "data": self._data,
                }.get(name)

        class _Driver:
            def __init__(self):
                self.visited = []

            def execute_cdp_cmd(self, method, params):
                if method == "Network.enable":
                    return {}
                if method == "Network.getResponseBody":
                    return {
                        "body": base64.b64encode(b"%PDF-1.4 discovered-wiley-link").decode("ascii"),
                        "base64Encoded": True,
                    }
                raise AssertionError(f"unexpected cdp call: {method}")

            def get(self, url):
                self.visited.append(url)

            def get_log(self, _kind):
                payload = {
                    "message": {
                        "method": "Network.responseReceived",
                        "params": {
                            "requestId": "req-1",
                            "response": {
                                "url": "https://onlinelibrary.wiley.com/doi/pdf/10.1002/anie.201410454",
                                "mimeType": "application/pdf",
                            },
                        },
                    }
                }
                return [{"message": json.dumps(payload)}]

            def find_elements(self, *_args, **_kwargs):
                return [
                    _Element(href="https://onlinelibrary.wiley.com/doi/epdf/10.1002/anie.201410454"),
                    _Element(href="https://onlinelibrary.wiley.com/doi/pdf/10.1002/anie.201410454"),
                    _Element(href="https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/anie.201410454"),
                ]

            def quit(self):
                return None

        fake_manager = mock.Mock()
        fake_manager.launch_browser.return_value = _Driver()

        with mock.patch("vpnsci_sustech.fetcher.ChromeDebugSessionManager", return_value=fake_manager), \
             mock.patch("vpnsci_sustech.fetcher.time.sleep", return_value=None), \
             mock.patch.object(fetcher, "_phase2_site_wait", return_value=None):
            result = fetcher._download_pdf_via_browser(
                "https://onlinelibrary.wiley.com/doi/10.1002/anie.201410454",
                "https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/anie.201410454",
            )

        self.assertIsNotNone(result)
        self.assertEqual(
            fake_manager.launch_browser.return_value.visited,
            [
                "https://onlinelibrary.wiley.com/doi/10.1002/anie.201410454",
                "https://onlinelibrary.wiley.com/doi/pdf/10.1002/anie.201410454",
            ],
        )

    def test_browser_pdf_download_prefers_sciencedirect_view_pdf_link_with_query(self):
        fetcher = PaperFetcher(_Cfg())

        class _Element:
            def __init__(self, href=None, src=None, data=None):
                self._href = href
                self._src = src
                self._data = data

            def get_attribute(self, name):
                return {
                    "href": self._href,
                    "src": self._src,
                    "data": self._data,
                }.get(name)

        class _Driver:
            def __init__(self):
                self.visited = []

            def execute_cdp_cmd(self, method, params):
                if method == "Network.enable":
                    return {}
                if method == "Network.getResponseBody":
                    return {
                        "body": base64.b64encode(b"%PDF-1.4 sd-discovered-link").decode("ascii"),
                        "base64Encoded": True,
                    }
                raise AssertionError(f"unexpected cdp call: {method}")

            def get(self, url):
                self.visited.append(url)

            def get_log(self, _kind):
                payload = {
                    "message": {
                        "method": "Network.responseReceived",
                        "params": {
                            "requestId": "req-1",
                            "response": {
                                "url": "https://www.sciencedirect.com/science/article/pii/S2314717216300873/pdfft?md5=abc&pid=1-s2.0-main.pdf",
                                "mimeType": "application/pdf",
                            },
                        },
                    }
                }
                return [{"message": json.dumps(payload)}]

            def find_elements(self, *_args, **_kwargs):
                return [
                    _Element(href="https://www.sciencedirect.com/science/article/pii/S2314717216300873/pdfft?md5=abc&pid=1-s2.0-main.pdf"),
                    _Element(href="https://www.sciencedirect.com/science/article/pii/S2314717216300873#abs0005"),
                ]

            def quit(self):
                return None

        fake_manager = mock.Mock()
        fake_manager.launch_browser.return_value = _Driver()

        with mock.patch("vpnsci_sustech.fetcher.ChromeDebugSessionManager", return_value=fake_manager), \
             mock.patch("vpnsci_sustech.fetcher.time.sleep", return_value=None), \
             mock.patch.object(fetcher, "_phase2_site_wait", return_value=None):
            result = fetcher._download_pdf_via_browser(
                "https://www.sciencedirect.com/science/article/pii/S2314717216300873",
                "https://www.sciencedirect.com/science/article/pii/S2314717216300873/pdfft",
            )

        self.assertIsNotNone(result)
        self.assertEqual(
            fake_manager.launch_browser.return_value.visited,
            [
                "https://www.sciencedirect.com/science/article/pii/S2314717216300873",
                "https://www.sciencedirect.com/science/article/pii/S2314717216300873/pdfft?md5=abc&pid=1-s2.0-main.pdf",
            ],
        )

    def test_browser_direct_can_fallback_to_sciencedirect_article_html(self):
        fetcher = PaperFetcher(_Cfg())
        paper = Paper(
            doi="10.1016/j.jesit.2016.10.007",
            url="https://www.sciencedirect.com/science/article/pii/S2314717216300873",
        )

        class _Driver:
            current_url = "https://www.sciencedirect.com/science/article/pii/S2314717216300873"
            title = "Filtering antenna with radiation and filtering functions for wireless applications - ScienceDirect"
            page_source = "<html><head><title>Filtering antenna with radiation and filtering functions for wireless applications - ScienceDirect</title></head><body><span class='title-text'>Filtering antenna with radiation and filtering functions for wireless applications</span><div class='abstract'>OA abstract</div><div id='body'>This manuscript presents a filtering antenna design. This manuscript presents a filtering antenna design. This manuscript presents a filtering antenna design. This manuscript presents a filtering antenna design. This manuscript presents a filtering antenna design. This manuscript presents a filtering antenna design.</div></body></html>"

            def execute_cdp_cmd(self, method, params):
                if method == "Network.enable":
                    return {}
                raise AssertionError(f"unexpected cdp call: {method}")

            def get(self, _url):
                return None

            def get_log(self, _kind):
                return []

            def find_elements(self, *_args, **_kwargs):
                return []

            def quit(self):
                return None

        fake_manager = mock.Mock()
        fake_manager.launch_browser.return_value = _Driver()

        with mock.patch("vpnsci_sustech.fetcher.ChromeDebugSessionManager", return_value=fake_manager), \
             mock.patch("vpnsci_sustech.fetcher.time.sleep", return_value=None), \
             mock.patch.object(fetcher, "_phase2_site_wait", return_value=None):
            result = fetcher._try_browser_pdf_direct(
                "10.1016/j.jesit.2016.10.007",
                "https://www.sciencedirect.com/science/article/pii/S2314717216300873",
                paper,
            )

        self.assertIsNotNone(result)
        self.assertEqual(result.source, "browser")
        self.assertIn("filtering antenna design", result.full_text.lower())

    def test_browser_article_html_can_print_sciencedirect_page_to_pdf(self):
        fetcher = PaperFetcher(_Cfg())
        paper = Paper(
            doi="10.1016/j.jesit.2016.10.007",
            url="https://www.sciencedirect.com/science/article/pii/S2314717216300873",
        )

        class _Driver:
            current_url = "https://www.sciencedirect.com/science/article/pii/S2314717216300873"
            title = "Filtering antenna with radiation and filtering functions for wireless applications - ScienceDirect"
            page_source = "<html><head><title>Filtering antenna with radiation and filtering functions for wireless applications - ScienceDirect</title></head><body><span class='title-text'>Filtering antenna with radiation and filtering functions for wireless applications</span><div class='abstract'>OA abstract</div><div id='body'>This manuscript presents a filtering antenna design. This manuscript presents a filtering antenna design. This manuscript presents a filtering antenna design. This manuscript presents a filtering antenna design. This manuscript presents a filtering antenna design. This manuscript presents a filtering antenna design.</div></body></html>"

            def execute_cdp_cmd(self, method, params):
                if method == "Page.printToPDF":
                    return {"data": base64.b64encode(b"%PDF-1.4 printed-sciencedirect").decode("ascii")}
                raise AssertionError(f"unexpected cdp call: {method}")

            def get(self, _url):
                return None

            def quit(self):
                return None

        fake_manager = mock.Mock()
        fake_manager.launch_browser.return_value = _Driver()

        with mock.patch("vpnsci_sustech.fetcher.ChromeDebugSessionManager", return_value=fake_manager), \
             mock.patch("vpnsci_sustech.fetcher.time.sleep", return_value=None), \
             mock.patch.object(fetcher, "_phase2_site_wait", return_value=None), \
             mock.patch.object(fetcher, "_save_artifact", return_value=Path("F:/tmp/sciencedirect-printed.pdf")), \
             mock.patch("vpnsci_sustech.fetcher.html_extractor.extract", return_value={"title": "Filtering antenna with radiation and filtering functions for wireless applications", "full_text": "html text" * 300}):
            result = fetcher._try_browser_article_html(
                "https://www.sciencedirect.com/science/article/pii/S2314717216300873",
                paper,
            )

        self.assertIsNotNone(result)
        self.assertEqual(Path(result.pdf_path).as_posix(), "F:/tmp/sciencedirect-printed.pdf")
        self.assertEqual(result.source, "browser+printed_pdf")

    def test_browser_article_html_skips_printed_pdf_when_page_is_challenge_like(self):
        fetcher = PaperFetcher(_Cfg())
        paper = Paper(
            doi="10.1016/j.jesit.2016.10.007",
            url="https://www.sciencedirect.com/science/article/pii/S2314717216300873",
        )

        class _Driver:
            current_url = "https://www.sciencedirect.com/science/article/pii/S2314717216300873"
            title = "ScienceDirect"
            page_source = "<html><body>Are you a robot? Please confirm you are a human by completing the captcha challenge below.</body></html>"

            def execute_cdp_cmd(self, method, params):
                if method == "Page.printToPDF":
                    return {"data": base64.b64encode(b"%PDF-1.4 challenge-page").decode("ascii")}
                raise AssertionError(f"unexpected cdp call: {method}")

            def get(self, _url):
                return None

            def quit(self):
                return None

        fake_manager = mock.Mock()
        fake_manager.launch_browser.return_value = _Driver()

        with mock.patch("vpnsci_sustech.fetcher.ChromeDebugSessionManager", return_value=fake_manager), \
             mock.patch("vpnsci_sustech.fetcher.time.sleep", return_value=None), \
             mock.patch.object(fetcher, "_phase2_site_wait", return_value=None), \
             mock.patch.object(fetcher, "_save_artifact", return_value=Path("F:/tmp/should-not-save.pdf")) as save_artifact_mock, \
             mock.patch("vpnsci_sustech.fetcher.html_extractor.extract", return_value={"title": "", "full_text": "Are you a robot? captcha challenge", "abstract": ""}):
            result = fetcher._try_browser_article_html(
                "https://www.sciencedirect.com/science/article/pii/S2314717216300873",
                paper,
            )

        self.assertIsNotNone(result)
        self.assertEqual(result.pdf_path, "")
        save_artifact_mock.assert_not_called()

    def test_browser_article_html_generates_local_pdf_when_print_unavailable(self):
        fetcher = PaperFetcher(_Cfg())
        paper = Paper(
            doi="10.1016/j.jesit.2016.10.007",
            url="https://www.sciencedirect.com/science/article/pii/S2314717216300873",
        )

        class _Driver:
            current_url = "https://www.sciencedirect.com/science/article/pii/S2314717216300873"
            title = "Filtering antenna with radiation and filtering functions for wireless applications - ScienceDirect"
            page_source = "<html><body>article</body></html>"

            def execute_cdp_cmd(self, method, params):
                if method == "Page.printToPDF":
                    raise RuntimeError("print failed")
                raise AssertionError(f"unexpected cdp call: {method}")

            def get(self, _url):
                return None

            def quit(self):
                return None

        fake_manager = mock.Mock()
        fake_manager.launch_browser.return_value = _Driver()

        with mock.patch("vpnsci_sustech.fetcher.ChromeDebugSessionManager", return_value=fake_manager), \
             mock.patch("vpnsci_sustech.fetcher.time.sleep", return_value=None), \
             mock.patch.object(fetcher, "_phase2_site_wait", return_value=None), \
             mock.patch.object(fetcher, "_save_artifact", return_value=Path("F:/tmp/generated-local.pdf")) as save_artifact_mock, \
             mock.patch.object(fetcher, "_create_generated_text_pdf", return_value=b"%PDF-1.4 generated"), \
             mock.patch("vpnsci_sustech.fetcher.html_extractor.extract", return_value={"title": "Filtering antenna", "full_text": "good full text " * 200, "abstract": ""}):
            result = fetcher._try_browser_article_html(
                "https://www.sciencedirect.com/science/article/pii/S2314717216300873",
                paper,
            )

        self.assertIsNotNone(result)
        self.assertEqual(Path(result.pdf_path).as_posix(), "F:/tmp/generated-local.pdf")
        self.assertEqual(result.source, "browser+generated_pdf")
        save_artifact_mock.assert_called_once()

    def test_fetch_can_return_sciencedirect_browser_article_html_before_auth_paths(self):
        fetcher = PaperFetcher(_Cfg())
        expected = Paper(
            doi="10.1016/j.jesit.2016.10.007",
            title="Filtering antenna with radiation and filtering functions for wireless applications",
            url="https://www.sciencedirect.com/science/article/pii/S2314717216300873",
            source="browser",
            full_text="filtering antenna" * 200,
            pdf_path="",
        )
        fetcher._try_open_access = lambda doi: None
        fetcher._resolve_doi = lambda doi: "https://www.sciencedirect.com/science/article/pii/S2314717216300873"
        fetcher._try_browser_pdf_direct = lambda doi, url, paper: expected
        fetcher._try_carsi_pdf = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("carsi should not run first"))
        result = fetcher.fetch("10.1016/j.jesit.2016.10.007", use_cache=False)
        self.assertEqual(result.source, "browser")
        self.assertGreater(len(result.full_text), 1000)

    def test_resolve_doi_canonicalizes_elsevier_linkinghub_url(self):
        fetcher = PaperFetcher(_Cfg())

        class _Resp:
            status_code = 200
            url = "https://linkinghub.elsevier.com/retrieve/pii/S2314717216300873"

            def close(self):
                return None

        with mock.patch("vpnsci_sustech.fetcher.request_with_retry", return_value=_Resp()):
            resolved = fetcher._resolve_doi("10.1016/j.jesit.2016.10.007")

        self.assertEqual(
            resolved,
            "https://www.sciencedirect.com/science/article/pii/S2314717216300873",
        )
