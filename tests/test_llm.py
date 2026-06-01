import unittest

from cic.llm import LLMClient, extract_json_object, heuristic_insights
from cic.rules import normalize_holding


class LLMTest(unittest.TestCase):
    def test_no_key_returns_fallback(self):
        fallback = {"items": []}
        client = LLMClient(api_key="")
        result = client.chat_json("system", "user", fallback)
        self.assertEqual(result.status, "skipped_no_api_key")
        self.assertEqual(result.data, fallback)

    def test_extract_json_from_wrapped_text(self):
        parsed = extract_json_object('前缀 {"items":[{"stock_code":"000001.SZ"}]} 后缀', {"items": []})
        self.assertEqual(parsed["items"][0]["stock_code"], "000001.SZ")

    def test_heuristic_insights_shape(self):
        holding = normalize_holding({"stock_code": "000001.SZ", "stock_name": "平安银行"})
        insights = heuristic_insights([holding])
        self.assertEqual(insights["items"][0]["stock_code"], "000001.SZ")
        self.assertIn("research_question", insights["items"][0])


if __name__ == "__main__":
    unittest.main()
