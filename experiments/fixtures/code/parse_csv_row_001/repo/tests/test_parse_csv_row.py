import unittest
from lib.csvutil import split_csv_row

class TestCsv(unittest.TestCase):
    def test_quoted_comma(self) -> None:
        self.assertEqual(split_csv_row('a,"b,c",d'), ['a', 'b,c', 'd'])

if __name__ == '__main__':
    unittest.main()
