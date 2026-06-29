import unittest

from experiments.real_benchmarks.prepare_gsm8k_sample import extract_gold_answer
from experiments.real_benchmarks.run_gsm8k_llm import exact_match, extract_model_answer, normalize_number


class RealBenchmarkUtilityTests(unittest.TestCase):
    def test_extract_gold_answer(self):
        self.assertEqual(extract_gold_answer("Work here. #### 1,234"), "1234")

    def test_extract_model_answer(self):
        self.assertEqual(extract_model_answer("Reasoning...\n#### 42"), "42")
        self.assertEqual(extract_model_answer("Final answer: 3.0"), "3")

    def test_exact_match(self):
        self.assertTrue(exact_match("1,200", "1200"))
        self.assertTrue(exact_match("3.0", "3"))
        self.assertFalse(exact_match("4", "3"))
        self.assertIsNone(normalize_number("no numeric answer"))


if __name__ == "__main__":
    unittest.main()
