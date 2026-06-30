import os
import unittest
from lib.config import get_setting

class TestConfig(unittest.TestCase):
    def test_env_override(self) -> None:
        os.environ['TEST_SETTING_X'] = 'from_env'
        self.assertEqual(get_setting('TEST_SETTING_X', 'default'), 'from_env')

if __name__ == '__main__':
    unittest.main()
