import unittest

from vpnsci_sustech.sources.backend_routing import resolve_requested_backend


class BackendRoutingTests(unittest.TestCase):
    def test_explicit_backend_wins(self):
        route = resolve_requested_backend("任意查询", explicit_backend="ieee")

        self.assertEqual(route.backend, "ieee")
        self.assertTrue(route.explicit)

    def test_cnki_intent_routes_to_cnki(self):
        route = resolve_requested_backend("在知网查钙钛矿太阳能电池")

        self.assertEqual(route.backend, "cnki")
        self.assertFalse(route.explicit)
        self.assertTrue(route.reasons)

    def test_dissertation_intent_routes_to_cnki(self):
        route = resolve_requested_backend("石墨烯 硕士论文")

        self.assertEqual(route.backend, "cnki")
        self.assertIn("cnki_database_intent", route.reasons[0])

    def test_plain_chinese_query_does_not_route_to_cnki(self):
        route = resolve_requested_backend("钙钛矿太阳能电池 稳定性")

        self.assertEqual(route.backend, "")

    def test_explicit_cnki_backend_marks_route_reason(self):
        route = resolve_requested_backend("graph neural network", explicit_backend="cnki")

        self.assertEqual(route.backend, "cnki")
        self.assertEqual(route.reasons, ["explicit_backend"])


if __name__ == "__main__":
    unittest.main()
