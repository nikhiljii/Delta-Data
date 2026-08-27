"""Unit tests for deltadata_cli.client -- HTTP status handling.

/api/v1/compare's own contract (see artifacts/api-server/routers/v1_compare.py):
- HTTP 200 always means the API produced a real compare result, which may
  itself carry {"status": "error", "classification": "EXECUTION_ERROR", ...}
  when the SUPPLIED SQL failed to execute against the data.
- Any non-2xx (400/401/413/422/500/503/504) means the API rejected the
  request/infrastructure failed before or instead of producing a compare
  result -- bad input, size limits, auth, a server fault, or an analysis
  timeout. These must never be confused with an EXECUTION_ERROR result.
"""
from __future__ import annotations

import os
import sys

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from deltadata_cli.client import DeltaDataAPIError, call_compare


class _FakeResponse:
    def __init__(self, status_code: int, json_body=None, text: str = ""):
        self.status_code = status_code
        self._json_body = json_body
        self.text = text if text else (str(json_body) if json_body is not None else "")

    def json(self):
        if self._json_body is None:
            raise ValueError("no JSON body")
        return self._json_body


@pytest.fixture()
def sql_file_pair(tmp_path):
    data = tmp_path / "orders.csv"
    data.write_text("customer_id\n1\n2\n")
    return [str(data)]


@pytest.mark.parametrize("status_code", [400, 401, 413, 422, 500, 503, 504])
def test_non_2xx_status_raises_typed_api_error(monkeypatch, sql_file_pair, status_code):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **kw: _FakeResponse(status_code, json_body={"status": "error", "error": "boom"}),
    )
    with pytest.raises(DeltaDataAPIError) as exc_info:
        call_compare(
            api_url="http://example.test",
            api_key="key",
            old_sql="SELECT 1",
            new_sql="SELECT 1",
            data_paths=sql_file_pair,
        )
    assert str(status_code) in str(exc_info.value)
    assert "boom" in str(exc_info.value)


def test_504_analysis_timeout_raises_typed_api_error_not_execution_error(monkeypatch, sql_file_pair):
    """A 504 from the API (its own analysis-timeout path) must not be
    mistaken for the SQL-execution-error case, which is HTTP 200."""
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **kw: _FakeResponse(504, json_body={"status": "error", "error": "Analysis timed out."}),
    )
    with pytest.raises(DeltaDataAPIError):
        call_compare(
            api_url="http://example.test",
            api_key="key",
            old_sql="SELECT 1",
            new_sql="SELECT 1",
            data_paths=sql_file_pair,
        )


def test_200_execution_error_body_is_returned_not_raised(monkeypatch, sql_file_pair):
    """The one case where status == 'error' must NOT raise -- it's the real
    SQL-execution-failure result, and the CLI maps it to EXIT_EXECUTION_ERROR."""
    body = {
        "status": "error",
        "classification": "EXECUTION_ERROR",
        "change_detected": False,
        "risk_level": None,
        "change_types": [],
        "summary": "failed",
        "tests": [],
        "recommendation": "fix it",
        "error": "failed",
    }
    monkeypatch.setattr(httpx, "post", lambda *a, **kw: _FakeResponse(200, json_body=body))
    result = call_compare(
        api_url="http://example.test",
        api_key="key",
        old_sql="SELECT 1",
        new_sql="SELECT 1",
        data_paths=sql_file_pair,
    )
    assert result == body


def test_200_ok_body_is_returned(monkeypatch, sql_file_pair):
    body = {"status": "ok", "risk_level": "LOW", "classification": "NO_CHANGE"}
    monkeypatch.setattr(httpx, "post", lambda *a, **kw: _FakeResponse(200, json_body=body))
    result = call_compare(
        api_url="http://example.test",
        api_key="key",
        old_sql="SELECT 1",
        new_sql="SELECT 1",
        data_paths=sql_file_pair,
    )
    assert result == body


def test_non_json_2xx_response_raises_typed_api_error(monkeypatch, sql_file_pair):
    monkeypatch.setattr(httpx, "post", lambda *a, **kw: _FakeResponse(200, json_body=None, text="<html>oops</html>"))
    with pytest.raises(DeltaDataAPIError):
        call_compare(
            api_url="http://example.test",
            api_key="key",
            old_sql="SELECT 1",
            new_sql="SELECT 1",
            data_paths=sql_file_pair,
        )
