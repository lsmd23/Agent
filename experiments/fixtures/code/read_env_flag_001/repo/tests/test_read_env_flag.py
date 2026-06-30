import unittest
from lib.envutil import as_bool

class TestEnv(unittest.TestCase):
    def test_false_string(self) -> None:
        self.assertFalse(as_bool('false'))

if __name__ == '__main__':
    unittest.main()
