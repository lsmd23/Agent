import unittest
from lib.security import hash_password

class TestHash(unittest.TestCase):
    def test_not_plain(self) -> None:
        self.assertNotEqual(hash_password('secret'), 'secret')

if __name__ == '__main__':
    unittest.main()
