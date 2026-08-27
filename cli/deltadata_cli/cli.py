"""`deltadata compare` -- CI-friendly CLI over the DeltaData /api/v1/compare API.

Exit codes (documented in the README -- keep both in sync):
  0  OK             -- no behavioral change, or risk stayed below --fail-on
  1  RISK_THRESHOLD -- detected risk met or exceeded --fail-on
  2  EXECUTION_ERROR-- the provided SQL failed to execute against the data
  3  USAGE_ERROR    -- bad CLI arguments, missing files, or could not reach
                        the API at all (auth/connection/timeout)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional, Sequence

from . import formatting
from .client import DeltaDataAPIError, call_compare

EXIT_OK = 0
EXIT_RISK_THRESHOLD = 1
EXIT_EXECUTION_ERROR = 2
EXIT_USAGE_ERROR = 3

_RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
_FAIL_ON_CHOICES = ["none", "low", "medium", "high", "critical"]


class UsageError(Exception):
    pass


def _positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid float value: {value!r}") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"--timeout must be a positive number, got {value!r}")
    return parsed


class _ArgumentParser(argparse.ArgumentParser):
    """argparse's default `error()` exits with status 2, which would collide
    with our own EXECUTION_ERROR=2. Route CLI-usage errors through the same
    USAGE_ERROR=3 exit code as every other invalid-input case instead."""

    def error(self, message: str) -> None:  # pragma: no cover - exercised via tests
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        raise SystemExit(EXIT_USAGE_ERROR)


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog="deltadata",
        description="DeltaData -- behavioral regression testing for SQL changes.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    compare = sub.add_parser(
        "compare",
        help="Compare BEFORE/AFTER SQL against sample data and report behavioral differences.",
    )
    compare.add_argument("--before", required=True, metavar="FILE", help="Path to the BEFORE SQL file.")
    compare.add_argument("--after", required=True, metavar="FILE", help="Path to the AFTER SQL file.")
    compare.add_argument(
        "--data",
        action="append",
        required=True,
        dest="data",
        metavar="CSV_FILE",
        help="Path to a source CSV file. Repeat --data once per table the queries need.",
    )
    compare.add_argument(
        "--api-url",
        default=os.environ.get("DELTADATA_API_URL", "http://localhost:8000"),
        help="Base URL of a running DeltaData API (default: $DELTADATA_API_URL or http://localhost:8000).",
    )
    compare.add_argument(
        "--api-key",
        default=os.environ.get("DELTADATA_API_KEY", ""),
        help="API key sent as X-API-Key (default: $DELTADATA_API_KEY).",
    )
    compare.add_argument(
        "--fail-on",
        default="high",
        choices=_FAIL_ON_CHOICES,
        type=str.lower,
        help="Exit non-zero when detected risk meets or exceeds this level, or 'none' to never "
        "fail on risk (default: high).",
    )
    compare.add_argument("--json", action="store_true", help="Print the raw API JSON instead of a formatted summary.")
    compare.add_argument(
        "--timeout",
        type=_positive_float,
        default=60.0,
        help="HTTP request timeout in seconds, must be positive (default: 60).",
    )
    return parser


def _read_sql_file(path: str, flag: str) -> str:
    if not os.path.isfile(path):
        raise UsageError(f"{flag}: file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError as exc:
        raise UsageError(f"{flag}: could not read {path}: {exc}") from exc


def _validate_data_files(paths: list[str]) -> None:
    for path in paths:
        if not os.path.isfile(path):
            raise UsageError(f"--data: file not found: {path}")


def _risk_meets_threshold(risk_level: Optional[str], fail_on: str) -> bool:
    if fail_on == "none":
        return False
    level = _RISK_ORDER.get((risk_level or "LOW").upper())
    threshold = _RISK_ORDER.get(fail_on.upper())
    if level is None or threshold is None:
        return False
    return level >= threshold


def _run_compare(args: argparse.Namespace) -> int:
    try:
        old_sql = _read_sql_file(args.before, "--before")
        new_sql = _read_sql_file(args.after, "--after")
        _validate_data_files(args.data)
    except UsageError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_USAGE_ERROR

    try:
        result = call_compare(
            api_url=args.api_url,
            api_key=args.api_key,
            old_sql=old_sql,
            new_sql=new_sql,
            data_paths=args.data,
            timeout=args.timeout,
        )
    except DeltaDataAPIError as exc:
        print(f"Error: {exc.message}", file=sys.stderr)
        return EXIT_USAGE_ERROR

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(formatting.render_human(result))

    if result.get("status") == "error":
        return EXIT_EXECUTION_ERROR

    if _risk_meets_threshold(result.get("risk_level"), args.fail_on):
        return EXIT_RISK_THRESHOLD

    return EXIT_OK


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # Re-raise argparse's own controlled exits (already mapped to
        # EXIT_USAGE_ERROR by _ArgumentParser.error, or 0 for --help).
        return exc.code if isinstance(exc.code, int) else EXIT_USAGE_ERROR

    if args.command == "compare":
        return _run_compare(args)

    parser.print_help()
    return EXIT_USAGE_ERROR


def run() -> None:
    """Console-script entry point (see [project.scripts] in pyproject.toml)."""
    sys.exit(main())


if __name__ == "__main__":
    run()
