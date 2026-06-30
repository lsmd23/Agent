import unittest
from lib.htmlutil import escape_html

class TestHtml(unittest.TestCase):
    def test_escapes_angle_brackets(self) -> None:
        self.assertEqual(escape_html('<b>'), '&lt;b&gt;')

if __name__ == '__main__':
    unittest.main()
