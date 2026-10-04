import json
from pathlib import Path

import pytest

from scripts.check_verapdf import check_report

ROOT = Path(__file__).resolve().parents[1]


def test_verapdf_release_gate_is_pinned_and_starts_without_exceptions():
    baseline = json.loads((ROOT / ".github" / "verapdf-baseline.json").read_text())
    assert baseline == {
        "accepted_failed_rule_ids": [],
        "profile": "ua2",
        "verapdf_version": "1.30.2",
    }
    workflow = (ROOT / ".github" / "workflows" / "publication.yml").read_text()
    image = (
        "verapdf/cli:v1.30.2@sha256:"
        "d5ee329657cf9bc4b2400392dd54c7d0a0ce9980ff6fa2da5590eebeec007cdb"
    )
    assert image in workflow
    assert workflow.index("make publication") < workflow.index("--flavour ua2")
    assert workflow.index("--flavour ua2") < workflow.index(
        "Upload verified publication"
    )


def _report(*, rule: str = "", compliant: bool = True, failed_to_parse: int = 0) -> str:
    failed_rules = int(bool(rule))
    return f"""\
<report>
  <buildInformation>
    <releaseDetails id="core" version="1.30.2" />
  </buildInformation>
  <jobs>
    <job>
      <validationReport profileName="PDF/UA-2 validation profile"
        isCompliant="{str(compliant).lower()}">
        <details failedRules="{failed_rules}">{rule}</details>
      </validationReport>
    </job>
  </jobs>
  <batchSummary totalJobs="1" failedToParse="{failed_to_parse}"
    encrypted="0" outOfMemory="0" veraExceptions="0">
    <validationReports failedJobs="0">1</validationReports>
  </batchSummary>
</report>
"""


def _write_gate_files(
    directory: Path, report: str, accepted: list[str]
) -> tuple[Path, Path]:
    report_path = directory / "report.xml"
    baseline_path = directory / "baseline.json"
    report_path.write_text(report, encoding="utf-8")
    baseline_path.write_text(
        json.dumps(
            {
                "profile": "ua2",
                "verapdf_version": "1.30.2",
                "accepted_failed_rule_ids": accepted,
            }
        ),
        encoding="utf-8",
    )
    return report_path, baseline_path


def test_verapdf_gate_accepts_a_compliant_report(tmp_path: Path):
    report, baseline = _write_gate_files(tmp_path, _report(), [])
    assert check_report(report, baseline) == set()


def test_verapdf_gate_accepts_only_reviewed_failed_rules(tmp_path: Path):
    rule_id = "ISO 14289-2:2024|7.1|1"
    failed_rule = (
        '<rule specification="ISO 14289-2:2024" clause="7.1" '
        'testNumber="1" status="failed" />'
    )
    report, baseline = _write_gate_files(
        tmp_path,
        _report(rule=failed_rule, compliant=False),
        [rule_id],
    )
    assert check_report(report, baseline) == {rule_id}

    baseline.write_text(
        json.dumps(
            {
                "profile": "ua2",
                "verapdf_version": "1.30.2",
                "accepted_failed_rule_ids": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="New PDF/UA-2 rule failures"):
        check_report(report, baseline)


def test_verapdf_gate_rejects_pdf_parse_failures(tmp_path: Path):
    report, baseline = _write_gate_files(tmp_path, _report(failed_to_parse=1), [])
    with pytest.raises(ValueError, match="could not process the PDF cleanly"):
        check_report(report, baseline)
