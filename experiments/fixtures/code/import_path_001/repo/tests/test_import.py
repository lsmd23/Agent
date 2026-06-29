import unittest

from mypkg.core import foo


class TestImport(unittest.TestCase):
    def test_foo(self) -> None:
        self.assertEqual(foo(), 1)


if __name__ == "__main__":
    unittest.main()
