import tempfile
import unittest
from pathlib import Path

from vpnsci_sustech.sources.search_cache import SearchSession, load_session, save_session
from vpnsci_sustech.sources.search_models import SearchHit
from vpnsci_sustech.sources.session_derivation import derive_search_session


class SessionDerivationTests(unittest.TestCase):
    def test_derive_search_session_creates_first_level_derivation(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = SearchSession(
                session_id="search-root",
                query="microwave filter",
                filters={},
                hits=[
                    SearchHit(title="A", doi="10.1/a", hit_key="doi:10.1/a", source="openalex"),
                    SearchHit(title="B", doi="10.1/b", hit_key="doi:10.1/b", source="semantic_scholar"),
                ],
                source_summary={"openalex": 1, "semantic_scholar": 1},
            )

            derived = derive_search_session(
                base,
                selected_hit_keys=["doi:10.1/b"],
                derivation_type="manual_selection",
                derivation_note="selected RF paper only",
            )

            self.assertEqual(derived.derivation["source_session_id"], "search-root")
            self.assertEqual(derived.derivation["root_session_id"], "search-root")
            self.assertEqual(derived.derivation["derivation_type"], "manual_selection")
            self.assertEqual(derived.derivation["derivation_note"], "selected RF paper only")
            self.assertEqual(derived.derivation["selected_count_before"], 2)
            self.assertEqual(derived.derivation["selected_count_after"], 1)
            self.assertEqual(derived.hits[0].hit_key, "doi:10.1/b")
            self.assertEqual(derived.source_summary, {"semantic_scholar": 1})

    def test_derive_search_session_supports_multi_level_provenance(self):
        level1 = SearchSession(
            session_id="search-level1",
            query="microwave filter",
            filters={},
            hits=[SearchHit(title="A", doi="10.1/a", hit_key="doi:10.1/a")],
            derivation={
                "source_session_id": "search-root",
                "root_session_id": "search-root",
                "derivation_type": "manual_selection",
                "selected_count_before": 5,
                "selected_count_after": 1,
            },
        )

        derived = derive_search_session(
            level1,
            selected_hit_keys=["doi:10.1/a"],
            derivation_type="manual_selection",
        )

        self.assertEqual(derived.derivation["source_session_id"], "search-level1")
        self.assertEqual(derived.derivation["root_session_id"], "search-root")

    def test_derived_session_roundtrips_through_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = SearchSession(
                session_id="search-root",
                query="graph neural network",
                filters={},
                hits=[SearchHit(title="A", doi="10.1/a", hit_key="doi:10.1/a")],
            )
            derived = derive_search_session(
                base,
                selected_hit_keys=["doi:10.1/a"],
                derivation_type="manual_selection",
            )

            save_session(derived, Path(tmp))
            loaded = load_session(derived.session_id, Path(tmp))

            self.assertEqual(loaded.derivation["source_session_id"], "search-root")
            self.assertEqual(loaded.derivation["root_session_id"], "search-root")
            self.assertEqual(loaded.hits[0].hit_key, "doi:10.1/a")


if __name__ == "__main__":
    unittest.main()
