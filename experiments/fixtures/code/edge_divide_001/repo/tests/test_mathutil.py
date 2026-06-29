import unittest

from lib.mathutil import safe_divide


class TestMathUtil(unittest.TestCase):
    def test_zero_denominator_returns_zero(self) -> None:
        self.assertEqual(safe_divide(5, 0), 0.0)


if __name__ == "__main__":
    unittest.main()
