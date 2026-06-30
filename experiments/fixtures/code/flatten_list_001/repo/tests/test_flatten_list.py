import unittest
from lib.listutil import flatten

class TestFlat(unittest.TestCase):
    def test_deep(self) -> None:
        self.assertEqual(flatten([1, [2, [3]]]), [1, 2, 3])

if __name__ == '__main__':
    unittest.main()
