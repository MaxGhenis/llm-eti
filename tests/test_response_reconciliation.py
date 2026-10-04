import csv
from pathlib import Path

from scripts.reconcile_responses import (
    archived_parser,
    reconcile_archive,
    reconcile_file,
)

ROOT = Path(__file__).resolve().parents[1]


def test_all_8095_archived_responses_reconcile_with_historical_parser():
    report = reconcile_archive(ROOT)
    assert report["response_rows"] == 8095
    assert report["numeric_values_compared"] == 16190
    assert report["mismatch_count"] == 0


def test_reconciliation_detects_changed_numeric_value_and_preserves_zero(tmp_path):
    path = tmp_path / "responses.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "income_response_raw",
                "broad_income_this",
                "taxable_income_this",
            ],
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "income_response_raw": '```json\n{"broad_income": 1200, "taxable_income": 0}\n```',
                    "broad_income_this": "1200",
                    "taxable_income_this": "0",
                },
                {
                    "income_response_raw": '{"answer": {"broad_income": null, "taxable_income": 400}}',
                    "broad_income_this": "",
                    "taxable_income_this": "401",
                },
            ]
        )
    report = reconcile_file(path, archived_parser(ROOT))
    assert report["rows"] == 2
    assert report["numeric_values_compared"] == 4
    assert report["mismatches"] == [
        {"record": 2, "field": "taxable_income", "stored": 401.0, "reparsed": 400.0}
    ]
