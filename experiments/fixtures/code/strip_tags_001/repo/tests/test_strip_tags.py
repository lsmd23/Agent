import unittest
from lib.htmlutil import strip_tags

class TestStrip(unittest.TestCase):
    def test_removes_tags(self) -> None:
        self.assertEqual(strip_tags('<p>hi</p>'), 'hi')

if __name__ == '__main__':
    unittest.main()
