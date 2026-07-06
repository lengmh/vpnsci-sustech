from pathlib import Path
import shutil

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py


class build_py(_build_py):
    def run(self):
        super().run()
        self._stage_paper_search_pro()

    def _stage_paper_search_pro(self):
        project_root = Path(__file__).resolve().parent
        src = project_root / "tools" / "paper-search-pro"
        if not src.is_dir():
            raise RuntimeError(f"missing bundled paper-search-pro source: {src}")

        dst = Path(self.build_lib) / "vpnsci_sustech" / "_bundled" / "paper-search-pro"
        if dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst, ignore=self._ignore_paper_search_pro_files(src))

    def _ignore_paper_search_pro_files(self, src_root: Path):
        base_ignore = shutil.ignore_patterns(
            ".git",
            "__pycache__",
            "*.pyc",
            "*.pyo",
            ".pytest_cache",
            "node_modules",
            "paper-search-results",
            ".cache",
        )
        frontend_root = src_root / "assets" / "webartifacts_app" / "paper-report"

        def ignore(directory, names):
            ignored = set(base_ignore(directory, names))
            if Path(directory).resolve() == frontend_root.resolve():
                ignored.add("src")
            return ignored

        return ignore


setup(cmdclass={"build_py": build_py})
