#!/usr/bin/env python3
"""Check a veraPDF XML report against the reviewed PDF/UA-2 baseline."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

FATAL_BATCH_COUNTERS = (
    "failedToParse",
    "encrypted",
    "outOfMemory",
    "veraExceptions",
)


def _local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _elements(root: ET.Element, name: str) -> list[ET.Element]:
    return [element for element in root.iter() if _local_name(element) == name]


def _integer_attribute(element: ET.Element, attribute: str) -> int:
    value = element.get(attribute)
    try:
        return int(value or "")
    except ValueError as error:
        raise ValueError(f"veraPDF report has invalid {attribute}={value!r}") from error


def _failed_rule_id(rule: ET.Element) -> str:
    fields = [rule.get(name) for name in ("specification", "clause", "testNumber")]
    if not all(fields):
        raise ValueError("A failed veraPDF rule lacks a stable identifier")
    return "|".join(str(field) for field in fields)


def check_report(report_path: Path, baseline_path: Path) -> set[str]:
    """Validate report health and reject failed rules outside the baseline."""

    try:
        root = ET.parse(report_path).getroot()
    except (ET.ParseError, OSError) as error:
        raise ValueError(
            f"Could not parse veraPDF report {report_path}: {error}"
        ) from error

    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise ValueError(
            f"Could not read veraPDF baseline {baseline_path}: {error}"
        ) from error
    if not isinstance(baseline, dict) or baseline.get("profile") != "ua2":
        raise ValueError("veraPDF baseline must declare the ua2 profile")
    expected_version = baseline.get("verapdf_version")
    if not isinstance(expected_version, str) or not expected_version:
        raise ValueError("veraPDF baseline must declare its veraPDF version")
    accepted = baseline.get("accepted_failed_rule_ids")
    if (
        not isinstance(accepted, list)
        or any(not isinstance(rule_id, str) or not rule_id for rule_id in accepted)
        or accepted != sorted(set(accepted))
    ):
        raise ValueError(
            "veraPDF baseline rule identifiers must be unique, sorted strings"
        )
    accepted_rule_ids = set(accepted)

    core_releases = [
        element
        for element in _elements(root, "releaseDetails")
        if element.get("id") == "core"
    ]
    if len(core_releases) != 1 or core_releases[0].get("version") != expected_version:
        observed_versions = [element.get("version") for element in core_releases]
        raise ValueError(
            f"Expected veraPDF core {expected_version}, found {observed_versions}"
        )

    batch_summaries = _elements(root, "batchSummary")
    if len(batch_summaries) != 1:
        raise ValueError(
            f"Expected one veraPDF batch summary, found {len(batch_summaries)}"
        )
    batch_summary = batch_summaries[0]
    if _integer_attribute(batch_summary, "totalJobs") != 1:
        raise ValueError("veraPDF must process exactly one PDF")
    batch_failures = {
        counter: _integer_attribute(batch_summary, counter)
        for counter in FATAL_BATCH_COUNTERS
    }
    batch_failures = {key: value for key, value in batch_failures.items() if value}
    if batch_failures:
        raise ValueError(f"veraPDF could not process the PDF cleanly: {batch_failures}")

    validation_summaries = _elements(batch_summary, "validationReports")
    if len(validation_summaries) != 1:
        raise ValueError("veraPDF report lacks one validation summary")
    if _integer_attribute(validation_summaries[0], "failedJobs") != 0:
        raise ValueError("veraPDF reports a failed validation job")

    validation_reports = _elements(root, "validationReport")
    if len(validation_reports) != 1:
        raise ValueError(
            f"Expected one veraPDF validation report, found {len(validation_reports)}"
        )
    validation_report = validation_reports[0]
    profile_name = validation_report.get("profileName", "")
    if "PDF/UA-2" not in profile_name.upper():
        raise ValueError(f"veraPDF used an unexpected profile: {profile_name!r}")

    failed_rule_ids = {
        _failed_rule_id(rule)
        for rule in _elements(validation_report, "rule")
        if rule.get("status") == "failed"
    }
    details = _elements(validation_report, "details")
    if len(details) != 1:
        raise ValueError("veraPDF validation report lacks one details element")
    if _integer_attribute(details[0], "failedRules") != len(failed_rule_ids):
        raise ValueError(
            "veraPDF failed-rule count disagrees with its rule identifiers"
        )

    compliance = validation_report.get("isCompliant")
    if compliance not in {"true", "false"}:
        raise ValueError(f"veraPDF reports invalid compliance state {compliance!r}")
    if (compliance == "true") != (not failed_rule_ids):
        raise ValueError("veraPDF compliance state disagrees with its failed rules")

    new_failures = sorted(failed_rule_ids - accepted_rule_ids)
    if new_failures:
        raise ValueError(f"New PDF/UA-2 rule failures: {new_failures}")
    resolved_failures = sorted(accepted_rule_ids - failed_rule_ids)
    if resolved_failures:
        print(
            f"Previously accepted PDF/UA-2 failures are now resolved: {resolved_failures}"
        )
    print(
        "veraPDF processed one PDF; accepted failed rule identifiers: "
        f"{sorted(failed_rule_ids)}"
    )
    return failed_rule_ids


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("baseline", type=Path)
    arguments = parser.parse_args()
    try:
        check_report(arguments.report, arguments.baseline)
    except ValueError as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
