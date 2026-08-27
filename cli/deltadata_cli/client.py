"""Thin HTTP client for the DeltaData /api/v1/compare endpoint.

Deliberately dumb: it never parses SQL, never touches the analysis engine,
and never re-derives risk/classification. It just posts the request and
hands back whatever JSON the API returned (or raises `DeltaDataAPIError` for
anything that stopped it from getting a compare response at all).
"""
from __future__ import annotations

import os
import ssl
from typing import Any

import httpx

DEFAULT_TIMEOUT_SECONDS = 60.0

# httpx defaults to the certifi-vendored CA bundle rather than the system
# trust store. That bundle can be missing CAs the host OS already trusts
# (e.g. an internal proxy's certificate authority), which surfaces as a
# confusing CERTIFICATE_VERIFY_FAILED even though the same host works fine
# with curl or a browser. Build the SSL context from the system's default
# verify paths (honoring SSL_CERT_FILE/SSL_CERT_DIR when set) instead, so
# the CLI trusts whatever the machine it runs on already trusts.
_SSL_CONTEXT = ssl.create_default_context()


class DeltaDataAPIError(Exception):
    """Raised when the CLI could not obtain a compare result from the API --
    connection failures, auth failures, or the API rejecting the request
    before it could run an analysis (4xx/5xx with no usable body)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _extract_error_message(response: "httpx.Response") -> str:
    try:
        body = response.json()
        if isinstance(body, dict):
            return body.get("error") or body.get("detail") or response.text
    except Exception:
        pass
    return response.text or f"HTTP {response.status_code}"


def call_compare(
    api_url: str,
    api_key: str,
    old_sql: str,
    new_sql: str,
    data_paths: list[str],
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """POST old_sql/new_sql/data files to `{api_url}/api/v1/compare`.

    Returns the parsed JSON body on any response the API produced (including
    its own stable {"status": "error", ...} bodies -- callers decide what to
    do with those). Raises DeltaDataAPIError only when no such body could be
    obtained at all (network failure, timeout, or a response that isn't the
    documented JSON shape).
    """
    url = api_url.rstrip("/") + "/api/v1/compare"
    headers = {"X-API-Key": api_key} if api_key else {}

    open_files = [open(path, "rb") for path in data_paths]
    try:
        files = [
            ("files", (os.path.basename(path), fh, "text/csv"))
            for path, fh in zip(data_paths, open_files)
        ]
        try:
            response = httpx.post(
                url,
                data={"old_sql": old_sql, "new_sql": new_sql},
                files=files,
                headers=headers,
                timeout=timeout,
                verify=_SSL_CONTEXT,
            )
        except httpx.ConnectError as exc:
            raise DeltaDataAPIError(
                f"Could not connect to the DeltaData API at {api_url!r}. "
                f"Is it running, and is --api-url correct? ({exc})"
            ) from exc
        except httpx.TimeoutException as exc:
            raise DeltaDataAPIError(
                f"Request to the DeltaData API timed out after {timeout:g}s ({exc})."
            ) from exc
        except httpx.HTTPError as exc:
            raise DeltaDataAPIError(f"HTTP request to the DeltaData API failed: {exc}") from exc
    finally:
        for fh in open_files:
            fh.close()

    # Every non-2xx response from /api/v1/compare is the API rejecting the
    # request itself -- bad input (400/422), size limits (413), auth
    # (401/503), a server-side fault (500), or an analysis timeout (504).
    # None of these mean "the supplied SQL failed to execute": that specific
    # case is reported as HTTP 200 with a `{"status": "error", "classification":
    # "EXECUTION_ERROR", ...}` body (handled by the caller as EXIT_EXECUTION_ERROR).
    # Conflating the two would make CI unable to tell "your SQL is broken"
    # apart from "the request/infrastructure is broken", so every non-2xx
    # response is surfaced as a DeltaDataAPIError (-> EXIT_USAGE_ERROR) instead.
    if response.status_code < 200 or response.status_code >= 300:
        raise DeltaDataAPIError(
            f"DeltaData API returned HTTP {response.status_code}: {_extract_error_message(response)}"
        )

    try:
        body = response.json()
    except Exception as exc:
        raise DeltaDataAPIError(
            f"DeltaData API returned a non-JSON response (HTTP {response.status_code})."
        ) from exc

    if not isinstance(body, dict) or "status" not in body:
        raise DeltaDataAPIError(
            f"DeltaData API returned an unexpected response shape (HTTP {response.status_code})."
        )

    return body
