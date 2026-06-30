import unittest
from lib.strutil import is_palindrome

class TestPal(unittest.TestCase):
    def test_case_insensitive(self) -> None:
        self.assertTrue(is_palindrome('Racecar'))

if __name__ == '__main__':
    unittest.main()
