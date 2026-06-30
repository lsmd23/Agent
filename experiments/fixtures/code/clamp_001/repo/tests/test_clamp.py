import unittest
from lib.mathutil import clamp

class TestClamp(unittest.TestCase):
    def test_upper(self) -> None:
        self.assertEqual(clamp(10, 0, 5), 5)

if __name__ == '__main__':
    unittest.main()
