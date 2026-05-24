"""Shared Chrome debug/profile session utilities for Phase 2."""

from dataclasses import dataclass
from pathlib import Path
import shutil
import logging

logger = logging.getLogger(__name__)


@dataclass
class ChromeDebugSessionManager:
    base_dir: Path
    debug_port: int = 9222
    profile_root_name: str = "chrome-debug-profile"

    def source_profile_dir(self) -> Path:
        return Path.home() / "AppData/Local/Google/Chrome/User Data/Default"

    def profile_root(self) -> Path:
        return self.base_dir / self.profile_root_name

    def default_profile_dir(self) -> Path:
        return self.profile_root() / "Default"

    def debug_endpoint(self) -> str:
        return f"http://127.0.0.1:{self.debug_port}"

    def chrome_arguments(self, enable_debug: bool = True) -> list[str]:
        args = [
            f"--user-data-dir={self.profile_root()}",
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
        ]
        if enable_debug:
            args = [
                f"--remote-debugging-port={self.debug_port}",
                f"--remote-allow-origins=http://127.0.0.1:{self.debug_port}",
                *args,
            ]
        return args

    def profile_copy_plan(self) -> tuple[tuple[str, ...], tuple[str, ...]]:
        files_to_copy = (
            "Cookies",
            "Cookies-journal",
            "Preferences",
            "Secure Preferences",
            "History",
            "Visited Links",
            "Web Data",
            "Login Data",
        )
        dirs_to_copy = (
            "Network",
            "Local Storage",
            "Session Storage",
            "IndexedDB",
            "SharedStorage",
            "WebStorage",
        )
        return files_to_copy, dirs_to_copy

    def lock_files(self) -> tuple[str, ...]:
        return ("SingletonLock", "SingletonCookie", "SingletonSocket")

    def clone_profile(self):
        src = self.source_profile_dir()
        dst = self.default_profile_dir()
        dst.mkdir(parents=True, exist_ok=True)
        files_to_copy, dirs_to_copy = self.profile_copy_plan()
        for fname in files_to_copy:
            src_file = src / fname
            if src_file.exists():
                try:
                    shutil.copy2(src_file, dst / fname)
                except OSError as e:
                    logger.warning("Could not copy browser profile file %s: %s", src_file, e)
        for dname in dirs_to_copy:
            src_dir = src / dname
            if src_dir.exists() and src_dir.is_dir():
                try:
                    shutil.copytree(src_dir, dst / dname, dirs_exist_ok=True)
                except OSError as e:
                    logger.warning("Could not copy browser profile directory %s: %s", src_dir, e)
        for lock in self.lock_files():
            try:
                (self.profile_root() / lock).unlink()
            except FileNotFoundError:
                pass

    def prepare_profile(self) -> Path:
        if self.profile_root().exists():
            shutil.rmtree(self.profile_root(), ignore_errors=True)
        self.profile_root().mkdir(parents=True, exist_ok=True)
        self.clone_profile()
        return self.profile_root()

    def build_chrome_options(
        self,
        enable_debug: bool = False,
        extra_args: list[str] | None = None,
        prefs: dict | None = None,
        capabilities: dict | None = None,
    ):
        from selenium.webdriver.chrome.options import Options

        opts = Options()
        for arg in self.chrome_arguments(enable_debug=enable_debug):
            opts.add_argument(arg)
        for arg in extra_args or []:
            opts.add_argument(arg)
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        if prefs:
            opts.add_experimental_option("prefs", prefs)
        for key, value in (capabilities or {}).items():
            opts.set_capability(key, value)
        return opts

    def launch_browser(
        self,
        enable_debug: bool = False,
        extra_args: list[str] | None = None,
        prefs: dict | None = None,
        capabilities: dict | None = None,
    ):
        from selenium import webdriver

        self.prepare_profile()
        opts = self.build_chrome_options(
            enable_debug=enable_debug,
            extra_args=extra_args,
            prefs=prefs,
            capabilities=capabilities,
        )
        return webdriver.Chrome(options=opts)
