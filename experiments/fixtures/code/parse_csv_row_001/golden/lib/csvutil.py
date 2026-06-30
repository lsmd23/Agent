import csv
from io import StringIO


def split_csv_row(row: str) -> list[str]:
    return next(csv.reader(StringIO(row)))
