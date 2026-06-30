import unittest
from lib.stats import mean

class TestMean(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(mean([]), 0.0)

if __name__ == '__main__':
    unittest.main()
