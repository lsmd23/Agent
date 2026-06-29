import unittest

from lib.textutil import normalize


class TestTextUtil(unittest.TestCase):
    def test_normalize_matches_docstring(self) -> None:
        self.assertEqual(normalize("AbC"), "abc")


if __name__ == "__main__":
    unittest.main()
