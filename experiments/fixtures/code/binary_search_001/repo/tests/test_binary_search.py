import unittest
from lib.algos import binary_search

class TestSearch(unittest.TestCase):
    def test_exact(self) -> None:
        self.assertEqual(binary_search([1, 3, 5], 3), 1)

if __name__ == '__main__':
    unittest.main()
