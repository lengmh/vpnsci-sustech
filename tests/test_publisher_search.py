import unittest
from unittest import mock

from vpnsci_sustech.sources import publisher_search
from vpnsci_sustech.http_clients import RequestsHttpClient, CurlCffiHttpClient


class PublisherSearchTests(unittest.TestCase):
    def test_challenge_detection_covers_cloudflare_and_robot_pages(self):
        self.assertTrue(publisher_search.looks_like_access_challenge("<title>Just a moment...</title>"))
        self.assertTrue(publisher_search.looks_like_access_challenge("verify you are human"))
        self.assertTrue(publisher_search.looks_like_access_challenge("robot check"))
        self.assertFalse(publisher_search.looks_like_access_challenge("<html><body>normal article page</body></html>"))

    def test_phase2_http_clients_support_post(self):
        self.assertTrue(hasattr(RequestsHttpClient(), "post"))
        self.assertTrue(hasattr(CurlCffiHttpClient(mock.Mock()), "post"))

    def test_challenge_detection_does_not_flag_sciencedirect_search_results_page(self):
        html = """
        <html>
          <head>
            <meta name="robots" content="NOINDEX,FOLLOW,NOARCHIVE">
            <script src="/cdn-cgi/challenge-platform/scripts/jsd/main.js"></script>
            <title>filtering antenna - Search | ScienceDirect.com</title>
          </head>
          <body>
            <a href="/science/article/pii/S2314717216300873">Filtering antenna with radiation and filtering functions for wireless applications</a>
            <a href="/science/article/pii/S2314717216300873/pdfft?pid=1-s2.0-S2314717216300873-main.pdf">View PDF</a>
          </body>
        </html>
        """
        self.assertFalse(publisher_search.looks_like_access_challenge(html))

    def test_challenge_detection_does_not_flag_wiley_advanced_search_page(self):
        html = """
        <html>
          <head>
            <title>Advanced Search - Wiley Online Library</title>
            <script src="/cdn-cgi/challenge-platform/scripts/jsd/main.js"></script>
          </head>
          <body>
            <div class="password-recaptcha-ajax"></div>
            <h1>ADVANCED SEARCH</h1>
            <form action="/action/doSearch" method="get">
              <input name="publication[]" value="15213773" type="hidden" />
              <input name="text1" value="" />
            </form>
          </body>
        </html>
        """
        self.assertFalse(publisher_search.looks_like_access_challenge(html))

    def test_challenge_detection_does_not_flag_ieee_search_results_page(self):
        html = """
        <html>
          <head>
            <title>IEEE Xplore Search Results</title>
          </head>
          <body>
            <script>var RECAPTCHA_PUBLIC_KEY = "site-key";</script>
            <div id="xplMainContent">Search Results</div>
          </body>
        </html>
        """
        self.assertFalse(publisher_search.looks_like_access_challenge(html))

    def test_parse_sciencedirect_search_api_payload(self):
        payload = {
            "searchResults": [
                {
                    "title": "<em>Filtering</em> Antenna Example",
                    "doi": "10.1016/example",
                    "sourceTitle": "AEU - International Journal of Electronics and Communications",
                    "publicationDate": "2024-03-01",
                    "pii": "S1234567890123456",
                    "link": "/science/article/pii/S1234567890123456",
                    "pdf": {"downloadLink": "/science/article/pii/S1234567890123456/pdfft?pid=1-s2.0-main.pdf"},
                    "authors": [{"name": "Alice"}, {"name": "Bob"}],
                }
            ]
        }
        hits = publisher_search.parse_sciencedirect_search_api(payload)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].doi, "10.1016/example")
        self.assertEqual(hits[0].title, "Filtering Antenna Example")
        self.assertIn("/science/article/pii/S1234567890123456", hits[0].url)
        self.assertIn("pid=", hits[0].pdf_url)

    def test_parse_springer_search_html(self):
        html = """
        <html><body>
          <li class="app-card-open">
            <a href="/article/10.1007/BF00994018">Support-Vector Networks</a>
            <span class="app-card-open__metadata">Machine Learning (1995)</span>
          </li>
        </body></html>
        """
        hits = publisher_search.parse_springer_search_html(html)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].doi, "10.1007/BF00994018")
        self.assertEqual(hits[0].title, "Support-Vector Networks")

    def test_parse_wiley_search_html(self):
        html = """
        <html><body>
          <div class="search__item">
            <a href="/doi/10.1111/j.2517-6161.1996.tb02080.x">Regression Shrinkage and Selection via the Lasso</a>
            <span class="publication_meta">Journal of the Royal Statistical Society: Series B (1996)</span>
          </div>
        </body></html>
        """
        hits = publisher_search.parse_wiley_search_html(html)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].doi, "10.1111/j.2517-6161.1996.tb02080.x")
        self.assertIn("/doi/pdfdirect/", hits[0].pdf_url)

    def test_route_for_supported_publishers(self):
        self.assertEqual(publisher_search.resolve_backend("sciencedirect"), "sciencedirect")
        self.assertEqual(publisher_search.resolve_backend("springerlink"), "springerlink")
        self.assertEqual(publisher_search.resolve_backend("wiley"), "wiley")

    def test_route_for_supported_publishers_includes_ieee(self):
        self.assertEqual(publisher_search.resolve_backend("ieee"), "ieee")
        self.assertEqual(publisher_search.resolve_backend("ieeexplore"), "ieee")
        self.assertEqual(publisher_search.resolve_backend("ieee xplore"), "ieee")

    def test_top_level_search_routes_sciencedirect_with_browser_fallback(self):
        fake_hits = [publisher_search.SearchHit(title="SD Hit", url="https://www.sciencedirect.com/science/article/pii/S1")]
        with mock.patch.object(publisher_search, "search_sciencedirect", return_value=fake_hits) as sd_mock:
            hits = publisher_search.search("filtering antenna", backend="sciencedirect", limit=3)

        self.assertEqual(len(hits), 1)
        self.assertTrue(sd_mock.call_args.kwargs["allow_browser_fallback"])

    def test_top_level_search_routes_ieee(self):
        fake_hits = [
            publisher_search.SearchHit(
                title="Network Anomaly Detection Using a Graph Neural Network",
                doi="10.1109/ICNC57223.2023.10074111",
                url="https://ieeexplore.ieee.org/document/10074111/",
                pdf_url="https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=10074111",
                journal="2023 International Conference on Computing, Networking and Communications (ICNC)",
                year=2023,
                authors=["Patrice Kisanga", "Isaac Woungang"],
                citation_count=35,
                abstract="Contrary to the many traditional network security approaches...",
            )
        ]
        with mock.patch.object(publisher_search, "search_ieee", return_value=fake_hits) as ieee_mock:
            hits = publisher_search.search("graph neural network", backend="ieee", limit=3)

        self.assertEqual(len(hits), 1)
        ieee_mock.assert_called_once_with("graph neural network", limit=3)

    def test_parse_ieee_search_api_records(self):
        payload = {
            "records": [
                {
                    "articleTitle": "Network Anomaly Detection Using a [::Graph::] Neural Network",
                    "doi": "10.1109/ICNC57223.2023.10074111",
                    "documentLink": "/document/10074111/",
                    "pdfLink": "/stamp/stamp.jsp?tp=&arnumber=10074111",
                    "publicationTitle": "2023 International Conference on Computing, [::Networking::] and Communications (ICNC)",
                    "publicationYear": "2023",
                    "authors": [
                        {"preferredName": "Patrice Kisanga"},
                        {"preferredName": "Isaac Woungang"},
                    ],
                    "citationCount": 35,
                    "abstract": "Contrary to the many traditional [::network::] security approaches.",
                }
            ]
        }

        hits = publisher_search.parse_ieee_search_api(payload)

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].title, "Network Anomaly Detection Using a Graph Neural Network")
        self.assertEqual(hits[0].doi, "10.1109/ICNC57223.2023.10074111")
        self.assertEqual(hits[0].url, "https://ieeexplore.ieee.org/document/10074111/")
        self.assertEqual(hits[0].pdf_url, "https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=10074111")
        self.assertEqual(hits[0].journal, "2023 International Conference on Computing, Networking and Communications (ICNC)")
        self.assertEqual(hits[0].year, 2023)
        self.assertEqual(hits[0].authors, ["Patrice Kisanga", "Isaac Woungang"])
        self.assertEqual(hits[0].citation_count, 35)
        self.assertNotIn("[::", hits[0].abstract)

    def test_search_ieee_warms_page_then_posts_rest_search(self):
        class _JsonResp:
            def __init__(self, status_code=200, text="", payload=None):
                self.status_code = status_code
                self.text = text
                self.headers = {"content-type": "application/json"}
                self.url = "https://ieeexplore.ieee.org/rest/search"
                self._payload = payload or {}

            def json(self):
                return self._payload

        page_resp = _JsonResp(status_code=200, text="<title>IEEE Xplore Search Results</title>")
        api_resp = _JsonResp(
            status_code=200,
            text='{"records": []}',
            payload={
                "records": [
                    {
                        "articleTitle": "Network Anomaly Detection Using a Graph Neural Network",
                        "doi": "10.1109/ICNC57223.2023.10074111",
                        "articleNumber": "10074111",
                        "pdfLink": "/stamp/stamp.jsp?tp=&arnumber=10074111",
                        "publicationYear": 2023,
                    }
                ]
            },
        )
        fake_client = mock.Mock()
        fake_client.get.return_value = page_resp
        fake_client.post.return_value = api_resp

        with mock.patch.object(publisher_search, "create_http_client", return_value=fake_client), \
             mock.patch.object(publisher_search, "_SITE_LIMITER") as limiter:
            hits = publisher_search.search_ieee("graph neural network", limit=3)

        self.assertEqual(len(hits), 1)
        fake_client.get.assert_called_once()
        self.assertEqual(fake_client.get.call_args.args[0], "https://ieeexplore.ieee.org/search/searchresult.jsp")
        self.assertEqual(fake_client.get.call_args.kwargs["params"]["queryText"], "graph neural network")
        self.assertEqual(
            fake_client.get.call_args.kwargs["headers"]["Referer"],
            "https://ieeexplore.ieee.org/search/searchresult.jsp?queryText=graph+neural+network",
        )
        fake_client.post.assert_called_once()
        self.assertEqual(fake_client.post.call_args.args[0], "https://ieeexplore.ieee.org/rest/search")
        self.assertEqual(fake_client.post.call_args.kwargs["json"]["rowsPerPage"], 3)
        self.assertEqual(fake_client.post.call_args.kwargs["json"]["queryText"], "graph neural network")
        self.assertEqual(limiter.wait.call_count, 2)
        limiter.wait.assert_any_call("ieee")

    def test_search_ieee_reports_challenge_page(self):
        class _JsonResp:
            status_code = 200
            text = "verify you are human"
            headers = {"content-type": "text/html"}
            url = "https://ieeexplore.ieee.org/search/searchresult.jsp"

        fake_client = mock.Mock()
        fake_client.get.return_value = _JsonResp()

        with mock.patch.object(publisher_search, "create_http_client", return_value=fake_client), \
             mock.patch.object(publisher_search, "_SITE_LIMITER"):
            with self.assertRaises(publisher_search.PublisherSearchBlockedError):
                publisher_search.search_ieee("graph neural network", limit=3)

    def test_search_sciencedirect_uses_http_api_before_browser_fallback(self):
        class _PageResp:
            status_code = 200
            url = "https://www.sciencedirect.com/search?qs=filtering+antenna"
            text = '<script>window.__INITIAL_STATE__={"token":{"searchToken":"abc123"}};</script>'
            headers = {"content-type": "text/html"}

        class _ApiResp:
            status_code = 200
            url = "https://www.sciencedirect.com/search/api?qs=filtering+antenna&t=abc123&hostname=www.sciencedirect.com"
            headers = {"content-type": "application/json"}
            text = '{"searchResults":[{"title":"<em>Filtering</em> antenna example","doi":"10.1016/example","pii":"S123","link":"/science/article/pii/S123","pdf":{"downloadLink":"/science/article/pii/S123/pdfft?pid=main.pdf"}}]}'

            def json(self):
                return {
                    "searchResults": [
                        {
                            "title": "<em>Filtering</em> antenna example",
                            "doi": "10.1016/example",
                            "pii": "S123",
                            "link": "/science/article/pii/S123",
                            "pdf": {"downloadLink": "/science/article/pii/S123/pdfft?pid=main.pdf"},
                        }
                    ]
                }

        fake_client = mock.Mock()
        fake_client.get.side_effect = [_PageResp(), _ApiResp()]
        with mock.patch.object(publisher_search, "create_http_client", return_value=fake_client), \
             mock.patch.object(publisher_search, "_SITE_LIMITER"), \
             mock.patch.object(publisher_search, "_search_sciencedirect_via_browser") as browser_mock:
            hits = publisher_search.search_sciencedirect("filtering antenna", limit=3, allow_browser_fallback=True)

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].doi, "10.1016/example")
        browser_mock.assert_not_called()

    def test_search_backend_falls_back_when_wiley_returns_challenge_page(self):
        class _Resp:
            status_code = 403
            url = "https://onlinelibrary.wiley.com/action/doSearch"
            text = "<title>Just a moment...</title>"
            headers = {"content-type": "text/html"}

        fake_client = type("C", (), {"get": lambda self, *args, **kwargs: _Resp()})()
        fake_hits = [publisher_search.SearchHit(title="fallback", doi="10.1002/anie.201410454")]
        with mock.patch.object(publisher_search, "create_http_client", return_value=fake_client), \
             mock.patch.object(publisher_search, "_search_wiley_via_crossref", return_value=fake_hits):
            hits = publisher_search.search_wiley("lasso", limit=3)

        self.assertEqual(len(hits), 1)

    def test_search_backend_can_use_browser_fallback_for_wiley(self):
        class _Resp:
            status_code = 403
            url = "https://onlinelibrary.wiley.com/action/doSearch"
            text = "<title>Just a moment...</title>"
            headers = {"content-type": "text/html"}

        html = """
        <html><body>
          <div class="search__item">
            <a href="/doi/10.1111/j.2517-6161.1996.tb02080.x">Regression Shrinkage and Selection via the Lasso</a>
          </div>
        </body></html>
        """
        fake_client = type("C", (), {"get": lambda self, *args, **kwargs: _Resp()})()
        with mock.patch.object(publisher_search, "create_http_client", return_value=fake_client), \
             mock.patch.object(publisher_search, "_search_wiley_via_browser", return_value=publisher_search.parse_wiley_search_html(html)):
            hits = publisher_search.search_wiley("lasso", limit=3, allow_browser_fallback=True)

        self.assertEqual(len(hits), 1)

    def test_search_wiley_via_browser_can_submit_advanced_form(self):
        class _Input:
            def __init__(self):
                self.sent = ""

            def clear(self):
                self.sent = ""

            def send_keys(self, value):
                self.sent += value

        class _Button:
            def __init__(self):
                self.clicked = 0

            def click(self):
                self.clicked += 1
                raise Exception("intercepted")

        class _Form:
            def __init__(self):
                self.text1 = _Input()
                self.submit = _Button()
                self.attrs = {
                    "id": "frmSearch",
                    "class": "advanced-search frmSearch clearfix",
                }

            def get_attribute(self, name):
                return self.attrs.get(name)

            def find_elements(self, by, selector):
                if '#text1' in selector or 'input[id=\"text1\"]' in selector:
                    return [self.text1]
                if '#advanced-search-btn' in selector or 'button[type=\"submit\"]' in selector or 'input[type=\"submit\"]' in selector:
                    return [self.submit]
                return []

        class _Driver:
            def __init__(self):
                self.current_url = "https://onlinelibrary.wiley.com/search/advanced?publication=15213773"
                self.title = "Advanced Search - Wiley Online Library"
                self.page_source = """
                <html><body>
                  <a href="/doi/10.1002/anie.201410454">Synergetic Spin Crossover and Fluorescence in One-Dimensional Hybrid Complexes</a>
                </body></html>
                """
                self.form = _Form()
                self.js_clicked = 0

            def get(self, _url):
                return None

            def execute_script(self, script, *args):
                if 'click' in script:
                    self.js_clicked += 1
                return None

            def find_elements(self, by, selector):
                if 'form[action*=\"/action/doSearch\"]' in selector:
                    return [self.form]
                return []

            def quit(self):
                return None

        fake_mgr = mock.Mock()
        fake_mgr.launch_browser.return_value = _Driver()

        with mock.patch.object(publisher_search, "ChromeDebugSessionManager", return_value=fake_mgr), \
             mock.patch.object(publisher_search, "_SITE_LIMITER"), \
             mock.patch.object(publisher_search.time, "sleep", return_value=None):
            hits = publisher_search._search_wiley_via_browser("synergetic spin crossover", limit=3)

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].doi, "10.1002/anie.201410454")
        self.assertEqual(fake_mgr.launch_browser.return_value.form.text1.sent, "synergetic spin crossover")
        self.assertEqual(fake_mgr.launch_browser.return_value.js_clicked, 1)

    def test_search_wiley_can_fallback_to_crossref_results(self):
        class _Resp:
            status_code = 403
            url = "https://onlinelibrary.wiley.com/action/doSearch"
            text = "<title>Just a moment...</title>"
            headers = {"content-type": "text/html"}

        fake_client = mock.Mock()
        fake_client.get.return_value = _Resp()
        fake_hits = [
            publisher_search.SearchHit(
                title="Synergetic Spin Crossover and Fluorescence in One-Dimensional Hybrid Complexes",
                doi="10.1002/anie.201410454",
                url="https://onlinelibrary.wiley.com/doi/10.1002/anie.201410454",
                pdf_url="https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/anie.201410454",
                journal="Angewandte Chemie International Edition",
            )
        ]
        with mock.patch.object(publisher_search, "create_http_client", return_value=fake_client), \
             mock.patch.object(publisher_search, "_search_wiley_via_crossref", return_value=fake_hits):
            hits = publisher_search.search_wiley("synergetic spin crossover", limit=3)

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].doi, "10.1002/anie.201410454")

    def test_search_backend_can_use_browser_fallback_for_springer(self):
        class _Resp:
            status_code = 403
            url = "https://link.springer.com/search"
            text = "<title>Just a moment...</title>"
            headers = {"content-type": "text/html"}

        html = """
        <html><body>
          <li class="app-card-open">
            <a href="/article/10.1007/BF00994018">Support-Vector Networks</a>
          </li>
        </body></html>
        """
        fake_client = type("C", (), {"get": lambda self, *args, **kwargs: _Resp()})()
        with mock.patch.object(publisher_search, "create_http_client", return_value=fake_client), \
             mock.patch.object(publisher_search, "_search_springer_via_browser", return_value=publisher_search.parse_springer_search_html(html)):
            hits = publisher_search.search_springer("support-vector networks", limit=3, allow_browser_fallback=True)

        self.assertEqual(len(hits), 1)

    def test_search_springer_can_fallback_to_crossref_results(self):
        class _Resp:
            status_code = 403
            url = "https://link.springer.com/search"
            text = "<title>Just a moment...</title>"
            headers = {"content-type": "text/html"}

        fake_client = mock.Mock()
        fake_client.get.return_value = _Resp()
        fake_hits = [
            publisher_search.SearchHit(
                title="Support-vector networks",
                doi="10.1007/BF00994018",
                url="https://link.springer.com/article/10.1007/BF00994018",
                pdf_url="https://link.springer.com/content/pdf/10.1007/BF00994018.pdf",
                journal="Machine Learning",
                year=1995,
            )
        ]
        with mock.patch.object(publisher_search, "create_http_client", return_value=fake_client), \
             mock.patch.object(publisher_search, "_search_springer_via_crossref", return_value=fake_hits):
            hits = publisher_search.search_springer("support-vector networks", limit=3)

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].doi, "10.1007/BF00994018")

    def test_search_springer_boosts_with_crossref_when_native_results_miss_classic_hit(self):
        html = """
        <html><body>
          <li class="app-card-open">
            <a href="/article/10.1007/s12596-026-03075-5">Support vector machines for indoor visible light positioning</a>
            <span class="app-card-open__metadata">Journal of Optics (2026)</span>
          </li>
        </body></html>
        """
        class _Resp:
            status_code = 200
            url = "https://link.springer.com/search"
            text = html
            headers = {"content-type": "text/html"}

        fake_client = mock.Mock()
        fake_client.get.return_value = _Resp()
        cross_hits = [
            publisher_search.SearchHit(
                title="Support-vector networks",
                doi="10.1007/BF00994018",
                url="https://link.springer.com/article/10.1007/BF00994018",
                pdf_url="https://link.springer.com/content/pdf/10.1007/BF00994018.pdf",
                journal="Machine Learning",
                year=1995,
            )
        ]
        with mock.patch.object(publisher_search, "create_http_client", return_value=fake_client), \
             mock.patch.object(publisher_search, "_search_springer_via_crossref", return_value=cross_hits):
            hits = publisher_search.search_springer("support-vector networks", limit=10)

        self.assertTrue(any(h.doi == "10.1007/BF00994018" for h in hits))

    def test_search_backend_can_use_browser_fallback_for_sciencedirect(self):
        class _Resp:
            status_code = 403
            url = "https://www.sciencedirect.com/search?qs=filtering+antenna"
            text = "<title>Just a moment...</title>"
            headers = {"content-type": "text/html"}

        fake_hits = [
            publisher_search.SearchHit(
                title="Filtering antenna with radiation and filtering functions for wireless applications",
                doi="",
                url="https://www.sciencedirect.com/science/article/pii/S2314717216300873",
                pdf_url="https://www.sciencedirect.com/science/article/pii/S2314717216300873/pdfft?pid=1-s2.0-S2314717216300873-main.pdf",
            )
        ]
        fake_client = mock.Mock()
        fake_client.get.return_value = _Resp()
        with mock.patch.object(publisher_search, "create_http_client", return_value=fake_client), \
             mock.patch.object(publisher_search, "_search_sciencedirect_via_browser", return_value=fake_hits) as browser_mock:
            hits = publisher_search.search_sciencedirect("filtering antenna", limit=3, allow_browser_fallback=True)

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].doi, "")
        browser_mock.assert_called_once()

    def test_search_sciencedirect_via_browser_can_read_live_dom_results(self):
        class _El:
            def __init__(self, href, text):
                self._href = href
                self.text = text

            def get_attribute(self, name):
                if name == "href":
                    return self._href
                return None

        fake_driver = mock.Mock()
        article = _El(
            "https://www.sciencedirect.com/science/article/pii/S2314717216300873",
            "Filtering antenna with radiation and filtering functions for wireless applications",
        )
        article.parent_text = "Journal of Electrical Systems and Information Technology May 2017"
        fake_driver.find_elements.return_value = [
            article,
            _El(
                "https://www.sciencedirect.com/science/article/pii/S2314717216300873/pdfft?pid=1-s2.0-S2314717216300873-main.pdf",
                "View PDF",
            ),
        ]
        fake_mgr = mock.Mock()
        fake_mgr.launch_browser.return_value = fake_driver

        with mock.patch.object(publisher_search, "ChromeDebugSessionManager", return_value=fake_mgr), \
             mock.patch.object(publisher_search, "_SITE_LIMITER"):
            hits = publisher_search._search_sciencedirect_via_browser("filtering antenna", limit=3)

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].title, "Filtering antenna with radiation and filtering functions for wireless applications")
        self.assertIn("pid=", hits[0].pdf_url)
        self.assertEqual(hits[0].journal, "Journal of Electrical Systems and Information Technology")
        self.assertEqual(hits[0].year, 2017)

    def test_search_sciencedirect_dom_metadata_prefers_journal_line_over_access_labels(self):
        class _El:
            def __init__(self, href, text):
                self._href = href
                self.text = text

            def get_attribute(self, name):
                if name == "href":
                    return self._href
                return None

        article = _El(
            "https://www.sciencedirect.com/science/article/pii/S2314717216300873",
            "Filtering antenna with radiation and filtering functions for wireless applications",
        )
        article.parent_text = (
            "Research articleOpen access\n"
            "Filtering antenna with radiation and filtering functions for wireless applications\n"
            "Journal of Electrical Systems and Information TechnologyMay 2017\n"
            "Jagadish Baburao Jadhav Pramod Jagan Deore"
        )
        fake_driver = mock.Mock()
        fake_driver.find_elements.return_value = [article]

        hits = publisher_search.parse_sciencedirect_search_results_dom(fake_driver)
        self.assertEqual(hits[0].journal, "Journal of Electrical Systems and Information Technology")
        self.assertEqual(hits[0].year, 2017)

    def test_search_sciencedirect_via_browser_urlencodes_query(self):
        fake_driver = mock.Mock()
        fake_driver.find_elements.return_value = []
        fake_driver.page_source = "<html></html>"
        fake_mgr = mock.Mock()
        fake_mgr.launch_browser.return_value = fake_driver

        with mock.patch.object(publisher_search, "ChromeDebugSessionManager", return_value=fake_mgr), \
             mock.patch.object(publisher_search, "_SITE_LIMITER"):
            publisher_search._search_sciencedirect_via_browser("a b+c", limit=3)

        fake_driver.get.assert_called_once()
        called_url = fake_driver.get.call_args.args[0]
        self.assertIn("qs=a+b%2Bc", called_url)

    def test_search_sciencedirect_via_browser_waits_for_live_dom_results(self):
        class _El:
            def __init__(self, href, text):
                self._href = href
                self.text = text

            def get_attribute(self, name):
                if name == "href":
                    return self._href
                return None

        fake_driver = mock.Mock()
        fake_driver.page_source = "<html></html>"
        fake_driver.find_elements.side_effect = [
            [],
            [],
            [
                _El(
                    "https://www.sciencedirect.com/science/article/pii/S2314717216300873",
                    "Filtering antenna with radiation and filtering functions for wireless applications",
                ),
                _El(
                    "https://www.sciencedirect.com/science/article/pii/S2314717216300873/pdfft?pid=1-s2.0-S2314717216300873-main.pdf",
                    "View PDF",
                ),
            ],
        ]
        fake_mgr = mock.Mock()
        fake_mgr.launch_browser.return_value = fake_driver

        with mock.patch.object(publisher_search, "ChromeDebugSessionManager", return_value=fake_mgr), \
             mock.patch.object(publisher_search, "_SITE_LIMITER"), \
             mock.patch.object(publisher_search.time, "sleep", return_value=None):
            hits = publisher_search._search_sciencedirect_via_browser("filtering antenna", limit=3)

        self.assertEqual(len(hits), 1)

    def test_browser_fallback_uses_shared_profile_root_name(self):
        fake_driver = mock.Mock()
        fake_driver.page_source = """
        <html><body>
          <li class="app-card-open">
            <a href="/article/10.1007/BF00994018">Support-Vector Networks</a>
          </li>
        </body></html>
        """
        fake_mgr = mock.Mock()
        fake_mgr.launch_browser.return_value = fake_driver

        with mock.patch.object(publisher_search, "ChromeDebugSessionManager", return_value=fake_mgr) as mgr_cls:
            hits = publisher_search._search_springer_via_browser("support-vector networks", limit=3)

        self.assertEqual(len(hits), 1)
        mgr_cls.assert_called_once_with(base_dir=mock.ANY, profile_root_name="chrome-profile")
