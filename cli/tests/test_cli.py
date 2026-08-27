"""Unit tests for the deltadata CLI -- argument parsing, formatting, exit
codes. All API calls are mocked; nothing here talks to a real server (see
tests/test_live_e2e.md-style verification run separately against the live
artifacts/api-server workflow for true end-to-end coverage)."""
from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from deltadata_cli import cli, formatting
from deltadata_cli.client import DeltaDataAPIError


@pytest.fixture()
def sql_files(tmp_path):
    before = tmp_path / "before.sql"
    after = tmp_path / "after.sql"
    before.write_text("SELECT COUNT(DISTINCT customer_id) AS cnt FROM orders;")
    after.write_text("SELECT COUNT(customer_id) AS cnt FROM orders;")
    data = tmp_path / "orders.csv"
    data.write_text("customer_id\n1\n1\n2\n")
    return {"before": str(before), "after": str(after), "data": str(data)}


def _ok_result(risk_level="HIGH", status="ok", change_detected=True):
    return {
        "status": status,
        "change_detected": change_detected,
        "classification": "BREAKING_CHANGE" if risk_level in ("HIGH", "CRITICAL") else "BENIGN_CHANGE",
        "risk_level": risk_level,
        "change_types": ["METRIC_DEFINITION_CHANGE"],
        "summary": "COUNT(DISTINCT customer_id) changed to COUNT(customer_id)",
        "tests": [
            {
                "name": "customer_count_behavior",
                "type": "AGGREGATION_CHECK",
                "status": "CHANGE_DETECTED",
                "severity": risk_level,
                "reason": "customer_count_behavior: 6 -> 10 (+66.7%)",
            }
        ],
        "recommendation": "Confirm whether the intended business metric is unique customers or total rows.",
        "error": None,
    }


def _error_result():
    return {
        "status": "error",
        "change_detected": False,
        "classification": "EXECUTION_ERROR",
        "risk_level": None,
        "change_types": [],
        "summary": "The provided SQL failed to execute against the uploaded data.",
        "tests": [],
        "recommendation": "Fix the SQL execution error before this change can be evaluated.",
        "error": "The provided SQL failed to execute against the uploaded data.",
    }


# ── argument parsing ─────────────────────────────────────────────────────────

def test_missing_required_argument_exits_usage_error(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.build_parser().parse_args(["compare", "--before", "x.sql"])
    assert exc_info.value.code == cli.EXIT_USAGE_ERROR
    assert "error" in capsys.readouterr().err


def test_missing_data_file_is_usage_error(sql_files, capsys):
    code = cli.main(
        [
            "compare",
            "--before", sql_files["before"],
            "--after", sql_files["after"],
            "--data", "/does/not/exist.csv",
        ]
    )
    assert code == cli.EXIT_USAGE_ERROR
    assert "not found" in capsys.readouterr().err


def test_missing_before_file_is_usage_error(sql_files, capsys):
    code = cli.main(
        [
            "compare",
            "--before", "/does/not/exist.sql",
            "--after", sql_files["after"],
            "--data", sql_files["data"],
        ]
    )
    assert code == cli.EXIT_USAGE_ERROR
    assert "--before" in capsys.readouterr().err


@pytest.mark.parametrize("bad_timeout", ["0", "-5", "-0.1", "not-a-number"])
def test_invalid_timeout_is_usage_error(sql_files, capsys, bad_timeout):
    code = cli.main(
        [
            "compare",
            "--before", sql_files["before"],
            "--after", sql_files["after"],
            "--data", sql_files["data"],
            "--timeout", bad_timeout,
        ]
    )
    assert code == cli.EXIT_USAGE_ERROR
    assert "timeout" in capsys.readouterr().err.lower()


def test_invalid_fail_on_choice_is_usage_error(sql_files, capsys):
    code = cli.main(
        [
            "compare",
            "--before", sql_files["before"],
            "--after", sql_files["after"],
            "--data", sql_files["data"],
            "--fail-on", "extreme",
        ]
    )
    assert code == cli.EXIT_USAGE_ERROR


def test_repeated_data_flag_collects_multiple_files(sql_files, monkeypatch, tmp_path):
    second = tmp_path / "customers.csv"
    second.write_text("customer_id\n1\n2\n")
    captured = {}

    def fake_call_compare(**kwargs):
        captured["data_paths"] = kwargs["data_paths"]
        return _ok_result(risk_level="LOW", change_detected=False)

    monkeypatch.setattr(cli, "call_compare", fake_call_compare)
    code = cli.main(
        [
            "compare",
            "--before", sql_files["before"],
            "--after", sql_files["after"],
            "--data", sql_files["data"],
            "--data", str(second),
        ]
    )
    assert code == cli.EXIT_OK
    assert captured["data_paths"] == [sql_files["data"], str(second)]


# ── exit codes driven by API responses ──────────────────────────────────────

def test_high_risk_exceeding_default_fail_on_exits_nonzero(sql_files, monkeypatch, capsys):
    monkeypatch.setattr(cli, "call_compare", lambda **kwargs: _ok_result(risk_level="HIGH"))
    code = cli.main(
        ["compare", "--before", sql_files["before"], "--after", sql_files["after"], "--data", sql_files["data"]]
    )
    assert code == cli.EXIT_RISK_THRESHOLD
    assert "Risk: HIGH" in capsys.readouterr().out


def test_low_risk_stays_below_default_fail_on(sql_files, monkeypatch):
    monkeypatch.setattr(cli, "call_compare", lambda **kwargs: _ok_result(risk_level="LOW", change_detected=False))
    code = cli.main(
        ["compare", "--before", sql_files["before"], "--after", sql_files["after"], "--data", sql_files["data"]]
    )
    assert code == cli.EXIT_OK


def test_fail_on_none_never_fails_on_risk(sql_files, monkeypatch):
    monkeypatch.setattr(cli, "call_compare", lambda **kwargs: _ok_result(risk_level="CRITICAL"))
    code = cli.main(
        [
            "compare", "--before", sql_files["before"], "--after", sql_files["after"],
            "--data", sql_files["data"], "--fail-on", "none",
        ]
    )
    assert code == cli.EXIT_OK


def test_fail_on_medium_flags_high_risk(sql_files, monkeypatch):
    monkeypatch.setattr(cli, "call_compare", lambda **kwargs: _ok_result(risk_level="HIGH"))
    code = cli.main(
        [
            "compare", "--before", sql_files["before"], "--after", sql_files["after"],
            "--data", sql_files["data"], "--fail-on", "medium",
        ]
    )
    assert code == cli.EXIT_RISK_THRESHOLD


def test_fail_on_critical_does_not_flag_high_risk(sql_files, monkeypatch):
    monkeypatch.setattr(cli, "call_compare", lambda **kwargs: _ok_result(risk_level="HIGH"))
    code = cli.main(
        [
            "compare", "--before", sql_files["before"], "--after", sql_files["after"],
            "--data", sql_files["data"], "--fail-on", "critical",
        ]
    )
    assert code == cli.EXIT_OK


def test_execution_error_exits_distinct_code_regardless_of_fail_on(sql_files, monkeypatch, capsys):
    monkeypatch.setattr(cli, "call_compare", lambda **kwargs: _error_result())
    code = cli.main(
        [
            "compare", "--before", sql_files["before"], "--after", sql_files["after"],
            "--data", sql_files["data"], "--fail-on", "none",
        ]
    )
    assert code == cli.EXIT_EXECUTION_ERROR
    assert "EXECUTION ERROR" in capsys.readouterr().out


def test_api_connection_failure_is_usage_error(sql_files, monkeypatch, capsys):
    def raise_api_error(**kwargs):
        raise DeltaDataAPIError("Could not connect to the DeltaData API at 'http://bad-host'.")

    monkeypatch.setattr(cli, "call_compare", raise_api_error)
    code = cli.main(
        ["compare", "--before", sql_files["before"], "--after", sql_files["after"], "--data", sql_files["data"]]
    )
    assert code == cli.EXIT_USAGE_ERROR
    assert "Could not connect" in capsys.readouterr().err


def test_json_output_matches_raw_api_response(sql_files, monkeypatch, capsys):
    result = _ok_result(risk_level="MEDIUM")
    monkeypatch.setattr(cli, "call_compare", lambda **kwargs: result)
    code = cli.main(
        [
            "compare", "--before", sql_files["before"], "--after", sql_files["after"],
            "--data", sql_files["data"], "--json",
        ]
    )
    assert code == cli.EXIT_OK
    printed = json.loads(capsys.readouterr().out)
    assert printed == result


# ── formatting ───────────────────────────────────────────────────────────────

def test_render_human_includes_before_after_in_finding_reason():
    text = formatting.render_human(_ok_result(risk_level="HIGH"))
    assert "Risk: HIGH" in text
    assert "6 -> 10" in text
    assert "Recommendation:" in text


def test_render_human_execution_error_shows_error_message():
    text = formatting.render_human(_error_result())
    assert "EXECUTION ERROR" in text
    assert "failed to execute" in text
