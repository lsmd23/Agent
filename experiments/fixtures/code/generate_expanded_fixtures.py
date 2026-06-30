#!/usr/bin/env python3
"""Generate expanded local executable code fixtures for T5."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CODE_ROOT = ROOT

SPECS: list[dict] = [
    {
        "fixture_id": "sanitize_html_001",
        "task_id": "phase1_code_sanitize_001",
        "description": "escape_html must HTML-escape user input.",
        "path": "lib/htmlutil.py",
        "broken": "def escape_html(text: str) -> str:\n    return text\n",
        "golden": "import html\n\n\ndef escape_html(text: str) -> str:\n    return html.escape(text)\n",
        "markers": ["html.escape"],
        "test": "import unittest\nfrom lib.htmlutil import escape_html\n\nclass TestHtml(unittest.TestCase):\n    def test_escapes_angle_brackets(self) -> None:\n        self.assertEqual(escape_html('<b>'), '&lt;b&gt;')\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["security", "sanitization"],
    },
    {
        "fixture_id": "strip_tags_001",
        "task_id": "phase1_code_strip_tags_001",
        "description": "strip_tags should remove HTML tags, not just spaces.",
        "path": "lib/htmlutil.py",
        "broken": "def strip_tags(text: str) -> str:\n    return text.strip()\n",
        "golden": "import re\n\n_TAG_RE = re.compile(r'<[^>]+>')\n\n\ndef strip_tags(text: str) -> str:\n    return _TAG_RE.sub('', text)\n",
        "markers": ["_TAG_RE.sub"],
        "test": "import unittest\nfrom lib.htmlutil import strip_tags\n\nclass TestStrip(unittest.TestCase):\n    def test_removes_tags(self) -> None:\n        self.assertEqual(strip_tags('<p>hi</p>'), 'hi')\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["security", "sanitization"],
    },
    {
        "fixture_id": "parse_int_001",
        "task_id": "phase1_code_parse_int_001",
        "description": "safe_int treats empty strings as zero.",
        "path": "lib/parseutil.py",
        "broken": "def safe_int(value: str) -> int:\n    return int(value)\n",
        "golden": "def safe_int(value: str) -> int:\n    if not value.strip():\n        return 0\n    return int(value)\n",
        "markers": ["if not value.strip()"],
        "test": "import unittest\nfrom lib.parseutil import safe_int\n\nclass TestParse(unittest.TestCase):\n    def test_empty_is_zero(self) -> None:\n        self.assertEqual(safe_int(''), 0)\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["parsing"],
    },
    {
        "fixture_id": "parse_csv_row_001",
        "task_id": "phase1_code_csv_001",
        "description": "split_csv_row mishandles quoted commas.",
        "path": "lib/csvutil.py",
        "broken": "def split_csv_row(row: str) -> list[str]:\n    return row.split(',')\n",
        "golden": "import csv\nfrom io import StringIO\n\n\ndef split_csv_row(row: str) -> list[str]:\n    return next(csv.reader(StringIO(row)))\n",
        "markers": ["csv.reader"],
        "test": "import unittest\nfrom lib.csvutil import split_csv_row\n\nclass TestCsv(unittest.TestCase):\n    def test_quoted_comma(self) -> None:\n        self.assertEqual(split_csv_row('a,\"b,c\",d'), ['a', 'b,c', 'd'])\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["parsing"],
    },
    {
        "fixture_id": "json_get_001",
        "task_id": "phase1_code_json_001",
        "description": "get_path should traverse nested dict keys.",
        "path": "lib/jsonutil.py",
        "broken": "def get_path(data: dict, key: str):\n    return data.get(key)\n",
        "golden": "def get_path(data: dict, key: str):\n    current = data\n    for part in key.split('.'):\n        if not isinstance(current, dict):\n            return None\n        current = current.get(part)\n    return current\n",
        "markers": ["key.split('.')"],
        "test": "import unittest\nfrom lib.jsonutil import get_path\n\nclass TestJson(unittest.TestCase):\n    def test_nested(self) -> None:\n        self.assertEqual(get_path({'a': {'b': 1}}, 'a.b'), 1)\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["parsing"],
    },
    {
        "fixture_id": "url_join_001",
        "task_id": "phase1_code_url_001",
        "description": "join_url drops duplicate slashes incorrectly.",
        "path": "lib/urlutil.py",
        "broken": "def join_url(base: str, path: str) -> str:\n    return base + path\n",
        "golden": "def join_url(base: str, path: str) -> str:\n    return base.rstrip('/') + '/' + path.lstrip('/')\n",
        "markers": ["rstrip('/')"],
        "test": "import unittest\nfrom lib.urlutil import join_url\n\nclass TestUrl(unittest.TestCase):\n    def test_join(self) -> None:\n        self.assertEqual(join_url('http://x.com/', '/a'), 'http://x.com/a')\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["path"],
    },
    {
        "fixture_id": "pkg_helper_001",
        "task_id": "phase1_code_pkg_helper_001",
        "description": "Missing helpers module after refactor.",
        "path": "app/helpers.py",
        "broken": None,
        "golden": "def greet(name: str) -> str:\n    return f'hello {name}'\n",
        "markers": ["def greet"],
        "test": "import unittest\nfrom app.helpers import greet\n\nclass TestHelper(unittest.TestCase):\n    def test_greet(self) -> None:\n        self.assertEqual(greet('world'), 'hello world')\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["import", "refactor"],
        "extra_repo": {"app/__init__.py": ""},
    },
    {
        "fixture_id": "refactor_rename_001",
        "task_id": "phase1_code_refactor_001",
        "description": "Function renamed in module but test expects new name.",
        "path": "lib/legacy.py",
        "broken": "def old_name(value: int) -> int:\n    return value + 1\n",
        "golden": "def new_name(value: int) -> int:\n    return value + 1\n",
        "markers": ["def new_name"],
        "test": "import unittest\nfrom lib.legacy import new_name\n\nclass TestLegacy(unittest.TestCase):\n    def test_increment(self) -> None:\n        self.assertEqual(new_name(2), 3)\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["refactor"],
    },
    {
        "fixture_id": "clamp_001",
        "task_id": "phase1_code_clamp_001",
        "description": "clamp ignores upper bound.",
        "path": "lib/mathutil.py",
        "broken": "def clamp(value: float, low: float, high: float) -> float:\n    if value < low:\n        return low\n    return value\n",
        "golden": "def clamp(value: float, low: float, high: float) -> float:\n    if value < low:\n        return low\n    if value > high:\n        return high\n    return value\n",
        "markers": ["if value > high"],
        "test": "import unittest\nfrom lib.mathutil import clamp\n\nclass TestClamp(unittest.TestCase):\n    def test_upper(self) -> None:\n        self.assertEqual(clamp(10, 0, 5), 5)\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["edge_case", "math"],
    },
    {
        "fixture_id": "mean_001",
        "task_id": "phase1_code_mean_001",
        "description": "mean crashes on empty input instead of returning 0.",
        "path": "lib/stats.py",
        "broken": "def mean(values: list[float]) -> float:\n    return sum(values) / len(values)\n",
        "golden": "def mean(values: list[float]) -> float:\n    if not values:\n        return 0.0\n    return sum(values) / len(values)\n",
        "markers": ["if not values"],
        "test": "import unittest\nfrom lib.stats import mean\n\nclass TestMean(unittest.TestCase):\n    def test_empty(self) -> None:\n        self.assertEqual(mean([]), 0.0)\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["edge_case", "math"],
    },
    {
        "fixture_id": "palindrome_001",
        "task_id": "phase1_code_palindrome_001",
        "description": "is_palindrome is case-sensitive incorrectly.",
        "path": "lib/strutil.py",
        "broken": "def is_palindrome(text: str) -> bool:\n    return text == text[::-1]\n",
        "golden": "def is_palindrome(text: str) -> bool:\n    normalized = text.lower().replace(' ', '')\n    return normalized == normalized[::-1]\n",
        "markers": ["text.lower()"],
        "test": "import unittest\nfrom lib.strutil import is_palindrome\n\nclass TestPal(unittest.TestCase):\n    def test_case_insensitive(self) -> None:\n        self.assertTrue(is_palindrome('Racecar'))\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["string", "edge_case"],
    },
    {
        "fixture_id": "slugify_001",
        "task_id": "phase1_code_slugify_001",
        "description": "slugify leaves spaces instead of hyphens.",
        "path": "lib/strutil.py",
        "broken": "def slugify(text: str) -> str:\n    return text.lower()\n",
        "golden": "import re\n\n\ndef slugify(text: str) -> str:\n    text = text.lower().strip()\n    text = re.sub(r'[^a-z0-9]+', '-', text)\n    return text.strip('-')\n",
        "markers": ["re.sub"],
        "test": "import unittest\nfrom lib.strutil import slugify\n\nclass TestSlug(unittest.TestCase):\n    def test_spaces(self) -> None:\n        self.assertEqual(slugify('Hello World'), 'hello-world')\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["string"],
    },
    {
        "fixture_id": "merge_dict_001",
        "task_id": "phase1_code_merge_001",
        "description": "deep_merge overwrites nested dicts shallowly.",
        "path": "lib/dictutil.py",
        "broken": "def deep_merge(a: dict, b: dict) -> dict:\n    result = dict(a)\n    result.update(b)\n    return result\n",
        "golden": "def deep_merge(a: dict, b: dict) -> dict:\n    result = dict(a)\n    for key, value in b.items():\n        if key in result and isinstance(result[key], dict) and isinstance(value, dict):\n            result[key] = deep_merge(result[key], value)\n        else:\n            result[key] = value\n    return result\n",
        "markers": ["isinstance(result[key], dict)"],
        "test": "import unittest\nfrom lib.dictutil import deep_merge\n\nclass TestMerge(unittest.TestCase):\n    def test_nested(self) -> None:\n        a = {'x': {'y': 1}}\n        b = {'x': {'z': 2}}\n        self.assertEqual(deep_merge(a, b), {'x': {'y': 1, 'z': 2}})\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["refactor"],
    },
    {
        "fixture_id": "flatten_list_001",
        "task_id": "phase1_code_flatten_001",
        "description": "flatten only handles one nesting level.",
        "path": "lib/listutil.py",
        "broken": "def flatten(items: list) -> list:\n    result = []\n    for item in items:\n        if isinstance(item, list):\n            result.extend(item)\n        else:\n            result.append(item)\n    return result\n",
        "golden": "def flatten(items: list) -> list:\n    result = []\n    for item in items:\n        if isinstance(item, list):\n            result.extend(flatten(item))\n        else:\n            result.append(item)\n    return result\n",
        "markers": ["flatten(item)"],
        "test": "import unittest\nfrom lib.listutil import flatten\n\nclass TestFlat(unittest.TestCase):\n    def test_deep(self) -> None:\n        self.assertEqual(flatten([1, [2, [3]]]), [1, 2, 3])\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["edge_case"],
    },
    {
        "fixture_id": "email_valid_001",
        "task_id": "phase1_code_email_001",
        "description": "is_email accepts strings without domain.",
        "path": "lib/validate.py",
        "broken": "def is_email(value: str) -> bool:\n    return '@' in value\n",
        "golden": "import re\n\n_EMAIL_RE = re.compile(r'^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$')\n\n\ndef is_email(value: str) -> bool:\n    return bool(_EMAIL_RE.match(value))\n",
        "markers": ["_EMAIL_RE"],
        "test": "import unittest\nfrom lib.validate import is_email\n\nclass TestEmail(unittest.TestCase):\n    def test_rejects_no_domain(self) -> None:\n        self.assertFalse(is_email('user@'))\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["parsing"],
    },
    {
        "fixture_id": "trim_lines_001",
        "task_id": "phase1_code_trim_lines_001",
        "description": "trim_lines doc says strip each line; implementation strips whole blob.",
        "path": "lib/textutil.py",
        "broken": "def trim_lines(text: str) -> str:\n    \"\"\"Strip whitespace from each line.\"\"\"\n    return text.strip()\n",
        "golden": "def trim_lines(text: str) -> str:\n    \"\"\"Strip whitespace from each line.\"\"\"\n    return '\\n'.join(line.strip() for line in text.splitlines())\n",
        "markers": ["line.strip() for line"],
        "test": "import unittest\nfrom lib.textutil import trim_lines\n\nclass TestTrim(unittest.TestCase):\n    def test_per_line(self) -> None:\n        self.assertEqual(trim_lines(' a \\n b '), 'a\\nb')\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["docs"],
    },
    {
        "fixture_id": "config_get_001",
        "task_id": "phase1_code_config_get_001",
        "description": "Config loader ignores environment override.",
        "path": "lib/config.py",
        "broken": "import os\n\n\ndef get_setting(name: str, default: str = '') -> str:\n    return default\n",
        "golden": "import os\n\n\ndef get_setting(name: str, default: str = '') -> str:\n    return os.environ.get(name, default)\n",
        "markers": ["os.environ.get"],
        "test": "import os\nimport unittest\nfrom lib.config import get_setting\n\nclass TestConfig(unittest.TestCase):\n    def test_env_override(self) -> None:\n        os.environ['TEST_SETTING_X'] = 'from_env'\n        self.assertEqual(get_setting('TEST_SETTING_X', 'default'), 'from_env')\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["config"],
    },
    {
        "fixture_id": "hash_password_001",
        "task_id": "phase1_code_hash_001",
        "description": "hash_password stores plain text instead of digest.",
        "path": "lib/security.py",
        "broken": "def hash_password(password: str) -> str:\n    return password\n",
        "golden": "import hashlib\n\n\ndef hash_password(password: str) -> str:\n    return hashlib.sha256(password.encode('utf-8')).hexdigest()\n",
        "markers": ["hashlib.sha256"],
        "test": "import unittest\nfrom lib.security import hash_password\n\nclass TestHash(unittest.TestCase):\n    def test_not_plain(self) -> None:\n        self.assertNotEqual(hash_password('secret'), 'secret')\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["security"],
    },
    {
        "fixture_id": "read_env_flag_001",
        "task_id": "phase1_code_env_flag_001",
        "description": "as_bool treats 'false' string as true.",
        "path": "lib/envutil.py",
        "broken": "def as_bool(value: str) -> bool:\n    return bool(value)\n",
        "golden": "def as_bool(value: str) -> bool:\n    return value.strip().lower() in {'1', 'true', 'yes', 'on'}\n",
        "markers": ["value.strip().lower()"],
        "test": "import unittest\nfrom lib.envutil import as_bool\n\nclass TestEnv(unittest.TestCase):\n    def test_false_string(self) -> None:\n        self.assertFalse(as_bool('false'))\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["config", "parsing"],
    },
    {
        "fixture_id": "binary_search_001",
        "task_id": "phase1_code_binary_search_001",
        "description": "binary_search off-by-one on exact match at mid.",
        "path": "lib/algos.py",
        "broken": "def binary_search(items: list[int], target: int) -> int:\n    lo, hi = 0, len(items) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if items[mid] < target:\n            lo = mid + 1\n        elif items[mid] > target:\n            hi = mid - 1\n        else:\n            return mid + 1\n    return -1\n",
        "golden": "def binary_search(items: list[int], target: int) -> int:\n    lo, hi = 0, len(items) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if items[mid] < target:\n            lo = mid + 1\n        elif items[mid] > target:\n            hi = mid - 1\n        else:\n            return mid\n    return -1\n",
        "markers": ["return mid\n"],
        "test": "import unittest\nfrom lib.algos import binary_search\n\nclass TestSearch(unittest.TestCase):\n    def test_exact(self) -> None:\n        self.assertEqual(binary_search([1, 3, 5], 3), 1)\n\nif __name__ == '__main__':\n    unittest.main()\n",
        "tags": ["edge_case", "algorithm"],
    },
]


def write_fixture(spec: dict) -> None:
    fixture_id = spec["fixture_id"]
    base = CODE_ROOT / fixture_id
    rel_path = spec["path"]
    repo = base / "repo"
    golden = base / "golden"
    repo.mkdir(parents=True, exist_ok=True)
    golden.mkdir(parents=True, exist_ok=True)

    broken = spec.get("broken")
    if broken is not None:
        target = repo / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(broken, encoding="utf-8")

    golden_target = golden / rel_path
    golden_target.parent.mkdir(parents=True, exist_ok=True)
    golden_target.write_text(spec["golden"], encoding="utf-8")

    for extra_path, content in (spec.get("extra_repo") or {}).items():
        p = repo / extra_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    lib_parent = repo / Path(rel_path).parent
    if str(lib_parent).endswith("lib") or "/lib" in rel_path:
        init = lib_parent / "__init__.py"
        if not init.exists():
            init.write_text("", encoding="utf-8")

    test_name = f"test_{fixture_id.replace('_001', '')}.py"
    (repo / "tests").mkdir(exist_ok=True)
    (repo / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "tests" / test_name).write_text(spec["test"], encoding="utf-8")

    manifest = {
        "fixture_id": fixture_id,
        "task_ids": [spec["task_id"]],
        "description": spec["description"],
        "fix_files": [
            {
                "path": rel_path,
                "golden": f"golden/{rel_path}",
                "markers": spec["markers"],
            }
        ],
        "tags": spec.get("tags", []),
    }
    (base / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def task_entry(spec: dict) -> dict:
    tag = spec.get("tags", ["code"])[0]
    return {
        "task_id": spec["task_id"],
        "benchmark_id": "phase1_code_expanded",
        "task_family": "code_agent_task",
        "split": "phase1_expanded",
        "prompt": spec["description"] + " Fix the failing unit test with a minimal patch.",
        "budget": {
            "max_steps": 4,
            "max_module_calls": 8,
            "max_tool_calls": 3,
            "max_verifier_calls": 2,
            "max_tokens": 6000,
            "max_latency_ms": 120000,
            "max_activation_cost": 3.0,
        },
        "expected_route": {
            "oracle_available": True,
            "required_modules": ["code_agent"],
            "discouraged_modules": ["search_agent"],
            "oracle_best_module_id": "code_agent",
            "route_rationale": f"Executable code fix ({tag}).",
        },
        "memory_setup": {"injected_memory_ids": ["seed:code_route"], "quarantined_memory_ids": []},
        "negative_transfer_probe": {"enabled": False},
        "baseline_applicability": {
            "single_react_agent": True,
            "fixed_workflow_agent": True,
            "full_history_agent": True,
            "retrieval_memory_agent": True,
            "moa_style_agent": True,
            "agent_attention_agent": True,
        },
        "tags": ["code", tag, "phase1_expanded"],
        "success_oracle": {
            "oracle_type": "pytest_passes",
            "fixture_id": spec["fixture_id"],
            "success_label": "pass",
            "expected_tests": ["tests/test_*.py"],
            "criteria": [
                {
                    "criterion_id": "pytest_passes",
                    "description": "All unit tests in fixture repo pass after agent patch.",
                    "weight": 1.0,
                    "required": True,
                }
            ],
        },
        "environment": {"environment_type": "executable_fixture", "supports_executable_feedback": True},
    }


def main() -> None:
    for spec in SPECS:
        write_fixture(spec)
    tasks_path = ROOT.parents[1] / "tasks" / "phase1_code_expanded.jsonl"
    lines = [json.dumps(task_entry(spec), ensure_ascii=False) for spec in SPECS]
    tasks_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(SPECS)} fixtures and {tasks_path}")


if __name__ == "__main__":
    main()
