import unittest
from lib.parseutil import safe_int

class TestParse(unittest.TestCase):
    def test_empty_is_zero(self) -> None:
        self.assertEqual(safe_int(''), 0)

if __name__ == '__main__':
    unittest.main()
