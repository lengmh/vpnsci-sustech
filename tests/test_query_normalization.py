import unittest

from vpnsci_sustech.sources.query_normalization import (
    MAX_QUERY_VARIANTS,
    QueryVariant,
    build_query_variants,
)


class QueryNormalizationTests(unittest.TestCase):
    def test_original_query_is_always_first(self):
        variants = build_query_variants("钙钛矿太阳能电池 稳定性")
        self.assertEqual(variants[0], QueryVariant("钙钛矿太阳能电池 稳定性", "original"))

    def test_chinese_context_does_not_generate_hidden_english_variants(self):
        variants = build_query_variants("钙钛矿太阳能电池 稳定性")
        self.assertEqual(variants, [QueryVariant("钙钛矿太阳能电池 稳定性", "original")])

    def test_rag_llm_does_not_generate_hidden_abbreviation_variant(self):
        variants = build_query_variants("检索增强生成 大语言模型")
        self.assertEqual(variants, [QueryVariant("检索增强生成 大语言模型", "original")])

    def test_variant_count_is_limited(self):
        variants = build_query_variants("钙钛矿 太阳能电池 稳定性 图神经网络 大语言模型 检索增强生成")
        self.assertLessEqual(len(variants), MAX_QUERY_VARIANTS)

    def test_unknown_query_does_not_invent_translation(self):
        variants = build_query_variants("完全未知的中文短语")
        self.assertEqual([v.variant_type for v in variants], ["original"])

    def test_body_temperature_infrared_terms_do_not_generate_english_variants(self):
        variants = build_query_variants("非接触体温测量 红外线测量")
        self.assertEqual(variants, [QueryVariant("非接触体温测量 红外线测量", "original")])


if __name__ == "__main__":
    unittest.main()
