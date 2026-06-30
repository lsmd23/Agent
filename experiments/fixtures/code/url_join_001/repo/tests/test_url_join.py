import unittest
from lib.urlutil import join_url

class TestUrl(unittest.TestCase):
    def test_join(self) -> None:
        self.assertEqual(join_url('http://x.com/', '/a'), 'http://x.com/a')

if __name__ == '__main__':
    unittest.main()
