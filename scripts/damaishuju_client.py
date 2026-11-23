#!/usr/bin/env python3
"""Damaishuju MCP client wrapper (Mercado Libre Mexico MLM and Brazil MLB).

Thin wrapper around the already-installed connector helper at
``~/workspace/custom-connectors/custom.damaishuju/bin/client.py``.
It shells out to that helper; it does NOT copy any credential logic
and it never stores, logs or accepts an API key. If the helper is
missing, every call fails with a clear message -- results are never
fabricated.

Rules (from ``references/damaishuju-mcp.md``):
  - Damaishuju MCP is the ONLY data source. market_code is MLM
    (Mexico, default) or MLB (Brazil); keywords/categories are
    Spanish only for MLM and Portuguese only for MLB, never Chinese.
  - ``get_my_quota_status`` (free) is checked BEFORE any paid call.
    Paid tools: search_product_snapshots, industry_overview,
    product_sales_trend, review_search, image_search_products.
    Free tools: search_categories, get_my_quota_status.
  - Per-call point cost is UNKNOWN (verified 2026-11-23:
    available_points 50, no package). Never claim a cost.
  - Cache: search_categories and industry_overview results are
    cached for 14 days under ``.cache/`` (key = hash of params).
  - Retry at most once, only on transient errors. Never retry
    401/403 blindly.
  - Every call is logged (tool, params, time, returned count,
    remaining points) to stderr and/or a log file.

Usage:
  python3 damaishuju_client.py quota
  python3 damaishuju_client.py search-categories --args '{"query": "cuerda para saltar"}'
  python3 damaishuju_client.py search-products --args-file args.json
  python3 damaishuju_client.py industry-overview --args '{"category_id": "MLM123"}'
  python3 damaishuju_client.py product-sales-trend --args '{"sku_id": "MLM000000001"}'
  python3 damaishuju_client.py review-search --args '{"sku_id": "MLM000000001"}'
  python3 damaishuju_client.py image-search-products --args '{"image_url": "https://..."}'
"""
import argparse
import hashlib
import json
import logging
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_CLIENT = Path.home() / "workspace/custom-connectors/custom.damaishuju/bin/client.py"
DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"
CACHE_TTL = timedelta(days=14)
FREE_TOOLS = {"search_categories", "get_my_quota_status"}
PAID_TOOLS = {
    "search_product_snapshots",
    "industry_overview",
    "product_sales_trend",
    "review_search",
    "image_search_products",
}
CACHED_TOOLS = {"search_categories", "industry_overview"}
MARKET_CODES = {"MLM", "MLB"}
MARKET_CODE = "MLM"  # default; Mexico. Pass market_code="MLB" for Brazil.
MARKET_CURRENCIES = {"MLM": "MXN", "MLB": "BRL"}
MARKET_LANGUAGES = {"MLM": "Spanish", "MLB": "Portuguese"}


def validate_market(market_code):
    """Return the normalised market code, or raise for anything else."""
    code = (market_code or "").strip().upper()
    if code not in MARKET_CODES:
        raise DamaishujuError(f"unknown market_code {market_code!r}; use MLM or MLB")
    return code


def validate_keyword(keyword, market_code):
    """Reject keywords in the wrong language before any paid call.

    Chinese characters are never valid for either market. Spanish /
    Portuguese cannot be told apart reliably by script, so the skill
    layer must confirm the keyword language with the user; this
    function only enforces the hard rule (no CJK) and records the
    expected language for logging.
    """
    text = keyword or ""
    if re.search(r"[\u4e00-\u9fff]", text):
        raise DamaishujuError(
            f"keyword {keyword!r} contains Chinese characters; "
            f"{market_code} keywords must be in {MARKET_LANGUAGES[market_code]}"
        )
    return text

logger = logging.getLogger("damaishuju_client")


class DamaishujuError(RuntimeError):
    """Base error for this wrapper."""


class ClientUnavailableError(DamaishujuError):
    """The underlying MCP helper is missing."""


class AuthError(DamaishujuError):
    """401/403 from the MCP server; never retried blindly."""


class QuotaError(DamaishujuError):
    """Quota cannot be verified, or no points remain."""


def _count_results(result):
    """Best-effort count of returned items from an MCP tool result."""
    texts = []
    for block in result.get("content", []) or []:
        if isinstance(block, dict) and block.get("type") == "text":
            texts.append(block.get("text", ""))
    if not texts:
        return 0
    for text in texts:
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            continue
        if isinstance(parsed, list):
            return len(parsed)
        if isinstance(parsed, dict):
            for key in ("products", "snapshots", "items", "results", "reviews", "categories", "data"):
                value = parsed.get(key)
                if isinstance(value, list):
                    return len(value)
            return 1
    return len(texts)


def _parse_quota(result):
    """Extract available_points / plan from a quota result."""
    texts = [
        block.get("text", "")
        for block in result.get("content", []) or []
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    joined = "\n".join(texts)
    match = re.search(r"available_points['\"]?\s*[:=]\s*(\d+)", joined)
    points = int(match.group(1)) if match else None
    plan_code = None
    plan_name = None
    code_match = re.search(r"plan_code['\"]?\s*[:=]\s*(null|\"[^\"]*\"|'[^']*')", joined)
    if code_match and code_match.group(1) != "null":
        plan_code = code_match.group(1).strip("\"'")
    name_match = re.search(r"plan_name['\"]?\s*[:=]\s*(null|\"[^\"]*\"|'[^']*')", joined)
    if name_match and name_match.group(1) != "null":
        plan_name = name_match.group(1).strip("\"'")
    return {"available_points": points, "plan_code": plan_code, "plan_name": plan_name, "raw": result}


class DamaishujuClient:
    def __init__(self, client_path=None, cache_dir=None, log_file=None):
        self.client_path = Path(client_path) if client_path else DEFAULT_CLIENT
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        if log_file:
            handler = logging.FileHandler(log_file, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    # -- low-level call -------------------------------------------------
    def _run_once(self, tool, arguments):
        if not self.client_path.is_file():
            raise ClientUnavailableError(
                f"Damaishuju MCP helper not found at {self.client_path}; "
                "no data was fetched and no result was fabricated."
            )
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
            json.dump(arguments, handle, ensure_ascii=False)
            args_path = handle.name
        try:
            proc = subprocess.run(
                [sys.executable, str(self.client_path), "call-tool",
                 "--name", tool, "--arguments-file", args_path],
                capture_output=True, text=True, timeout=50,
            )
        except subprocess.TimeoutExpired as error:
            raise DamaishujuError(f"MCP call to {tool} timed out after 50s; first attempt may have completed") from error
        finally:
            Path(args_path).unlink(missing_ok=True)
        stderr = proc.stderr or ""
        if "HTTP 401" in stderr or "HTTP 403" in stderr:
            raise AuthError(
                f"MCP returned 401/403 for {tool}; check the registered credential "
                "and placement before retrying (not retried automatically)."
            )
        if proc.returncode != 0:
            raise DamaishujuError(f"MCP call to {tool} failed: {stderr.strip() or proc.stdout.strip()}")
        try:
            result = json.loads(proc.stdout)
        except ValueError as error:
            raise DamaishujuError(f"MCP call to {tool} returned unparsable output") from error
        if isinstance(result, dict) and result.get("isError"):
            raise DamaishujuError(f"MCP tool {tool} returned isError: {json.dumps(result, ensure_ascii=False)[:500]}")
        return result

    def _cache_path(self, tool, arguments):
        key = hashlib.sha256(
            json.dumps({"tool": tool, "arguments": arguments}, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        return self.cache_dir / f"{key}.json"

    def _cache_read(self, tool, arguments):
        path = self._cache_path(tool, arguments)
        if not path.is_file():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            cached_at = datetime.fromisoformat(entry["cached_at"])
        except (ValueError, KeyError, OSError):
            return None
        if datetime.now(timezone.utc) - cached_at > CACHE_TTL:
            return None
        logger.info("cache hit tool=%s params=%s", tool, json.dumps(arguments, ensure_ascii=False))
        return entry["result"]

    def _cache_write(self, tool, arguments, result):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "arguments": arguments,
            "result": result,
        }
        self._cache_path(tool, arguments).write_text(
            json.dumps(entry, ensure_ascii=False), encoding="utf-8")

    def call(self, tool, arguments, use_cache=True):
        """Call one MCP tool, with quota check, cache and one retry."""
        arguments = dict(arguments or {})
        arguments["market_code"] = validate_market(arguments.get("market_code") or MARKET_CODE)
        if tool in ("search_categories", "search_product_snapshots"):
            keyword = arguments.get("query") or arguments.get("keyword")
            if keyword:
                validate_keyword(keyword, arguments["market_code"])
        if tool in CACHED_TOOLS and use_cache:
            cached = self._cache_read(tool, arguments)
            if cached is not None:
                return cached
        remaining = None
        if tool in PAID_TOOLS:
            quota = self.quota()
            remaining = quota.get("available_points")
            if remaining is None:
                raise QuotaError("could not read available_points; paid call refused")
            if remaining <= 0:
                raise QuotaError("no Damaishuju points remain; paid call refused")
        attempts = 0
        while True:
            attempts += 1
            try:
                result = self._run_once(tool, arguments)
                break
            except AuthError:
                raise
            except DamaishujuError:
                if attempts >= 2:
                    raise
                logger.warning("transient failure on %s, retrying once", tool)
        count = _count_results(result)
        logger.info(
            "tool=%s params=%s time=%s returned_count=%s remaining_points=%s",
            tool, json.dumps(arguments, ensure_ascii=False),
            datetime.now(timezone.utc).isoformat(), count, remaining,
        )
        if tool in CACHED_TOOLS and use_cache:
            self._cache_write(tool, arguments, result)
        return result

    # -- public API -----------------------------------------------------
    def quota(self):
        """Free quota check; returns available_points/plan (points may be None if unparsable)."""
        result = self._run_once("get_my_quota_status", {})
        parsed = _parse_quota(result)
        logger.info(
            "tool=get_my_quota_status time=%s available_points=%s",
            datetime.now(timezone.utc).isoformat(), parsed["available_points"],
        )
        return parsed

    def search_categories(self, query, market_code=MARKET_CODE, **extra):
        args = {"market_code": market_code, "query": query}
        args.update(extra)
        return self.call("search_categories", args)

    def search_products(self, keyword, category_id=None, limit=None, market_code=MARKET_CODE, **extra):
        args = {"market_code": validate_market(market_code), "keyword": keyword}
        if category_id is not None:
            args["category_id"] = category_id
        if limit is not None:
            args["limit"] = limit
        args.update(extra)
        return self.call("search_product_snapshots", args)

    def industry_overview(self, category_id, market_code=MARKET_CODE, **extra):
        args = {"market_code": market_code, "category_id": category_id}
        args.update(extra)
        return self.call("industry_overview", args)

    def product_sales_trend(self, sku_id, days=None, market_code=MARKET_CODE, **extra):
        args = {"market_code": market_code, "sku_id": sku_id}
        if days is not None:
            args["days"] = days
        args.update(extra)
        return self.call("product_sales_trend", args)

    def review_search(self, sku_id, page=None, limit=None, market_code=MARKET_CODE, **extra):
        args = {"market_code": market_code, "sku_id": sku_id}
        if page is not None:
            args["page"] = page
        if limit is not None:
            args["limit"] = limit
        args.update(extra)
        return self.call("review_search", args)

    def image_search_products(self, image_url=None, image_base64=None, market_code=MARKET_CODE, **extra):
        args = {"market_code": market_code}
        if image_url is not None:
            args["image_url"] = image_url
        if image_base64 is not None:
            args["image_base64"] = image_base64
        args.update(extra)
        return self.call("image_search_products", args)


def _load_args(args_json, args_file):
    if args_file:
        return json.loads(Path(args_file).read_text(encoding="utf-8"))
    if args_json:
        return json.loads(args_json)
    return {}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Damaishuju MCP client wrapper (MLM/MLB).")
    parser.add_argument("--client", default=None, help="Path to the installed MCP helper client.py")
    parser.add_argument("--cache-dir", default=None, help="Cache directory (default: <repo>/.cache)")
    parser.add_argument("--log-file", default=None, help="Append call log to this file (in addition to stderr)")
    parser.add_argument("--no-cache", action="store_true", help="Bypass the 14-day cache")
    parser.add_argument("--market-code", default=None, help="Market code MLM (Mexico, default) or MLB (Brazil)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("quota")
    for name in ("search-categories", "search-products", "industry-overview",
                 "product-sales-trend", "review-search", "image-search-products"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--args", default=None, help="Arguments as a JSON object string")
        cmd.add_argument("--args-file", default=None, help="File holding arguments as a JSON object")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
    client = DamaishujuClient(client_path=args.client, cache_dir=args.cache_dir, log_file=args.log_file)
    tool_map = {
        "search-categories": "search_categories",
        "search-products": "search_product_snapshots",
        "industry-overview": "industry_overview",
        "product-sales-trend": "product_sales_trend",
        "review-search": "review_search",
        "image-search-products": "image_search_products",
    }
    try:
        if args.command == "quota":
            result = client.quota()
            print(json.dumps({k: v for k, v in result.items() if k != "raw"}, ensure_ascii=False, indent=2))
            return 0
        tool = tool_map[args.command]
        arguments = _load_args(args.args, args.args_file)
        if args.market_code:
            arguments["market_code"] = validate_market(args.market_code)
        if not isinstance(arguments, dict):
            parser.error("arguments must be a JSON object")
        result = client.call(tool, arguments, use_cache=not args.no_cache)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except DamaishujuError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
