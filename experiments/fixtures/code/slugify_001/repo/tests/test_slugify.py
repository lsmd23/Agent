import unittest
from lib.strutil import slugify

class TestSlug(unittest.TestCase):
    def test_spaces(self) -> None:
        self.assertEqual(slugify('Hello World'), 'hello-world')

if __name__ == '__main__':
    unittest.main()
