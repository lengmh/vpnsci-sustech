import tempfile
import unittest
from pathlib import Path

from vpnsci_sustech.models import Paper


class FileNamingTests(unittest.TestCase):
    def test_title_author_policy_preserves_chinese_metadata(self):
        from vpnsci_sustech.file_naming import build_artifact_stem

        paper = Paper(
            title="钙钛矿太阳能电池稳定性研究",
            authors=["张三", "李四"],
            year=2024,
            doi="10.1234/example",
        )

        self.assertEqual(
            build_artifact_stem(paper, policy="title_author"),
            "钙钛矿太阳能电池稳定性研究 - 张三",
        )

    def test_identifier_policy_matches_existing_doi_slug(self):
        from vpnsci_sustech.file_naming import build_artifact_stem

        paper = Paper(doi="10.1038/nphys1509")

        self.assertEqual(
            build_artifact_stem(paper, policy="identifier"),
            "10.1038_nphys1509",
        )

    def test_identifier_stem_supports_arxiv_url(self):
        from vpnsci_sustech.file_naming import identifier_stem

        self.assertEqual(
            identifier_stem(url="https://arxiv.org/abs/2301.08745"),
            "arxiv_2301.08745",
        )

    def test_sanitize_removes_windows_invalid_characters_and_reserved_names(self):
        from vpnsci_sustech.file_naming import sanitize_filename_component

        self.assertEqual(
            sanitize_filename_component('CON: a/b*c? "paper". '),
            "CON_ a_b_c_ _paper_",
        )
        self.assertEqual(sanitize_filename_component("NUL"), "_NUL")

    def test_long_stem_is_truncated_with_hash(self):
        from vpnsci_sustech.file_naming import build_artifact_stem

        paper = Paper(title="A" * 240, authors=["Smith"])
        stem = build_artifact_stem(paper, policy="title_author", max_length=80)

        self.assertLessEqual(len(stem), 80)
        self.assertRegex(stem, r"_[0-9a-f]{8}$")

    def test_title_policy_with_missing_metadata_falls_back_to_identifier(self):
        from vpnsci_sustech.file_naming import build_artifact_stem

        paper = Paper(doi="10.1234/example")

        self.assertEqual(
            build_artifact_stem(paper, policy="title_author"),
            "10.1234_example",
        )

    def test_custom_policy_with_empty_template_result_falls_back_to_identifier(self):
        from vpnsci_sustech.file_naming import build_artifact_stem

        paper = Paper(doi="10.1234/example")

        self.assertEqual(
            build_artifact_stem(paper, policy="custom", template="{title} - {first_author}"),
            "10.1234_example",
        )

    def test_custom_policy_with_underscore_only_result_falls_back_to_identifier(self):
        from vpnsci_sustech.file_naming import build_artifact_stem

        paper = Paper(doi="10.1234/example")

        self.assertEqual(
            build_artifact_stem(paper, policy="custom", template="{title}_{first_author}"),
            "10.1234_example",
        )

    def test_reserve_unique_path_does_not_overwrite_existing_file(self):
        from vpnsci_sustech.file_naming import reserve_unique_path

        temp_root = Path("F:/AI playground/TempFiles")
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as tmp:
            base = Path(tmp)
            existing = base / "paper.pdf"
            existing.write_bytes(b"old")

            reserved = reserve_unique_path(
                base,
                stem="paper",
                ext="pdf",
                collision_key="10.1234/example",
                collision="hash",
            )

            self.assertNotEqual(reserved, existing)
            self.assertEqual(existing.read_bytes(), b"old")
            self.assertTrue(reserved.name.startswith("paper_"))
            self.assertEqual(reserved.suffix, ".pdf")


if __name__ == "__main__":
    unittest.main()
