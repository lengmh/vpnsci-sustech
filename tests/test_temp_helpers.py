import os
from pathlib import Path
import tempfile
from unittest import mock

from tests.temp_helpers import get_temp_parent


def test_temp_override_owns_only_each_created_directory():
    with tempfile.TemporaryDirectory() as tmp:
        parent = Path(tmp) / "测试 workspace"
        parent.mkdir()
        marker = parent / "keep.txt"
        marker.write_text("keep", encoding="utf-8")
        with mock.patch.dict(os.environ, {"VPNSCI_TEST_TMP": str(parent)}):
            with tempfile.TemporaryDirectory(dir=get_temp_parent()) as first:
                with tempfile.TemporaryDirectory(dir=get_temp_parent()) as second:
                    assert Path(first).parent == parent
                    assert first != second
                    (Path(first) / "论文.txt").write_text("fixture", encoding="utf-8")
            assert not Path(first).exists()
            assert not Path(second).exists()
        assert marker.read_text(encoding="utf-8") == "keep"


def test_legacy_temp_override_remains_supported():
    with tempfile.TemporaryDirectory() as tmp:
        with mock.patch.dict(os.environ, {"VPNSCI_TEST_TMP": "", "VPN_SCI_TEST_TMP": tmp}):
            assert get_temp_parent() == Path(tmp)


def test_invalid_override_falls_back_without_deleting_the_existing_file():
    with tempfile.TemporaryDirectory() as tmp:
        marker = Path(tmp) / "not-a-directory"
        marker.write_text("keep", encoding="utf-8")
        with mock.patch.dict(os.environ, {"VPNSCI_TEST_TMP": str(marker)}):
            with mock.patch("tests.temp_helpers.tempfile.gettempdir", return_value=tmp):
                assert get_temp_parent() == Path(tmp)
        assert marker.read_text(encoding="utf-8") == "keep"
