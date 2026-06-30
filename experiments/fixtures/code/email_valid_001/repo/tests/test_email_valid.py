import unittest
from lib.validate import is_email

class TestEmail(unittest.TestCase):
    def test_rejects_no_domain(self) -> None:
        self.assertFalse(is_email('user@'))

if __name__ == '__main__':
    unittest.main()
