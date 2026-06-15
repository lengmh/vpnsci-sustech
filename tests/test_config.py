import tempfile
import unittest
from pathlib import Path
from unittest import mock

from vpnsci_sustech import config as config_module
from vpnsci_sustech.config import Config


class ConfigTests(unittest.TestCase):
    def test_semantic_scholar_api_key_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with mock.patch.object(config_module, "DEFAULT_BASE_DIR", tmp_path):
                cfg = Config(semantic_scholar_api_key="S2-KEY-123")
                cfg.save()

                loaded = Config.load()

                self.assertEqual(loaded.semantic_scholar_api_key, "S2-KEY-123")

    def test_phase3_config_fields_exist(self):
        cfg = Config()
        self.assertEqual(cfg.openalex_api_key, "")
        self.assertEqual(cfg.paper_search_pro_root, "")
        self.assertEqual(cfg.paper_search_pro_command, "")
        self.assertEqual(cfg.paper_search_pro_output_dir, "")

    def test_paper_filename_config_fields_exist(self):
        cfg = Config()
        self.assertEqual(cfg.paper_filename_policy, "title_author")
        self.assertEqual(cfg.paper_filename_template, "{title} - {first_author}")
        self.assertTrue(cfg.paper_filename_ask)
        self.assertEqual(cfg.paper_filename_max_length, 180)
        self.assertEqual(cfg.paper_filename_collision, "hash")

    def test_cnki_converter_config_fields_exist(self):
        cfg = Config()
        self.assertFalse(cfg.cnki_convert_caj_to_pdf)
        self.assertEqual(cfg.cnki_caj_converter_command, "")
