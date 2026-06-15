import json
import tempfile
import unittest
from pathlib import Path

from vpnsci_sustech.config import Config
from vpnsci_sustech.download_workflows import (
    DownloadWorkflowItem,
    DownloadWorkflowSidecar,
    find_download_workflow_sidecars,
    load_download_workflow_sidecar,
    sidecar_directory,
    write_download_workflow_sidecar,
)


class DownloadWorkflowTests(unittest.TestCase):
    def test_sidecar_directory_uses_cache_download_workflows(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Config(cache_dir=tmp)

            directory = sidecar_directory(cfg)

            self.assertEqual(directory, Path(tmp) / "download-workflows")

    def test_write_download_workflow_sidecar_persists_to_cache_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Config(cache_dir=tmp)
            sidecar = DownloadWorkflowSidecar(
                workflow_id="download-123",
                root_session_id="search-root",
                source_session_id="search-source",
                derived_session_id="search-derived",
                original_query="原始检索",
                display_query="展示标题",
                recovered_label="恢复标题",
                actual_queries=[{"source": "CNKI", "queries": ["滤波耦合器"]}],
                items=[
                    DownloadWorkflowItem(
                        hit_key="cnki:ABC123",
                        title="知网论文",
                        authors=["张三"],
                        source="cnki",
                        source_url="https://kns.cnki.net/kcms2/article/abstract?filename=ABC123",
                        local_file="F:/AI playground/TempFiles/知网论文.caj",
                        download_format="caj",
                        result_type="downloaded_pdf",
                    )
                ],
            )

            path = write_download_workflow_sidecar(sidecar, cfg)

            self.assertEqual(path.parent, Path(tmp) / "download-workflows")
            self.assertTrue(path.exists())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["workflow_id"], "download-123")
            self.assertEqual(data["items"][0]["hit_key"], "cnki:ABC123")

    def test_can_load_and_find_sidecars(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Config(cache_dir=tmp)
            sidecar = DownloadWorkflowSidecar(
                workflow_id="download-abc",
                display_query="展示标题",
                items=[DownloadWorkflowItem(hit_key="cnki:ABC123", title="知网论文")],
            )

            path = write_download_workflow_sidecar(sidecar, cfg)
            loaded = load_download_workflow_sidecar(path)
            found = find_download_workflow_sidecars(cfg, display_query="展示标题")

            self.assertEqual(loaded.workflow_id, "download-abc")
            self.assertEqual(loaded.items[0].hit_key, "cnki:ABC123")
            self.assertEqual([item.workflow_id for item in found], ["download-abc"])


if __name__ == "__main__":
    unittest.main()
