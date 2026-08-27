"""Render a /api/v1/compare response as a human-readable terminal summary."""
from __future__ import annotations

from typing import Any

_HEADER = "DeltaData Behavioral Regression Analysis"


def render_human(result: dict[str, Any]) -> str:
    lines: list[str] = [_HEADER, ""]

    if result.get("status") == "error":
        lines.append("Result: EXECUTION ERROR")
        lines.append("")
        lines.append(result.get("error") or result.get("summary") or "The analysis could not be completed.")
        return "\n".join(lines)

    classification = result.get("classification", "UNKNOWN")
    risk_level = result.get("risk_level")
    change_types = result.get("change_types") or []

    if change_types:
        lines.append("Change types: " + ", ".join(change_types))
    lines.append(f"Classification: {classification}")
    if risk_level:
        lines.append(f"Risk: {risk_level}")
    lines.append(f"Change detected: {'Yes' if result.get('change_detected') else 'No'}")
    lines.append("")

    summary = (result.get("summary") or "").strip()
    if summary:
        lines.append("Change:")
        lines.append(summary)
        lines.append("")

    tests = result.get("tests") or []
    findings = [t for t in tests if t.get("status") == "CHANGE_DETECTED"]
    if findings:
        lines.append("Findings:")
        for test in findings:
            name = test.get("name", "test")
            severity = test.get("severity", "")
            reason = test.get("reason", "")
            lines.append(f"  - [{severity}] {name}")
            lines.append(f"    {reason}")
        lines.append("")

    recommendation = result.get("recommendation")
    if recommendation:
        lines.append("Recommendation:")
        lines.append(recommendation)

    return "\n".join(lines).rstrip() + "\n"
