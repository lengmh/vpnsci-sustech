import unittest

from vpnsci_sustech.browser_cdp import supports_browser_pdf_capture, should_capture_pdf_response


class BrowserCdpTests(unittest.TestCase):
    def test_browser_pdf_capture_support_matrix(self):
        self.assertTrue(supports_browser_pdf_capture("https://www.sciencedirect.com/science/article/pii/S123"))
        self.assertTrue(supports_browser_pdf_capture("https://link.springer.com/article/10.1007/BF00994018"))
        self.assertTrue(supports_browser_pdf_capture("https://onlinelibrary.wiley.com/doi/10.1111/j.2517-6161.1996.tb02080.x"))
        self.assertFalse(supports_browser_pdf_capture("https://arxiv.org/abs/1706.03762"))

    def test_pdf_response_capture_is_not_ieee_only(self):
        self.assertTrue(should_capture_pdf_response("https://link.springer.com/content/pdf/10.1007/BF00994018.pdf", "application/pdf"))
        self.assertTrue(should_capture_pdf_response("https://onlinelibrary.wiley.com/doi/pdfdirect/10.1002/anie.201410454", "application/pdf"))
        self.assertTrue(should_capture_pdf_response("https://onlinelibrary.wiley.com/doi/pdf/10.1002/anie.201410454", "application/pdf"))
        self.assertTrue(should_capture_pdf_response("https://pdf.sciencedirectassets.com/123.pdf", "application/pdf"))
        self.assertFalse(should_capture_pdf_response("https://example.com/article", "text/html"))
