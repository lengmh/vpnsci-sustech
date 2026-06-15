import unittest
from pathlib import Path


class PackagingPhase2Tests(unittest.TestCase):
    def test_pyproject_declares_curl_cffi_dependency(self):
        text = Path("pyproject.toml").read_text(encoding="utf-8")
        self.assertTrue(
            "curl_cffi" in text or "curl-cffi" in text,
            "Phase 2 transport layer uses curl_cffi but pyproject.toml does not declare it.",
        )
