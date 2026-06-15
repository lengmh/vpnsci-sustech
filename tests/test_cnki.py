import unittest
import json
from pathlib import Path
import os
import tempfile
from unittest import mock

import pymupdf

from vpnsci_sustech.config import Config
from vpnsci_sustech.models import Paper
from vpnsci_sustech.sources import cnki


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cnki"


class CNKIProbeTests(unittest.TestCase):
    def test_detect_manual_login_required(self):
        html = "<html><body>统一身份认证 登录 中国知网</body></html>"

        self.assertEqual(
            cnki.detect_cnki_page_state(html, "https://login.cnki.net/login"),
            "manual_login_required",
        )

    def test_detect_captcha_required(self):
        html = "<html><body>验证码 滑块 安全验证</body></html>"

        self.assertEqual(
            cnki.detect_cnki_page_state(html, "https://kns.cnki.net/"),
            "captcha_required",
        )

    def test_fixture_page_states_are_classified(self):
        cases = {
            "login_page.html": "manual_login_required",
            "captcha_page.html": "captcha_required",
            "search_results.html": "search_results",
            "detail_page.html": "detail_page",
        }
        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                html = (FIXTURE_DIR / filename).read_text(encoding="utf-8")
                self.assertEqual(
                    cnki.detect_cnki_page_state(html, "https://kns.cnki.net/"),
                    expected,
                )

    def test_search_fixture_parses_to_search_session(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            session = cnki.search_cnki_from_html_file(
                "钙钛矿",
                FIXTURE_DIR / "search_results.html",
                limit=3,
                cache_dir=tmp,
                base_url="https://kns.cnki.net/",
            )

            self.assertEqual(session.source_summary, {"cnki": 1})
            self.assertEqual(session.hits[0].title, "钙钛矿太阳能电池稳定性研究")
            self.assertEqual(session.hits[0].cnki_id, "ABC123")

    def test_detail_fixture_parses_to_paper(self):
        result = cnki.get_cnki_detail(
            "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
            html_file=FIXTURE_DIR / "detail_page.html",
        )

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.paper.title, "钙钛矿太阳能电池稳定性研究")
        self.assertEqual(getattr(result.paper, "cnki_id"), "ABC123")

    def test_parse_detail_prefers_article_title_over_help_widget_title(self):
        html = """
        <html><head>
          <title>量子计算发展现状——2025年全国高等物理基础课程教育学术研讨会大会报告 - 中国知网</title>
        </head><body>
          <div class="title">使用帮助</div>
          <div class="wx-tit">
            <h1>量子计算发展现状——2025年全国高等物理基础课程教育学术研讨会大会报告<span>附视频</span></h1>
            <div id="authorpart" class="author">郭光灿 gcguo@ustc.edu.cn</div>
          </div>
          <div class="top-tip">物理与工程 . 2026 ,36 (03) : 5-15</div>
          <div id="ChDivSummary">摘要：报告介绍量子计算发展现状。</div>
          <a href="https://a.cnki.net/gw/api/get/pdf/ads/v1/pdf/2025/12/inline.pdf">PDF下载</a>
        </body></html>
        """

        paper = cnki.parse_cnki_detail(html, url="https://kns.cnki.net/kcms2/article/abstract?filename=ABC123")

        self.assertEqual(paper.title, "量子计算发展现状——2025年全国高等物理基础课程教育学术研讨会大会报告")
        self.assertEqual(paper.authors, ["郭光灿"])
        self.assertEqual(paper.year, 2026)

    def test_find_cnki_download_url_prefers_real_pdf_button_over_ad_pdf_links(self):
        html = """
        <html><body>
          <a class="but-ad-item-click" target="_blank"
             href="https://a.cnki.net/gw/api/get/pdf/ads/v1/pdf/2025/12/ad.pdf"></a>
          <a href="https://bar.cnki.net/bar/download/order?id=html">HTML阅读</a>
          <a id="cajDown" href="https://bar.cnki.net/bar/download/order?id=caj">CAJ下载</a>
          <a id="pdfDown" href="https://bar.cnki.net/bar/download/order?id=pdf">PDF下载</a>
        </body></html>
        """

        url, fmt = cnki.find_cnki_download_url(html, base_url="https://kns.cnki.net/kcms2/article/abstract?v=x", prefer="pdf")

        self.assertEqual(url, "https://bar.cnki.net/bar/download/order?id=pdf")
        self.assertEqual(fmt, "pdf")

    def test_detect_search_results(self):
        html = "<html><body><div class='result-table-list'><a>论文题名</a></div></body></html>"

        self.assertEqual(
            cnki.detect_cnki_page_state(html, "https://kns.cnki.net/kns8s/defaultresult/index"),
            "search_results",
        )

    def test_detect_detail_page(self):
        html = "<html><body><h1 class='title'>论文题名</h1><div id='ChDivSummary'>摘要</div></body></html>"

        self.assertEqual(
            cnki.detect_cnki_page_state(html, "https://kns.cnki.net/kcms2/article/abstract?v=x"),
            "detail_page",
        )

    def test_detect_detail_page_wins_over_residual_captcha_text_when_download_link_exists(self):
        html = """
        <html><body>
          <h1 class="title">论文题名</h1>
          <div id="ChDivSummary">摘要</div>
          <a href="https://bar.cnki.net/bar/download/order?id=ABC">PDF下载</a>
          <script>var captchaLabel = "验证码";</script>
        </body></html>
        """

        self.assertEqual(
            cnki.detect_cnki_page_state(html, "https://kns.cnki.net/kcms2/article/abstract?v=x"),
            "detail_page",
        )

    def test_extract_cnki_identifiers_from_url(self):
        ids = cnki.extract_cnki_identifiers(
            "https://kns.cnki.net/kcms2/article/abstract?v=x&filename=ABC123&dbname=CJFDLAST2024&dbcode=CJFD"
        )

        self.assertEqual(ids["filename"], "ABC123")
        self.assertEqual(ids["dbname"], "CJFDLAST2024")
        self.assertEqual(ids["dbcode"], "CJFD")

    def test_fsso_login_url_is_not_accepted_as_cnki_automation_target(self):
        self.assertFalse(cnki.is_cnki_url("https://fsso.cnki.net/login"))
        self.assertFalse(cnki.is_cnki_url("https://login.cnki.net/login"))
        self.assertTrue(cnki.is_cnki_url("https://kns.cnki.net/kcms2/article/abstract?filename=ABC123"))

        result = cnki.run_visible_browser_smoke(
            detail_url="https://fsso.cnki.net/login",
            dry_run=True,
        )

        self.assertEqual(result.status, "invalid_url")

    def test_visible_smoke_dry_run_does_not_launch_browser_and_bounds_limit(self):
        result = cnki.run_visible_browser_smoke(
            query="钙钛矿",
            limit=99,
            dry_run=True,
            driver_factory=mock.Mock(side_effect=AssertionError("browser should not launch")),
        )

        self.assertEqual(result.status, "dry_run")
        self.assertTrue(result.dry_run)
        self.assertEqual(result.limit, 3)
        self.assertIn("kw=", result.search_url)
        self.assertTrue(any("不会下载文件" in warning for warning in result.warnings))

    def test_visible_smoke_requires_confirmation_before_live_access(self):
        factory = mock.Mock(side_effect=AssertionError("browser should not launch"))

        result = cnki.run_visible_browser_smoke(
            detail_url="https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
            dry_run=False,
            confirm_live_access=False,
            driver_factory=factory,
        )

        self.assertEqual(result.status, "confirmation_required")
        factory.assert_not_called()

    def test_visible_smoke_rejects_non_cnki_url(self):
        result = cnki.run_visible_browser_smoke(
            detail_url="https://example.com/paper",
            dry_run=True,
        )

        self.assertEqual(result.status, "invalid_url")
        self.assertIn("CNKI", result.next_action)

    def test_visible_smoke_live_with_fake_driver_parses_search_snapshot(self):
        class FakeDriver:
            current_url = "https://kns.cnki.net/kns8s/defaultresult/index"
            page_source = """
            <html><body><table class="result-table-list">
              <tr>
                <td class="name"><a href="/kcms2/article/abstract?filename=ABC123&dbcode=CJFD">题名一</a></td>
                <td class="author">张三</td>
                <td class="source">期刊一</td>
                <td class="date">2024</td>
              </tr>
            </table></body></html>
            """

            def __init__(self):
                self.visited = []
                self.closed = False

            def get(self, url):
                self.visited.append(url)

            def quit(self):
                self.closed = True

        driver = FakeDriver()

        result = cnki.run_visible_browser_smoke(
            query="钙钛矿",
            limit=1,
            dry_run=False,
            confirm_live_access=True,
            driver_factory=lambda: driver,
        )

        self.assertEqual(result.status, "search_results")
        self.assertEqual(len(result.hits), 1)
        self.assertEqual(result.hits[0].cnki_id, "ABC123")
        self.assertTrue(driver.visited)
        self.assertTrue(driver.closed)

    def test_parse_cnki_search_results_extracts_metadata(self):
        html = """
        <table class="result-table-list">
          <tr>
            <td class="name">
              <a href="/kcms2/article/abstract?v=x&filename=ABC123&dbname=CJFDLAST2024&dbcode=CJFD">钙钛矿太阳能电池稳定性研究</a>
            </td>
            <td class="author">张三; 李四</td>
            <td class="source">太阳能学报</td>
            <td class="date">2024-05-01</td>
            <td class="download"><a href="/download/article?id=ABC123">PDF下载</a></td>
          </tr>
        </table>
        """

        hits = cnki.parse_cnki_search_results(html, base_url="https://kns.cnki.net/")

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].title, "钙钛矿太阳能电池稳定性研究")
        self.assertEqual(hits[0].authors, ["张三", "李四"])
        self.assertEqual(hits[0].journal, "太阳能学报")
        self.assertEqual(hits[0].year, 2024)
        self.assertEqual(hits[0].cnki_id, "ABC123")
        self.assertEqual(hits[0].source_url, "https://kns.cnki.net/kcms2/article/abstract?v=x&filename=ABC123&dbname=CJFDLAST2024&dbcode=CJFD")
        self.assertEqual(hits[0].backend, "cnki")
        self.assertIn("cnki", hits[0].sources)

    def test_parse_cnki_detail_extracts_paper(self):
        html = """
        <html>
          <h1 class="title">钙钛矿太阳能电池稳定性研究</h1>
          <div class="author"><span>张三</span><span>李四</span></div>
          <div class="sourinfo">太阳能学报 2024年 第5期</div>
          <span id="ChDivSummary">摘要：本文研究稳定性。</span>
          <p class="keywords">关键词：钙钛矿; 太阳能电池; 稳定性</p>
          <a id="pdfDown" href="/download?filename=ABC123&dbcode=CJFD">PDF下载</a>
        </html>
        """

        paper = cnki.parse_cnki_detail(
            html,
            url="https://kns.cnki.net/kcms2/article/abstract?v=x&filename=ABC123&dbname=CJFDLAST2024&dbcode=CJFD",
        )

        self.assertEqual(paper.title, "钙钛矿太阳能电池稳定性研究")
        self.assertEqual(paper.authors, ["张三", "李四"])
        self.assertEqual(paper.journal, "太阳能学报")
        self.assertEqual(paper.year, 2024)
        self.assertIn("本文研究稳定性", paper.abstract)
        self.assertEqual(getattr(paper, "cnki_id"), "ABC123")
        self.assertEqual(paper.source, "cnki")

    def test_get_cnki_detail_from_html_parses_without_network(self):
        html = """
        <html><body>
          <h1 class="title">题名详情</h1>
          <div class="author">王五; 赵六</div>
          <div class="sourinfo">测试期刊 2023</div>
          <div id="ChDivSummary">摘要：详情摘要</div>
        </body></html>
        """

        result = cnki.get_cnki_detail(
            "https://kns.cnki.net/kcms2/article/abstract?filename=DEF456",
            html=html,
        )

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.paper.title, "题名详情")
        self.assertEqual(getattr(result.paper, "cnki_id"), "DEF456")

    def test_get_cnki_detail_without_html_is_gated(self):
        result = cnki.get_cnki_detail("DEF456")

        self.assertEqual(result.status, "live_access_not_enabled")
        self.assertIn("filename=DEF456", result.url)

    def test_get_cnki_detail_rejects_non_cnki_url(self):
        result = cnki.get_cnki_detail("https://example.com/detail", html="<html></html>")

        self.assertEqual(result.status, "invalid_url")

    def test_search_cnki_from_html_saves_session_without_network(self):
        html = """
        <table class="result-table-list">
          <tr>
            <td class="name"><a href="/kcms2/article/abstract?filename=ABC123&dbcode=CJFD">题名一</a></td>
            <td class="author">张三</td>
            <td class="source">期刊一</td>
            <td class="date">2024</td>
          </tr>
        </table>
        """

        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            session = cnki.search_cnki_from_html(
                "钙钛矿",
                html,
                limit=3,
                cache_dir=Path(tmp),
                base_url="https://kns.cnki.net/",
            )

            self.assertEqual(session.query, "钙钛矿")
            self.assertEqual(session.source_summary, {"cnki": 1})
            self.assertEqual(session.hits[0].title, "题名一")
            saved = Path(tmp) / "search" / "sessions" / f"{session.session_id}.json"
            self.assertTrue(saved.exists())

    def test_search_cnki_from_html_file_saves_session_without_network(self):
        html = """
        <table class="result-table-list">
          <tr>
            <td class="name"><a href="/kcms2/article/abstract?filename=ABC123&dbcode=CJFD">题名一</a></td>
            <td class="author">张三</td>
            <td class="source">期刊一</td>
            <td class="date">2024</td>
          </tr>
        </table>
        """

        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            html_file = Path(tmp) / "search.html"
            html_file.write_text(html, encoding="utf-8")

            session = cnki.search_cnki_from_html_file(
                "钙钛矿",
                html_file,
                limit=1,
                cache_dir=tmp,
                base_url="https://kns.cnki.net/",
            )

            self.assertEqual(session.source_summary, {"cnki": 1})
            self.assertEqual(session.hits[0].cnki_id, "ABC123")

    def test_search_cnki_from_html_returns_blocked_session_for_login_page(self):
        html = "<html><body>统一身份认证 用户登录</body></html>"

        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            session = cnki.search_cnki_from_html(
                "钙钛矿",
                html,
                cache_dir=Path(tmp),
            )

            self.assertEqual(session.hits, [])
            self.assertEqual(session.errors[0].code, "manual_login_required")

    def test_wait_for_cnki_download_accepts_caj_and_ignores_partial_files(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            download_dir = Path(tmp)
            (download_dir / "paper.caj.crdownload").write_bytes(b"partial")
            self.assertIsNone(cnki.wait_for_cnki_download(download_dir, timeout=0))

            (download_dir / "paper.caj.crdownload").unlink()
            caj = download_dir / "paper.caj"
            caj.write_bytes(b"caj-content")

            result = cnki.wait_for_cnki_download(download_dir, timeout=0)

            self.assertIsNotNone(result)
            self.assertEqual(result.path, caj)
            self.assertEqual(result.format, "caj")
            self.assertEqual(result.content, b"caj-content")

    def test_wait_for_cnki_download_returns_new_complete_file_when_old_file_exists(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            download_dir = Path(tmp)
            old_pdf = download_dir / "old.pdf"
            old_pdf.write_bytes(b"%PDF-old")
            before = cnki.snapshot_cnki_download_dir(download_dir)

            self.assertIsNone(cnki.wait_for_cnki_download(download_dir, timeout=0, before=before))

            new_pdf = download_dir / "new.pdf"
            new_pdf.write_bytes(b"%PDF-new")
            result = cnki.wait_for_cnki_download(download_dir, timeout=0, before=before)

            self.assertIsNotNone(result)
            self.assertEqual(result.path, new_pdf)
            self.assertEqual(result.content, b"%PDF-new")

    def test_wait_for_cnki_download_returns_changed_file_when_same_name_changes(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            download_dir = Path(tmp)
            pdf = download_dir / "same-name.pdf"
            pdf.write_bytes(b"%PDF-old")
            old_mtime = 1_700_000_000
            os.utime(pdf, (old_mtime, old_mtime))
            before = cnki.snapshot_cnki_download_dir(download_dir)

            pdf.write_bytes(b"%PDF-new-content")
            new_mtime = old_mtime + 10
            os.utime(pdf, (new_mtime, new_mtime))
            result = cnki.wait_for_cnki_download(download_dir, timeout=0, before=before)

            self.assertIsNotNone(result)
            self.assertEqual(result.path, pdf)
            self.assertEqual(result.content, b"%PDF-new-content")

    def test_save_cnki_downloaded_artifact_uses_filename_policy_and_marks_non_pdf_unextracted(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = Config(output_dir=tmp, cache_dir=tmp, paper_filename_policy="title_author")
            paper = Paper(title="钙钛矿太阳能电池稳定性研究", authors=["张三"], source="cnki")
            setattr(paper, "cnki_id", "ABC123")
            downloaded = cnki.DownloadedArtifact(
                content=b"caj-content",
                path=Path(tmp) / "source.caj",
                format="caj",
                source_url="https://kns.cnki.net/download?filename=ABC123",
            )

            artifact = cnki.save_cnki_downloaded_artifact(paper, downloaded, config=cfg)

            self.assertEqual(Path(artifact.path).name, "钙钛矿太阳能电池稳定性研究 - 张三.caj")
            self.assertEqual(artifact.format, "caj")
            self.assertEqual(artifact.kind, "source_file")
            self.assertFalse(artifact.text_extracted)
            self.assertIn("未解析全文", artifact.note)
            self.assertEqual(paper.pdf_path, "")
            self.assertEqual(len(paper.artifacts), 1)

    def test_save_cnki_downloaded_artifact_allows_explicit_filename_policy_override(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = Config(output_dir=tmp, cache_dir=tmp, paper_filename_policy="identifier")
            paper = Paper(title="钙钛矿太阳能电池稳定性研究", authors=["张三"], source="cnki")
            setattr(paper, "cnki_id", "ABC123")
            downloaded = cnki.DownloadedArtifact(
                content=b"caj-content",
                path=Path(tmp) / "source.caj",
                format="caj",
            )

            artifact = cnki.save_cnki_downloaded_artifact(
                paper,
                downloaded,
                config=cfg,
                filename_policy="title_year_author",
            )

            self.assertEqual(Path(artifact.path).name, "钙钛矿太阳能电池稳定性研究 - 张三.caj")
            self.assertNotEqual(Path(artifact.path).name, "ABC123.caj")

    def test_caj_conversion_is_disabled_by_default(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = Config(output_dir=tmp, cache_dir=tmp, paper_filename_policy="title_author")
            paper = Paper(title="CNKI Source", authors=["Li"], source="cnki")
            downloaded = cnki.DownloadedArtifact(
                content=b"caj-content",
                path=Path(tmp) / "source.caj",
                format="caj",
            )

            with mock.patch.object(cnki.subprocess, "run", side_effect=AssertionError("converter should not run")):
                artifact = cnki.save_cnki_downloaded_artifact(paper, downloaded, config=cfg)

            self.assertEqual(artifact.format, "caj")
            self.assertEqual(len(paper.artifacts), 1)
            self.assertEqual(paper.pdf_path, "")

    def test_caj_conversion_success_adds_converted_pdf_artifact(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = Config(
                output_dir=tmp,
                cache_dir=tmp,
                paper_filename_policy="title_author",
                cnki_convert_caj_to_pdf=True,
                cnki_caj_converter_command="fake-convert {input} {output}",
            )
            paper = Paper(title="CNKI Source", authors=["Li"], source="cnki")
            downloaded = cnki.DownloadedArtifact(
                content=b"caj-content",
                path=Path(tmp) / "source.caj",
                format="caj",
            )

            def fake_run(command, **kwargs):
                output = Path(command[-1])
                doc = pymupdf.open()
                page = doc.new_page()
                page.insert_text((72, 72), "Converted CNKI full text")
                doc.save(output)
                doc.close()
                return mock.Mock(returncode=0, stdout="", stderr="")

            with mock.patch.object(cnki.subprocess, "run", side_effect=fake_run) as run_mock:
                artifact = cnki.save_cnki_downloaded_artifact(paper, downloaded, config=cfg)

            self.assertEqual(artifact.format, "caj")
            self.assertEqual(len(paper.artifacts), 2)
            converted = paper.artifacts[1]
            self.assertEqual(converted.kind, "converted_pdf")
            self.assertEqual(Path(converted.path).suffix.lower(), ".pdf")
            self.assertEqual(paper.pdf_path, converted.path)
            self.assertTrue(converted.text_extracted)
            self.assertIn("Converted CNKI full text", paper.full_text)
            run_mock.assert_called_once()

    def test_caj_conversion_failure_keeps_original_artifact_success(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = Config(
                output_dir=tmp,
                cache_dir=tmp,
                paper_filename_policy="title_author",
                cnki_convert_caj_to_pdf=True,
                cnki_caj_converter_command="fake-convert {input} {output}",
            )
            paper = Paper(title="CNKI Source", authors=["Li"], source="cnki")
            downloaded = cnki.DownloadedArtifact(
                content=b"caj-content",
                path=Path(tmp) / "source.caj",
                format="caj",
            )

            with mock.patch.object(cnki.subprocess, "run", return_value=mock.Mock(returncode=2, stdout="", stderr="boom")):
                artifact = cnki.save_cnki_downloaded_artifact(paper, downloaded, config=cfg)

            self.assertEqual(artifact.format, "caj")
            self.assertEqual(len(paper.artifacts), 1)
            self.assertIn("转 PDF 失败", artifact.note)
            self.assertEqual(paper.pdf_path, "")

    def test_caj_conversion_missing_placeholder_keeps_original_artifact_success(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = Config(
                output_dir=tmp,
                cache_dir=tmp,
                paper_filename_policy="title_author",
                cnki_convert_caj_to_pdf=True,
                cnki_caj_converter_command="fake-convert {input}",
            )
            paper = Paper(title="CNKI Source", authors=["Li"], source="cnki")
            downloaded = cnki.DownloadedArtifact(
                content=b"caj-content",
                path=Path(tmp) / "source.caj",
                format="caj",
            )

            with mock.patch.object(cnki.subprocess, "run", side_effect=AssertionError("converter should not run")):
                artifact = cnki.save_cnki_downloaded_artifact(paper, downloaded, config=cfg)

            self.assertEqual(artifact.format, "caj")
            self.assertEqual(len(paper.artifacts), 1)
            self.assertIn("{input} 和 {output}", artifact.note)
            self.assertEqual(paper.pdf_path, "")

    def test_save_cnki_downloaded_pdf_sets_pdf_path_and_extracted_flag(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = Config(output_dir=tmp, cache_dir=tmp, paper_filename_policy="title_author")
            pdf_path = Path(tmp) / "source.pdf"
            doc = pymupdf.open()
            page = doc.new_page()
            page.insert_text((72, 72), "CNKI PDF text")
            doc.save(pdf_path)
            doc.close()
            paper = Paper(title="CNKI PDF", authors=["Zhang"], source="cnki")
            downloaded = cnki.DownloadedArtifact(
                content=pdf_path.read_bytes(),
                path=pdf_path,
                format="pdf",
                source_url="https://kns.cnki.net/download?filename=ABC123",
            )

            artifact = cnki.save_cnki_downloaded_artifact(paper, downloaded, config=cfg)

            self.assertEqual(Path(artifact.path).name, "CNKI PDF - Zhang.pdf")
            self.assertEqual(paper.pdf_path, artifact.path)
            self.assertTrue(artifact.text_extracted)

    def test_save_cnki_downloaded_invalid_pdf_marks_unextracted(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = Config(output_dir=tmp, cache_dir=tmp, paper_filename_policy="title_author")
            paper = Paper(title="CNKI PDF", authors=["Zhang"], source="cnki")
            downloaded = cnki.DownloadedArtifact(
                content=b"%PDF-1.4",
                path=Path(tmp) / "source.pdf",
                format="pdf",
                source_url="https://kns.cnki.net/download?filename=ABC123",
            )

            artifact = cnki.save_cnki_downloaded_artifact(paper, downloaded, config=cfg)

            self.assertFalse(artifact.text_extracted)
            self.assertIn("未能提取全文", artifact.note)

    def test_save_cnki_downloaded_pdf_extracts_full_text(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = Config(output_dir=tmp, cache_dir=tmp, paper_filename_policy="title_author")
            pdf_path = Path(tmp) / "source.pdf"
            doc = pymupdf.open()
            page = doc.new_page()
            page.insert_text((72, 72), "CNKI PDF extracted text")
            doc.save(pdf_path)
            doc.close()
            paper = Paper(title="CNKI PDF", authors=["Zhang"], source="cnki")
            downloaded = cnki.DownloadedArtifact(
                content=pdf_path.read_bytes(),
                path=pdf_path,
                format="pdf",
                source_url="https://kns.cnki.net/download?filename=ABC123",
            )

            artifact = cnki.save_cnki_downloaded_artifact(paper, downloaded, config=cfg)

            self.assertTrue(artifact.text_extracted)
            self.assertIn("CNKI PDF extracted text", paper.full_text)

    def test_cnki_client_download_from_existing_file_does_not_use_network(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = Config(output_dir=str(Path(tmp) / "out"), cache_dir=tmp, paper_filename_policy="title_author")
            source = Path(tmp) / "download.cajx"
            source.write_bytes(b"cajx-content")
            paper = Paper(title="CNKI Source", authors=["Li"], source="cnki")
            client = cnki.CNKIClient(cfg)

            with mock.patch.object(client, "_open_browser_for_download", side_effect=AssertionError("network/browser should not run")):
                artifact = client.materialize_downloaded_file(
                    paper,
                    source,
                    source_url="https://kns.cnki.net/download?filename=XYZ",
                )

            self.assertEqual(Path(artifact.path).suffix.lower(), ".cajx")
            self.assertFalse(artifact.text_extracted)

    def test_cnki_client_live_download_requires_confirmation(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = Config(output_dir=str(Path(tmp) / "out"), cache_dir=tmp)
            client = cnki.CNKIClient(cfg)
            factory = mock.Mock(side_effect=AssertionError("browser should not launch"))

            with self.assertRaisesRegex(RuntimeError, "confirmation_required"):
                client.download_cnki_artifact(
                    Paper(source="cnki"),
                    "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                    confirm_live_access=False,
                    driver_factory=factory,
                )

            factory.assert_not_called()

    def test_cnki_client_live_download_blocks_on_captcha(self):
        class FakeDriver:
            current_url = "https://kns.cnki.net/verify/home"
            page_source = "<html><body>验证码 滑块 安全验证</body></html>"

            def __init__(self):
                self.visited = []
                self.closed = False

            def get(self, url):
                self.visited.append(url)

            def quit(self):
                self.closed = True

        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = Config(output_dir=str(Path(tmp) / "out"), cache_dir=tmp)
            client = cnki.CNKIClient(cfg)
            driver = FakeDriver()

            with self.assertRaisesRegex(RuntimeError, "captcha_required"):
                client.download_cnki_artifact(
                    Paper(source="cnki"),
                    "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                    confirm_live_access=True,
                    driver_factory=lambda: driver,
                    download_dir=Path(tmp) / "downloads",
                    timeout=0,
                )

            self.assertTrue(driver.visited)
            self.assertTrue(driver.closed)
            self.assertEqual(list((Path(tmp) / "out").glob("*")), [])

    def test_cnki_client_live_download_with_fake_driver_saves_artifact(self):
        class FakeDriver:
            def __init__(self, download_dir: Path):
                self.download_dir = download_dir
                self.visited = []
                self.clicked = []
                self.closed = False
                self.current_url = ""
                self.page_source = ""

            def get(self, url):
                self.visited.append(url)
                self.current_url = url
                if "download" in url:
                    self.download_dir.mkdir(parents=True, exist_ok=True)
                    (self.download_dir / "paper.caj").write_bytes(b"caj-content")
                    self.page_source = "<html><body>download started</body></html>"
                    return
                self.page_source = """
                <html><body>
                  <h1 class="title">CNKI Live Paper</h1>
                  <div class="author">Zhang</div>
                  <div id="ChDivSummary">摘要：live smoke</div>
                  <a id="cajDown" href="/download?filename=ABC123&format=caj">CAJ下载</a>
                </body></html>
                """

            def find_elements(self, by, value):
                class Element:
                    def __init__(self, driver):
                        self.driver = driver

                    def click(self):
                        self.driver.clicked.append("cajDown")
                        self.driver.get("https://kns.cnki.net/download?filename=ABC123&format=caj")

                if value == "cajDown":
                    return [Element(self)]
                return []

            def quit(self):
                self.closed = True

        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            output_dir = Path(tmp) / "out"
            download_dir = Path(tmp) / "downloads"
            cfg = Config(output_dir=str(output_dir), cache_dir=tmp, paper_filename_policy="title_author")
            client = cnki.CNKIClient(cfg)
            driver = FakeDriver(download_dir)

            paper = Paper(source="cnki")
            artifact = client.download_cnki_artifact(
                paper,
                "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                prefer="caj",
                confirm_live_access=True,
                driver_factory=lambda: driver,
                download_dir=download_dir,
                timeout=0,
            )

            self.assertEqual(Path(artifact.path).parent, output_dir)
            self.assertEqual(Path(artifact.path).name, "CNKI Live Paper - Zhang.caj")
            self.assertEqual(artifact.format, "caj")
            self.assertFalse(artifact.text_extracted)
            self.assertEqual(getattr(paper, "cnki_id"), "ABC123")
            self.assertEqual(driver.clicked, ["cajDown"])
            self.assertIn("/download?filename=ABC123&format=caj", driver.visited[-1])
            self.assertTrue(driver.closed)

    def test_cnki_client_live_download_resumes_after_manual_captcha_completion(self):
        class FakeElement:
            text = "PDF下载"

            def __init__(self, driver):
                self.driver = driver

            def get_attribute(self, name):
                return self.driver.download_url if name == "href" else ""

            def is_displayed(self):
                return True

            def click(self):
                self.driver.clicked.append("PDF下载")
                self.driver.current_url = "https://bar.cnki.net/bar/verify/index.html"
                self.driver.page_source = "<html><body>拼图校验 安全验证</body></html>"

        class FakeDriver:
            def __init__(self, download_dir: Path):
                self.download_dir = download_dir
                self.clicked = []
                self.closed = False
                self.poll_count = 0
                self.current_url = "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123"
                self.download_url = "https://bar.cnki.net/bar/download/order?id=pdf-real"
                self.page_source = f"""
                <html><body>
                  <h1 class="title">Captcha Resume Paper</h1>
                  <div class="author">Wang</div>
                  <div id="ChDivSummary">摘要</div>
                  <a id="pdfDown" href="{self.download_url}">PDF下载</a>
                </body></html>
                """

            def find_elements(self, by, value):
                return [FakeElement(self)]

            def get(self, url):
                self.current_url = url

            def refresh(self):
                self.poll_count += 1
                if self.poll_count == 2:
                    self.current_url = "https://bar.cnki.net/bar/verify/verifySuccess.html"
                    self.page_source = "<html><body>verifySuccess</body></html>"
                    self.download_dir.mkdir(parents=True, exist_ok=True)
                    doc = pymupdf.open()
                    page = doc.new_page()
                    page.insert_text((72, 72), "captcha resume pdf text")
                    doc.save(self.download_dir / "paper.pdf")
                    doc.close()

            def quit(self):
                self.closed = True

        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            download_dir = Path(tmp) / "downloads"
            cfg = Config(output_dir=str(Path(tmp) / "out"), cache_dir=tmp, paper_filename_policy="title_author")
            driver = FakeDriver(download_dir)
            client = cnki.CNKIClient(cfg)

            artifact = client.download_cnki_artifact(
                Paper(source="cnki"),
                driver.current_url,
                prefer="pdf",
                confirm_live_access=True,
                mode="attach",
                driver_factory=lambda: driver,
                download_dir=download_dir,
                timeout=5,
            )

            self.assertEqual(driver.clicked, ["PDF下载"])
            self.assertGreaterEqual(driver.poll_count, 2)
            self.assertEqual(Path(artifact.path).name, "Captcha Resume Paper - Wang.pdf")
            self.assertIn("resumed_after_captcha", artifact.note)
            self.assertTrue(driver.closed)

    def test_cnki_client_live_download_reports_captcha_timeout(self):
        class FakeElement:
            text = "PDF下载"

            def __init__(self, driver):
                self.driver = driver

            def get_attribute(self, name):
                return self.driver.download_url if name == "href" else ""

            def is_displayed(self):
                return True

            def click(self):
                self.driver.current_url = "https://bar.cnki.net/bar/verify/index.html"
                self.driver.page_source = "<html><body>拼图校验 安全验证</body></html>"

        class FakeDriver:
            def __init__(self):
                self.current_url = "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123"
                self.download_url = "https://bar.cnki.net/bar/download/order?id=pdf-real"
                self.page_source = f"""
                <html><body>
                  <h1 class="title">Captcha Timeout Paper</h1>
                  <div class="author">Wang</div>
                  <div id="ChDivSummary">摘要</div>
                  <a id="pdfDown" href="{self.download_url}">PDF下载</a>
                </body></html>
                """
                self.closed = False

            def find_elements(self, by, value):
                return [FakeElement(self)]

            def get(self, url):
                self.current_url = url

            def refresh(self):
                self.current_url = "https://bar.cnki.net/bar/verify/index.html"
                self.page_source = "<html><body>拼图校验 安全验证</body></html>"

            def quit(self):
                self.closed = True

        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            download_dir = Path(tmp) / "downloads"
            cfg = Config(output_dir=str(Path(tmp) / "out"), cache_dir=tmp, paper_filename_policy="title_author")
            driver = FakeDriver()
            client = cnki.CNKIClient(cfg)

            with self.assertRaisesRegex(RuntimeError, "captcha_timeout"):
                client.download_cnki_artifact(
                    Paper(source="cnki"),
                    driver.current_url,
                    prefer="pdf",
                    confirm_live_access=True,
                    mode="attach",
                    driver_factory=lambda: driver,
                    download_dir=download_dir,
                    timeout=0,
                )

            self.assertTrue(driver.closed)

    def test_cnki_batch_download_throttles_cools_and_persists_state(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = Config(output_dir=str(Path(tmp) / "out"), cache_dir=tmp, paper_filename_policy="title_author")
            client = cnki.CNKIClient(cfg)
            sleeps: list[float] = []
            calls: list[str] = []

            def fake_download(paper, detail_url, **kwargs):
                calls.append(detail_url)
                out = Path(tmp) / "out" / f"{getattr(paper, 'cnki_id', '')}.pdf"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(b"%PDF-1.4\n")
                return cnki.Artifact(
                    path=str(out),
                    format="pdf",
                    kind="fulltext",
                    source_url=detail_url,
                    text_extracted=False,
                    note="",
                )

            items = [
                cnki.CNKIBatchItem(
                    detail_url=f"https://kns.cnki.net/kcms2/article/abstract?filename=ABC12{i}",
                    title=f"Paper {i}",
                    first_author="Li",
                    cnki_id=f"ABC12{i}",
                )
                for i in range(1, 4)
            ]

            with mock.patch.object(client, "download_cnki_artifact", side_effect=fake_download):
                result = client.download_cnki_batch(
                    items,
                    confirm_live_access=True,
                    min_interval_seconds=1.0,
                    cooldown_every=2,
                    cooldown_seconds=5.0,
                    sleeper=sleeps.append,
                )

            self.assertEqual(result.status, "completed")
            self.assertEqual(calls, [item.detail_url for item in items])
            self.assertEqual(sleeps, [1.0, 5.0])
            self.assertTrue(result.state_path.exists())
            self.assertEqual([entry.status for entry in result.entries], ["succeeded", "succeeded", "succeeded"])
            self.assertIn("Paper 1", result.state_path.read_text(encoding="utf-8"))

    def test_cnki_batch_download_stops_after_failure_and_resume_skips_finished_entries(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = Config(output_dir=str(Path(tmp) / "out"), cache_dir=tmp, paper_filename_policy="title_author")
            client = cnki.CNKIClient(cfg)
            items = [
                cnki.CNKIBatchItem(
                    detail_url=f"https://kns.cnki.net/kcms2/article/abstract?filename=XYZ{i}",
                    title=f"Batch Paper {i}",
                    first_author="Wang",
                    cnki_id=f"XYZ{i}",
                )
                for i in range(1, 4)
            ]
            first_run_calls: list[str] = []

            def first_run_download(paper, detail_url, **kwargs):
                first_run_calls.append(detail_url)
                if detail_url.endswith("XYZ2"):
                    raise RuntimeError("captcha_timeout: 用户未完成验证码")
                out = Path(tmp) / "out" / "first.pdf"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(b"%PDF-1.4\n")
                return cnki.Artifact(path=str(out), format="pdf", kind="fulltext", source_url=detail_url)

            with mock.patch.object(client, "download_cnki_artifact", side_effect=first_run_download):
                first = client.download_cnki_batch(
                    items,
                    confirm_live_access=True,
                    min_interval_seconds=0,
                    max_consecutive_failures=1,
                    sleeper=lambda seconds: None,
                )

            self.assertEqual(first.status, "stopped")
            self.assertEqual(first.stopped_reason, "max_consecutive_failures:1")
            self.assertEqual(first_run_calls, [items[0].detail_url, items[1].detail_url])
            self.assertEqual([entry.status for entry in first.entries], ["succeeded", "failed", "pending"])

            resume_calls: list[str] = []

            def resume_download(paper, detail_url, **kwargs):
                resume_calls.append(detail_url)
                out = Path(tmp) / "out" / "resume.pdf"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(b"%PDF-1.4\n")
                return cnki.Artifact(path=str(out), format="pdf", kind="fulltext", source_url=detail_url)

            with mock.patch.object(client, "download_cnki_artifact", side_effect=resume_download):
                resumed = client.download_cnki_batch(
                    [],
                    confirm_live_access=True,
                    state_file=first.state_path,
                    resume=True,
                    min_interval_seconds=0,
                    max_consecutive_failures=1,
                    sleeper=lambda seconds: None,
                )

            self.assertEqual(resumed.status, "completed_with_failures")
            self.assertEqual(resume_calls, [items[2].detail_url])
            self.assertEqual([entry.status for entry in resumed.entries], ["succeeded", "failed", "succeeded"])

    def test_cnki_batch_download_writes_recovery_sidecar(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = Config(output_dir=str(Path(tmp) / "out"), cache_dir=tmp, paper_filename_policy="title_author")
            client = cnki.CNKIClient(cfg)

            def fake_download(paper, detail_url, **kwargs):
                out = Path(tmp) / "out" / "saved.pdf"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(b"%PDF-1.4\n")
                return cnki.Artifact(path=str(out), format="pdf", kind="fulltext", source_url=detail_url)

            items = [
                cnki.CNKIBatchItem(
                    detail_url="https://kns.cnki.net/kcms2/article/abstract?filename=ABC1",
                    title="Paper 1",
                    first_author="Li",
                    cnki_id="ABC1",
                )
            ]

            with mock.patch.object(client, "download_cnki_artifact", side_effect=fake_download):
                result = client.download_cnki_batch(
                    items,
                    confirm_live_access=True,
                    min_interval_seconds=0,
                    sleeper=lambda seconds: None,
                )

            self.assertIsNotNone(result.sidecar_path)
            self.assertTrue(result.sidecar_path.exists())
            data = json.loads(result.sidecar_path.read_text(encoding="utf-8"))
            self.assertEqual(data["items"][0]["hit_key"], "cnki:ABC1")
            self.assertEqual(data["display_query"], "")
            self.assertEqual(data["recovered_label"], "CNKI 下载结果集合")
            self.assertEqual(data["items"][0]["local_file"], str(Path(tmp) / "out" / "saved.pdf"))
            self.assertEqual(data["report_recovery_capability"], "degraded")

    def test_cnki_batch_sidecar_backfills_hit_key_and_cnki_identifiers_from_detail_url(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = Config(output_dir=str(Path(tmp) / "out"), cache_dir=tmp, paper_filename_policy="title_author")
            client = cnki.CNKIClient(cfg)

            def fake_download(paper, detail_url, **kwargs):
                out = Path(tmp) / "out" / "saved.pdf"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(b"%PDF-1.4\n")
                return cnki.Artifact(path=str(out), format="pdf", kind="fulltext", source_url=detail_url)

            items = [
                cnki.CNKIBatchItem(
                    detail_url="https://kns.cnki.net/kcms2/article/abstract?filename=ABC2&dbcode=CJFD&dbname=CJFDLAST2024",
                    title="Paper 2",
                    first_author="Li",
                    cnki_id="",
                )
            ]

            with mock.patch.object(client, "download_cnki_artifact", side_effect=fake_download):
                result = client.download_cnki_batch(
                    items,
                    confirm_live_access=True,
                    min_interval_seconds=0,
                    sleeper=lambda seconds: None,
                )

            data = json.loads(result.sidecar_path.read_text(encoding="utf-8"))
            self.assertEqual(data["items"][0]["hit_key"], "cnki:ABC2")
            self.assertEqual(data["items"][0]["cnki_id"], "ABC2")
            self.assertEqual(data["items"][0]["dbcode"], "CJFD")
            self.assertEqual(data["items"][0]["dbname"], "CJFDLAST2024")

    def test_cnki_batch_download_with_formal_provenance_writes_standard_sidecar(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = Config(output_dir=str(Path(tmp) / "out"), cache_dir=tmp, paper_filename_policy="title_author")
            client = cnki.CNKIClient(cfg)

            def fake_download(paper, detail_url, **kwargs):
                out = Path(tmp) / "out" / "saved.pdf"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(b"%PDF-1.4\n")
                return cnki.Artifact(path=str(out), format="pdf", kind="fulltext", source_url=detail_url)

            items = [
                cnki.CNKIBatchItem(
                    detail_url="https://kns.cnki.net/kcms2/article/abstract?filename=ABC1",
                    title="Paper 1",
                    first_author="Li",
                    cnki_id="ABC1",
                )
            ]

            with mock.patch.object(client, "download_cnki_artifact", side_effect=fake_download):
                result = client.download_cnki_batch(
                    items,
                    confirm_live_access=True,
                    min_interval_seconds=0,
                    sleeper=lambda seconds: None,
                    root_session_id="search-root",
                    source_session_id="search-source",
                    derived_session_id="search-derived",
                    original_query="滤波耦合器",
                    display_query="滤波耦合器结果集合",
                    actual_queries=[{"source": "CNKI", "queries": ["滤波耦合器"]}],
                )

            data = json.loads(result.sidecar_path.read_text(encoding="utf-8"))
            self.assertEqual(data["report_recovery_capability"], "standard")
            self.assertEqual(data["missing_fields"], [])
            self.assertEqual(data["root_session_id"], "search-root")
            self.assertEqual(data["source_session_id"], "search-source")
            self.assertEqual(data["derived_session_id"], "search-derived")

    def test_search_cnki_marks_gated_request_instead_of_source_execution(self):
        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = Config(cache_dir=tmp)

            session = cnki.search_cnki("钙钛矿", config=cfg)

            self.assertEqual(session.origin["engine"], "cnki")
            self.assertEqual(session.origin["kind"], "gated_request")
            self.assertEqual(session.errors[0].code, "live_access_not_enabled")

    def test_cnki_client_live_download_clicks_visible_pdf_link_when_id_is_cajdown(self):
        class FakeElement:
            def __init__(self, driver, href: str, text: str, displayed: bool = True):
                self.driver = driver
                self.href = href
                self.text = text
                self.displayed = displayed

            def get_attribute(self, name):
                return self.href if name == "href" else ""

            def is_displayed(self):
                return self.displayed

            def click(self):
                self.driver.clicked.append(self.text)
                self.driver.get(self.href)

        class FakeDriver:
            def __init__(self, download_dir: Path):
                self.download_dir = download_dir
                self.clicked = []
                self.visited = []
                self.closed = False
                self.current_url = "https://kns.cnki.net/kcms2/article/abstract?filename=PDF123"
                self.pdf_href = "https://bar.cnki.net/bar/download/order?id=pdf-real"
                self.caj_href = "https://bar.cnki.net/bar/download/order?id=caj-real"
                self.page_source = f"""
                <html><body>
                  <h1 class="title">Visible PDF</h1>
                  <div class="author">Chen</div>
                  <div id="ChDivSummary">摘要</div>
                  <a id="cajDown" href="{self.caj_href}">CAJ下载</a>
                  <a id="cajDown" href="{self.pdf_href}">PDF下载</a>
                </body></html>
                """

            def find_elements(self, by, value):
                if "href" in str(value):
                    return [
                        FakeElement(self, self.caj_href, "CAJ下载"),
                        FakeElement(self, self.pdf_href, "PDF下载"),
                    ]
                return []

            def get(self, url):
                self.visited.append(url)
                self.current_url = url
                if url == self.pdf_href:
                    self.download_dir.mkdir(parents=True, exist_ok=True)
                    doc = pymupdf.open()
                    page = doc.new_page()
                    page.insert_text((72, 72), "visible pdf text")
                    doc.save(self.download_dir / "paper.pdf")
                    doc.close()

            def quit(self):
                self.closed = True

        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            download_dir = Path(tmp) / "downloads"
            cfg = Config(output_dir=str(Path(tmp) / "out"), cache_dir=tmp, paper_filename_policy="title_author")
            driver = FakeDriver(download_dir)
            client = cnki.CNKIClient(cfg)

            artifact = client.download_cnki_artifact(
                Paper(source="cnki"),
                driver.current_url,
                prefer="pdf",
                confirm_live_access=True,
                mode="attach",
                driver_factory=lambda: driver,
                download_dir=download_dir,
                timeout=0,
            )

            self.assertEqual(driver.clicked, ["PDF下载"])
            self.assertEqual(driver.visited, [driver.pdf_href])
            self.assertEqual(Path(artifact.path).name, "Visible PDF - Chen.pdf")
            self.assertTrue(artifact.text_extracted)

    def test_click_cnki_download_button_falls_back_to_script_click(self):
        class FakeElement:
            text = "PDF下载"

            def get_attribute(self, name):
                return "https://bar.cnki.net/bar/download/order?id=pdf" if name == "href" else ""

            def is_displayed(self):
                return True

            def click(self):
                raise RuntimeError("webdriver click did not fire")

        class FakeDriver:
            def __init__(self):
                self.element = FakeElement()
                self.scripts = []
                self.script_clicked = False

            def find_elements(self, by, value):
                return [self.element]

            def execute_script(self, script, *args):
                self.scripts.append(script)
                if "click" in script:
                    self.script_clicked = True

        driver = FakeDriver()

        clicked = cnki._click_cnki_download_button(
            driver,
            "pdf",
            download_url="https://bar.cnki.net/bar/download/order?id=pdf",
        )

        self.assertTrue(clicked)
        self.assertTrue(driver.script_clicked)
        self.assertTrue(any("scrollIntoView" in script for script in driver.scripts))

    def test_cnki_client_attach_download_reuses_current_detail_page_without_reload(self):
        class FakeDriver:
            def __init__(self, download_dir: Path):
                self.download_dir = download_dir
                self.visited = []
                self.closed = False
                self.current_url = "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123"
                self.page_source = """
                <html><body>
                  <h1 class="title">Current Detail</h1>
                  <div class="author">Li</div>
                  <div id="ChDivSummary">摘要</div>
                  <a href="/download?filename=ABC123&format=caj">CAJ下载</a>
                </body></html>
                """

            def get(self, url):
                self.visited.append(url)
                self.download_dir.mkdir(parents=True, exist_ok=True)
                (self.download_dir / "paper.caj").write_bytes(b"caj-content")

            def quit(self):
                self.closed = True

        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            download_dir = Path(tmp) / "downloads"
            cfg = Config(output_dir=str(Path(tmp) / "out"), cache_dir=tmp, paper_filename_policy="title_author")
            driver = FakeDriver(download_dir)
            client = cnki.CNKIClient(cfg)

            artifact = client.download_cnki_artifact(
                Paper(source="cnki"),
                driver.current_url,
                prefer="caj",
                confirm_live_access=True,
                mode="attach",
                driver_factory=lambda: driver,
                download_dir=download_dir,
                timeout=0,
            )

            self.assertEqual(driver.visited, ["https://kns.cnki.net/download?filename=ABC123&format=caj"])
            self.assertEqual(Path(artifact.path).name, "Current Detail - Li.caj")

    def test_cnki_client_live_download_sets_browser_download_dir_via_cdp(self):
        class FakeDriver:
            def __init__(self, download_dir: Path):
                self.download_dir = download_dir
                self.cdp_calls = []
                self.current_url = "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123"
                self.page_source = """
                <html><body>
                  <h1 class="title">CDP Detail</h1>
                  <div id="ChDivSummary">摘要</div>
                  <a href="/download?filename=ABC123&format=pdf">PDF下载</a>
                </body></html>
                """

            def execute_cdp_cmd(self, command, params):
                self.cdp_calls.append((command, params))

            def get(self, url):
                self.download_dir.mkdir(parents=True, exist_ok=True)
                (self.download_dir / "paper.pdf").write_bytes(b"%PDF-1.4")

            def quit(self):
                pass

        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            download_dir = Path(tmp) / "downloads"
            cfg = Config(output_dir=str(Path(tmp) / "out"), cache_dir=tmp)
            driver = FakeDriver(download_dir)
            client = cnki.CNKIClient(cfg)

            client.download_cnki_artifact(
                Paper(source="cnki"),
                driver.current_url,
                prefer="pdf",
                confirm_live_access=True,
                mode="attach",
                driver_factory=lambda: driver,
                download_dir=download_dir,
                timeout=0,
            )

            self.assertIn(
                (
                    "Browser.setDownloadBehavior",
                    {"behavior": "allow", "downloadPath": str(download_dir.resolve())},
                ),
                driver.cdp_calls,
            )

    def test_cnki_client_live_download_materializes_inline_pdf_resource_when_no_file_lands(self):
        class FakeDriver:
            def __init__(self):
                self.current_url = "https://kns.cnki.net/kcms2/article/abstract?filename=ABC123"
                self.page_source = """
                <html><body>
                  <h1 class="title">Inline PDF Detail</h1>
                  <div class="author">Wang</div>
                  <div id="ChDivSummary">摘要</div>
                  <a id="pdfDown" href="https://bar.cnki.net/bar/download/order?id=inline-pdf">PDF下载</a>
                </body></html>
                """
                self.visited = []

                doc = pymupdf.open()
                page = doc.new_page()
                page.insert_text((72, 72), "inline CNKI PDF text")
                self.pdf_bytes = doc.tobytes()
                doc.close()

            def execute_cdp_cmd(self, command, params):
                if command in {"Browser.setDownloadBehavior", "Page.setDownloadBehavior"}:
                    return {}
                if command == "Page.getResourceTree":
                    return {
                        "frameTree": {
                            "frame": {
                                "id": "frame-1",
                                "url": self.current_url,
                                "mimeType": "application/pdf",
                            }
                        }
                    }
                if command == "Page.getResourceContent":
                    import base64

                    return {
                        "base64Encoded": True,
                        "content": base64.b64encode(self.pdf_bytes).decode("ascii"),
                    }
                raise AssertionError(f"unexpected cdp command: {command}")

            def get(self, url):
                self.visited.append(url)
                self.current_url = "https://a.cnki.net/gw/api/get/pdf/v1/pdf/2025/12/inline.pdf"
                self.page_source = "<html><body></body></html>"

            def quit(self):
                pass

        with tempfile.TemporaryDirectory(dir=Path("F:/AI playground/TempFiles")) as tmp:
            cfg = Config(output_dir=str(Path(tmp) / "out"), cache_dir=tmp, paper_filename_policy="title_author")
            driver = FakeDriver()
            client = cnki.CNKIClient(cfg)

            artifact = client.download_cnki_artifact(
                Paper(source="cnki"),
                driver.current_url,
                prefer="pdf",
                confirm_live_access=True,
                mode="attach",
                driver_factory=lambda: driver,
                download_dir=Path(tmp) / "downloads",
                timeout=0,
            )

            self.assertEqual(Path(artifact.path).name, "Inline PDF Detail - Wang.pdf")
            self.assertTrue(artifact.text_extracted)
            self.assertEqual(driver.visited, ["https://bar.cnki.net/bar/download/order?id=inline-pdf"])


if __name__ == "__main__":
    unittest.main()
