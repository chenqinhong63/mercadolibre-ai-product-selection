#!/usr/bin/env python3
"""Tests for damaishuju_client.py using fake helper scripts. No network, no key."""
import json
import os
import sys
import tempfile
from pathlib import Path
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from damaishuju_client import (  # noqa: E402
    AuthError,
    ClientUnavailableError,
    DamaishujuClient,
    QuotaError,
    _count_results,
    _parse_quota,
)

FAKE_OK = '''#!/usr/bin/env python3
import json, sys
from pathlib import Path
log = Path(sys.argv[0]).with_name("calls.log")
args_file = sys.argv[sys.argv.index("--arguments-file") + 1]
name = sys.argv[sys.argv.index("--name") + 1]
args = json.loads(Path(args_file).read_text())
with open(log, "a") as h:
    h.write(json.dumps({"tool": name, "args": args}) + "\\n")
if name == "get_my_quota_status":
    text = json.dumps({"available_points": 50, "plan_code": None, "plan_name": None})
else:
    text = json.dumps([{"sku_id": "MLM000000001"}, {"sku_id": "MLM000000002"}])
print(json.dumps({"content": [{"type": "text", "text": text}]}))
'''

FAKE_401 = '''#!/usr/bin/env python3
import sys
print("error: MCP returned HTTP 401; the operation was not replayed", file=sys.stderr)
sys.exit(1)
'''

FAKE_FLAKY = '''#!/usr/bin/env python3
import json, sys
from pathlib import Path
state = Path(sys.argv[0]).with_name("state.txt")
n = int(state.read_text()) if state.exists() else 0
state.write_text(str(n + 1))
if n == 0:
    print("error: MCP request did not complete", file=sys.stderr)
    sys.exit(1)
print(json.dumps({"content": [{"type": "text", "text": "[]"}]}))
'''


def write_fake(tmp, name, content):
    path = os.path.join(tmp, name)
    with open(path, "w") as handle:
        handle.write(content)
    os.chmod(path, 0o755)
    return path


class TestParsing(unittest.TestCase):
    def test_parse_quota(self):
        result = {"content": [{"type": "text", "text":
            '{"available_points": 50, "plan_code": null, "plan_name": null}'}]}
        parsed = _parse_quota(result)
        self.assertEqual(parsed["available_points"], 50)
        self.assertIsNone(parsed["plan_code"])

    def test_count_results_list(self):
        result = {"content": [{"type": "text", "text": '[{"a": 1}, {"a": 2}]'}]}
        self.assertEqual(_count_results(result), 2)

    def test_count_results_dict_key(self):
        result = {"content": [{"type": "text", "text": '{"products": [1, 2, 3]}'}]}
        self.assertEqual(_count_results(result), 3)


class TestWrapper(unittest.TestCase):
    def test_missing_client_fails_clearly(self):
        client = DamaishujuClient(client_path="/nonexistent/client.py",
                                 cache_dir=tempfile.mkdtemp())
        with self.assertRaises(ClientUnavailableError):
            client.quota()

    def test_quota_check_before_paid_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = write_fake(tmp, "fake_client.py", FAKE_OK)
            client = DamaishujuClient(client_path=fake, cache_dir=os.path.join(tmp, ".cache"))
            client.search_products("cuerda para saltar")
            calls = [json.loads(line) for line in
                     Path(os.path.join(tmp, "calls.log")).read_text().splitlines()]
            self.assertEqual(calls[0]["tool"], "get_my_quota_status")
            self.assertEqual(calls[1]["tool"], "search_product_snapshots")
            self.assertEqual(calls[1]["args"]["market_code"], "MLM")

    def test_search_categories_cached_14_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = write_fake(tmp, "fake_client.py", FAKE_OK)
            client = DamaishujuClient(client_path=fake, cache_dir=os.path.join(tmp, ".cache"))
            client.search_categories("cuerda")
            client.search_categories("cuerda")
            calls = Path(os.path.join(tmp, "calls.log")).read_text().strip().split("\n")
            self.assertEqual(len(calls), 1)  # second call served from cache

    def test_transient_error_retried_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = write_fake(tmp, "fake_client.py", FAKE_FLAKY)
            client = DamaishujuClient(client_path=fake, cache_dir=os.path.join(tmp, ".cache"))
            result = client.call("search_categories", {"query": "cuerda"})
            self.assertIn("content", result)
            self.assertEqual(Path(os.path.join(tmp, "state.txt")).read_text(), "2")

    def test_401_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = write_fake(tmp, "fake_client.py", FAKE_401)
            client = DamaishujuClient(client_path=fake, cache_dir=os.path.join(tmp, ".cache"))
            with self.assertRaises(AuthError):
                client.call("search_categories", {"query": "cuerda"})

    def test_zero_quota_refuses_paid_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            zero_quota = FAKE_OK.replace('"available_points": 50', '"available_points": 0')
            fake = write_fake(tmp, "fake_client.py", zero_quota)
            client = DamaishujuClient(client_path=fake, cache_dir=os.path.join(tmp, ".cache"))
            with self.assertRaises(QuotaError):
                client.search_products("cuerda para saltar")


if __name__ == "__main__":
    unittest.main()
