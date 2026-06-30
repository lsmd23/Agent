import unittest
from app.helpers import greet

class TestHelper(unittest.TestCase):
    def test_greet(self) -> None:
        self.assertEqual(greet('world'), 'hello world')

if __name__ == '__main__':
    unittest.main()
