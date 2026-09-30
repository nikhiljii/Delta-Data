#!/usr/bin/env python3
"""Trusted-base helper for the DeltaData pull_request_target workflow."""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any


class CheckError(Exception):
    """A PR cannot be safely analyzed with the available inputs."""

    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


def _pull_request_files(repository: str, pull_number: int, changed_count: int) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    page = 1
    while True:
        url = (
            f"https://api.github.com/repos/{repository}/pulls/{pull_number}/files"
            f"?per_page=100&page={page}"
        )
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "deltadata-pr-check",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                batch = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise CheckError(f"Could not list pull request files from GitHub: {exc}") from exc
        if not isinstance(batch, list):
            raise CheckError("GitHub returned an unexpected pull request files response.")
        files.extend(batch)
        if len(files) == changed_count:
            break
        if len(batch) < 100:
            break
        page += 1
        if page > 3:
            raise CheckError("Pull requests with more than 300 changed files are unsupported.")
    if len(files) != changed_count:
        raise CheckError(
            f"GitHub listed {len(files)} changed files, but the event reports {changed_count}; "
            "refusing to analyze an incomplete file list."
        )
    return files


def _write_output(output_path: str, name: str, value: str) -> None:
    with open(output_path, "a", encoding="utf-8") as output:
        output.write(f"{name}={value}\n")


def inspect_pull_request(args: argparse.Namespace) -> None:
    files = _pull_request_files(args.repository, args.pull_number, args.changed_count)
    if any(
        not isinstance(item, dict)
        or not isinstance(item.get("filename"), str)
        or not isinstance(item.get("status"), str)
        for item in files
    ):
        raise CheckError("GitHub returned an invalid pull request file entry.")
    sql_files = [
        {"path": item.get("filename"), "status": item.get("status")}
        for item in files
        if (
            item["filename"].endswith(".sql")
            or (
                isinstance(item.get("previous_filename"), str)
                and item["previous_filename"].endswith(".sql")
            )
        )
    ]
    encoded = base64.b64encode(
        json.dumps(sql_files, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    _write_output(args.output, "has_sql", "true" if sql_files else "false")
    _write_output(args.output, "changed_sql_b64", encoded)
    if sql_files:
        print("Changed SQL paths:")
        for item in sql_files:
            print(f"  {item['status']}: {json.dumps(item['path'])}")
    else:
        print("No SQL files changed; the behavioral check passes.")


def _git_show(commit: str, path: str, cwd: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "show", f"{commit}:{path}"],
            cwd=cwd,
            check=True,
            capture_output=True,
        )
        return result.stdout.decode("utf-8")
    except (subprocess.CalledProcessError, UnicodeDecodeError) as exc:
        raise CheckError(f"Could not read {path!r} at commit {commit}: {exc}") from exc


def _git_merge_base(base_sha: str, head_sha: str, repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "merge-base", base_sha, head_sha],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise CheckError(f"Could not find the PR base/head merge-base: {exc}") from exc
    merge_base = result.stdout.strip()
    if not merge_base:
        raise CheckError("Git returned an empty PR base/head merge-base.")
    return merge_base


def _git_changed_sql(base_sha: str, head_sha: str, repo_root: Path) -> list[dict[str, str]]:
    try:
        result = subprocess.run(
            [
                "git",
                "diff",
                "--find-renames",
                "--name-status",
                "-z",
                base_sha,
                head_sha,
                "--",
                "*.sql",
            ],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        raise CheckError(f"Could not diff the pull request base and head: {exc}") from exc
    parts = result.stdout.decode("utf-8").split("\0")
    if parts and not parts[-1]:
        parts.pop()
    status_names = {"M": "modified", "A": "added", "D": "removed", "R": "renamed", "C": "copied"}
    changed = []
    index = 0
    while index < len(parts):
        status = parts[index]
        index += 1
        if status.startswith(("R", "C")):
            if index + 1 >= len(parts):
                raise CheckError("Git returned an incomplete renamed-SQL record.")
            index += 1  # old path; GitHub lists the new path
        if index >= len(parts):
            raise CheckError("Git returned an incomplete changed-SQL list.")
        changed.append({"status": status_names.get(status[0], status), "path": parts[index]})
        index += 1
    return changed


def _read_changed_sql(encoded: str) -> list[dict[str, str]]:
    try:
        changed = json.loads(base64.b64decode(encoded, validate=True).decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise CheckError("The changed-SQL list was invalid or incomplete.") from exc
    if not isinstance(changed, list) or not changed:
        raise CheckError("Expected at least one changed SQL file to analyze.")
    for item in changed:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("path"), str)
            or (not item["path"].endswith(".sql") and item.get("status") != "renamed")
            or not isinstance(item.get("status"), str)
        ):
            raise CheckError("The changed-SQL list contains an invalid entry.")
    return changed


def _validate_compare_result(stdout: str) -> dict[str, Any]:
    try:
        result = json.loads(stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        raise CheckError(f"The DeltaData CLI did not return valid JSON: {exc}") from exc
    if not isinstance(result, dict):
        raise CheckError("The DeltaData CLI returned an unexpected JSON shape.")
    if result.get("status") != "ok":
        message = (
            f"DeltaData analysis did not complete successfully "
            f"(status: {result.get('status')!r})."
        )
        detail = result.get("error") or result.get("summary")
        if isinstance(detail, str) and detail:
            message += f" {detail}"
        raise CheckError(message)
    allowed_classifications = {
        "NO_CHANGE",
        "BENIGN_CHANGE",
        "BEHAVIORAL_CHANGE",
        "BREAKING_CHANGE",
    }
    if result.get("classification") not in allowed_classifications:
        raise CheckError(
            f"DeltaData returned an unsupported or missing classification: "
            f"{result.get('classification')!r}."
        )
    allowed_risk_levels = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    risk_level = result.get("risk_level")
    if not isinstance(risk_level, str) or risk_level.upper() not in allowed_risk_levels:
        raise CheckError(f"DeltaData returned an unsupported or missing risk level: {risk_level!r}.")
    if not isinstance(result.get("change_detected"), bool):
        raise CheckError("DeltaData returned a missing or invalid change_detected value.")
    if (result["classification"] == "NO_CHANGE") != (result["change_detected"] is False):
        raise CheckError("DeltaData returned inconsistent change detection and classification.")
    tests = result.get("tests")
    if not isinstance(tests, list):
        raise CheckError("DeltaData returned a missing or invalid tests list.")
    allowed_test_statuses = {"PASS", "FAIL", "CHANGE_DETECTED"}
    for index, test in enumerate(tests):
        if not isinstance(test, dict) or test.get("status") not in allowed_test_statuses:
            status = test.get("status") if isinstance(test, dict) else None
            raise CheckError(
                f"DeltaData test {index + 1} is incomplete or unsupported (status: {status!r})."
            )
    return result


def _run_compare(command: list[str], cwd: Path) -> None:
    completed = subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True)
    try:
        result = _validate_compare_result(completed.stdout)
    except CheckError as exc:
        if completed.returncode:
            raise CheckError(str(exc), exit_code=completed.returncode) from exc
        raise
    print(json.dumps(result, indent=2))
    if result["risk_level"] in {"HIGH", "CRITICAL"}:
        raise CheckError(
            "DeltaData detected HIGH or CRITICAL risk in changed SQL.",
            exit_code=1,
        )
    if completed.returncode:
        detail = completed.stderr.strip()
        message = f"DeltaData CLI exited with code {completed.returncode}."
        if detail:
            message += f" CLI stderr: {detail!r}"
        raise CheckError(message, exit_code=completed.returncode)


def _base_data_files(repo_root: Path, base_sha: str, sql_path: str) -> list[str]:
    directory = PurePosixPath(sql_path).parent
    result = subprocess.run(
        ["git", "ls-tree", "-r", "-z", "--name-only", base_sha],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    return sorted(
        name for name in result.stdout.decode("utf-8").split("\0")
        if name.endswith(".csv")
        and PurePosixPath(name).parent in (directory, directory / "data")
    )


def _stage_base_data_file(repo_root: Path, base_sha: str, path: str, dest: Path) -> None:
    result = subprocess.run(
        ["git", "show", f"{base_sha}:{path}"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    dest.write_bytes(result.stdout)


def _git_exists(commit: str, path: str, repo_root: Path) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{commit}:{path}"],
        cwd=repo_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def compare_changed_sql(args: argparse.Namespace) -> None:
    if args.head_repository != args.repository:
        raise CheckError("Fork pull requests are not analyzed with DeltaData credentials.")
    if not os.environ.get("DELTADATA_API_URL") or not os.environ.get("DELTADATA_API_KEY"):
        raise CheckError(
            "DELTADATA_API_URL and DELTADATA_API_KEY must be configured for same-repository SQL PRs."
        )

    repo_root = Path(args.repo_root).resolve()
    changed = _read_changed_sql(args.changed_sql_b64)
    merge_base = _git_merge_base(args.base_sha, args.head_sha, repo_root)
    git_changed = _git_changed_sql(merge_base, args.head_sha, repo_root)
    if sorted(changed, key=lambda item: item["path"]) != sorted(
        git_changed, key=lambda item: item["path"]
    ):
        raise CheckError(
            "The GitHub file list does not match the changed SQL at the specified PR commits; "
            "refusing to analyze a stale or incomplete list."
        )
    compared = 0
    for item in changed:
        path = item["path"]
        if item["status"] != "modified":
            print(f"Skipping {path}: {item['status']} SQL has no matching two-version comparison.")
            continue
        if PurePosixPath(path).name == "before.sql":
            print(f"Skipping {path}: before.sql is the baseline, not a changed candidate.")
            continue
        baseline_path = (
            str(PurePosixPath(path).with_name("before.sql"))
            if PurePosixPath(path).name == "after.sql" else path
        )
        if not _git_exists(merge_base, baseline_path, repo_root):
            print(f"Skipping {path}: no baseline SQL at {baseline_path} in merge-base.")
            continue
        data_files = _base_data_files(repo_root, args.base_sha, path)
        if not data_files:
            print(f"Skipping {path}: no trusted base-version CSV in its directory or data/ subdirectory.")
            continue
        basenames = [PurePosixPath(file).name.casefold() for file in data_files]
        if len(basenames) != len(set(basenames)):
            print(f"Skipping {path}: duplicate CSV basenames make table names ambiguous.")
            continue
        before_sql = _git_show(merge_base, baseline_path, repo_root)
        after_sql = _git_show(args.head_sha, path, repo_root)

        with tempfile.TemporaryDirectory(prefix="deltadata-pr-") as temp_dir:
            before_path = Path(temp_dir) / "before.sql"
            after_path = Path(temp_dir) / "after.sql"
            before_path.write_text(before_sql, encoding="utf-8")
            after_path.write_text(after_sql, encoding="utf-8")
            staged_data = []
            for index, file in enumerate(data_files):
                folder = Path(temp_dir) / "data" / str(index)
                folder.mkdir(parents=True)
                dest = folder / PurePosixPath(file).name
                _stage_base_data_file(repo_root, args.base_sha, file, dest)
                staged_data.append(dest)
            command = [
                "deltadata",
                "compare",
                "--before",
                str(before_path),
                "--after",
                str(after_path),
                "--fail-on",
                "high",
                "--json",
            ]
            for data_file in staged_data:
                command.extend(["--data", str(data_file)])
            print(f"Analyzing changed query {path} with trusted base-version CSV data")
            _run_compare(command, repo_root)
            compared += 1
    if not compared:
        print("No comparable changed SQL with trusted sample data; check passed.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="List changed PR SQL paths.")
    inspect.add_argument("--repository", required=True)
    inspect.add_argument("--pull-number", required=True, type=int)
    inspect.add_argument("--changed-count", required=True, type=int)
    inspect.add_argument("--output", required=True)
    inspect.set_defaults(handler=inspect_pull_request)

    compare = commands.add_parser("compare", help="Compare changed example SQL safely.")
    compare.add_argument("--repository", required=True)
    compare.add_argument("--head-repository", required=True)
    compare.add_argument("--base-sha", required=True)
    compare.add_argument("--head-sha", required=True)
    compare.add_argument("--changed-sql-b64", required=True)
    compare.add_argument("--repo-root", default=os.getcwd())
    compare.set_defaults(handler=compare_changed_sql)

    args = parser.parse_args(argv)
    try:
        args.handler(args)
    except CheckError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return exc.exit_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())