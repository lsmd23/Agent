import unittest
from lib.textutil import trim_lines

class TestTrim(unittest.TestCase):
    def test_per_line(self) -> None:
        self.assertEqual(trim_lines(' a \n b '), 'a\nb')

if __name__ == '__main__':
    unittest.main()
