import unittest
from lib.jsonutil import get_path

class TestJson(unittest.TestCase):
    def test_nested(self) -> None:
        self.assertEqual(get_path({'a': {'b': 1}}, 'a.b'), 1)

if __name__ == '__main__':
    unittest.main()
