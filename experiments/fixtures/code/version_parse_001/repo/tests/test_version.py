import unittest

from lib.version_util import is_compatible


class TestVersion(unittest.TestCase):
    def test_patch_level_matters(self) -> None:
        self.assertFalse(is_compatible("1.2.10", "1.2.3"))


if __name__ == "__main__":
    unittest.main()
