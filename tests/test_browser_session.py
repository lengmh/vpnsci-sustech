import tempfile
import unittest
from pathlib import Path
from unittest import mock

from vpnsci_sustech.browser_session import ChromeDebugSessionManager


class BrowserSessionTests(unittest.TestCase):
    def test_default_profile_clone_plan_covers_key_browser_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ChromeDebugSessionManager(base_dir=Path(tmpdir))
            files, dirs = mgr.profile_copy_plan()

        self.assertIn("Cookies", files)
        self.assertIn("Preferences", files)
        self.assertIn("Network", dirs)
        self.assertIn("Local Storage", dirs)

    def test_debug_session_url_uses_localhost_port(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ChromeDebugSessionManager(base_dir=Path(tmpdir), debug_port=9333)
            self.assertEqual(mgr.debug_endpoint(), "http://127.0.0.1:9333")

    def test_should_strip_singleton_locks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ChromeDebugSessionManager(base_dir=Path(tmpdir))
            self.assertIn("SingletonLock", mgr.lock_files())
            self.assertIn("SingletonCookie", mgr.lock_files())
            self.assertIn("SingletonSocket", mgr.lock_files())

    def test_default_source_profile_points_to_local_chrome_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ChromeDebugSessionManager(base_dir=Path(tmpdir))
            path = str(mgr.source_profile_dir()).replace("\\", "/")
            self.assertIn("Google/Chrome/User Data/Default", path)

    def test_build_chrome_options_uses_cloned_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ChromeDebugSessionManager(base_dir=Path(tmpdir), debug_port=9444)
            args = mgr.chrome_arguments()

        self.assertTrue(any("--user-data-dir=" in arg for arg in args))
        self.assertTrue(any("--remote-debugging-port=9444" == arg for arg in args))
        self.assertIn("--disable-blink-features=AutomationControlled", args)

    def test_build_regular_browser_args_omit_debug_port(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ChromeDebugSessionManager(base_dir=Path(tmpdir), debug_port=9444)
            args = mgr.chrome_arguments(enable_debug=False)

        self.assertTrue(any("--user-data-dir=" in arg for arg in args))
        self.assertFalse(any("--remote-debugging-port=" in arg for arg in args))

    def test_profile_root_name_can_be_overridden(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ChromeDebugSessionManager(base_dir=Path(tmpdir), profile_root_name="chrome-profile")

        self.assertEqual(mgr.profile_root(), Path(tmpdir) / "chrome-profile")
        self.assertEqual(mgr.default_profile_dir(), Path(tmpdir) / "chrome-profile" / "Default")

    def test_clone_profile_copies_known_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / "src"
            src.mkdir(parents=True)
            (src / "Cookies").write_text("cookie", encoding="utf-8")
            (src / "Preferences").write_text("prefs", encoding="utf-8")
            (src / "Network").mkdir()
            (src / "Network" / "Cookies").write_text("n", encoding="utf-8")
            mgr = ChromeDebugSessionManager(base_dir=root / "run")
            with mock.patch.object(mgr, "source_profile_dir", return_value=src):
                mgr.clone_profile()

            self.assertTrue((mgr.default_profile_dir() / "Cookies").exists())
            self.assertTrue((mgr.default_profile_dir() / "Preferences").exists())
            self.assertTrue((mgr.default_profile_dir() / "Network").exists())

    def test_prepare_profile_returns_target_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / "src"
            src.mkdir(parents=True)
            mgr = ChromeDebugSessionManager(base_dir=root / "run")
            with mock.patch.object(mgr, "source_profile_dir", return_value=src):
                result = mgr.prepare_profile()

            self.assertEqual(result, mgr.profile_root())

    def test_prepare_profile_clears_stale_clone_before_copying(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / "src"
            src.mkdir(parents=True)
            (src / "Preferences").write_text("prefs", encoding="utf-8")
            mgr = ChromeDebugSessionManager(base_dir=root / "run")
            stale = mgr.default_profile_dir()
            stale.mkdir(parents=True, exist_ok=True)
            (stale / "stale.txt").write_text("old", encoding="utf-8")

            with mock.patch.object(mgr, "source_profile_dir", return_value=src):
                mgr.prepare_profile()

            self.assertFalse((mgr.default_profile_dir() / "stale.txt").exists())
            self.assertTrue((mgr.default_profile_dir() / "Preferences").exists())

    def test_browser_options_can_be_materialized(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ChromeDebugSessionManager(base_dir=Path(tmpdir), debug_port=9444)
            opts = mgr.build_chrome_options(enable_debug=False, extra_args=["--window-size=1400,1000"])

        args = opts.arguments
        self.assertIn("--window-size=1400,1000", args)
        self.assertFalse(any("--remote-debugging-port=" in arg for arg in args))

    def test_browser_options_can_include_prefs_and_capabilities(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ChromeDebugSessionManager(base_dir=Path(tmpdir), debug_port=9444)
            opts = mgr.build_chrome_options(
                enable_debug=False,
                prefs={"download.default_directory": str(Path(tmpdir) / "downloads")},
                capabilities={"goog:loggingPrefs": {"performance": "ALL"}},
            )

        self.assertEqual(opts.experimental_options["prefs"]["download.default_directory"], str(Path(tmpdir) / "downloads"))
        self.assertEqual(opts.capabilities["goog:loggingPrefs"], {"performance": "ALL"})

    def test_launch_helper_uses_prepared_profile_options(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ChromeDebugSessionManager(base_dir=Path(tmpdir), debug_port=9444)
            with mock.patch.object(mgr, "prepare_profile"), \
                 mock.patch("selenium.webdriver.Chrome") as chrome_mock:
                mgr.launch_browser(enable_debug=False, extra_args=["--window-size=1400,1000"])

        chrome_mock.assert_called_once()
