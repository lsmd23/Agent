import unittest
from lib.legacy import new_name

class TestLegacy(unittest.TestCase):
    def test_increment(self) -> None:
        self.assertEqual(new_name(2), 3)

if __name__ == '__main__':
    unittest.main()
