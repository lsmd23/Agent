import unittest
from lib.dictutil import deep_merge

class TestMerge(unittest.TestCase):
    def test_nested(self) -> None:
        a = {'x': {'y': 1}}
        b = {'x': {'z': 2}}
        self.assertEqual(deep_merge(a, b), {'x': {'y': 1, 'z': 2}})

if __name__ == '__main__':
    unittest.main()
