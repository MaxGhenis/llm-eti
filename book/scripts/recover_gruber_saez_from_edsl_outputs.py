#!/usr/bin/env python3
"""Recover Gruber-Saez results from raw EDSL output files.

This script rebuilds a final CSV from `edsl_output_tax_*.csv` files created
within a time window. It reconstructs the original household scenario from the
question text, joins back to the PolicyEngine input CSV, parses the model
answer, and computes the implied ETI fields.
"""

import argparse
import re
import sys
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.append(str(Path(__file__).parent.parent.parent))

from llm_eti.edsl_client import EDSLClient

ET = ZoneInfo("America/New_York")
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V3"


def _default_window() -> tuple[datetime, datetime]:
    today = date.today()
    return (
        datetime.combine(today, time(13, 20), tzinfo=ET),
        datetime.combine(today, time(15, 3), tzinfo=ET),
    )


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ET)
    return dt.astimezone(ET)


def _file_mtime_et(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=ET)


def _select_files(directory: Path, start: datetime, end: datetime) -> list[Path]:
    files = []
    for path in sorted(directory.glob("edsl_output_tax_*.csv")):
        mtime = _file_mtime_et(path)
        if start <= mtime <= end:
            files.append(path)
    return files


def _parse_prompt(question_text: str) -> dict[str, float]:
    patterns = {
        "broad_income": r"Last year, your broad income was \$([0-9,]+)",
        "taxable_income": r"Last year, your taxable income was \$([0-9,]+)",
        "mtr_last_pct": r"Last year, your marginal tax rate was (-?[0-9]+)%",
        "mtr_this_pct": r"marginal tax rate this year will be (-?[0-9]+)%",
    }
    parsed: dict[str, float] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, question_text)
        if not match:
            raise ValueError(f"Could not parse {key} from question text")
        parsed[key] = float(match.group(1).replace(",", ""))
    return parsed


def _build_source_lookup(source_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(source_csv)
    df["broad_income_round"] = df["broad_income"].round().astype(int)
    df["taxable_income_round"] = df["taxable_income"].round().astype(int)
    df["mtr_pct"] = (df["mtr"] * 100).astype(int)
    df["mtr_prime_pct"] = (df["mtr_prime"] * 100).astype(int)

    key_cols = [
        "broad_income_round",
        "taxable_income_round",
        "mtr_pct",
        "mtr_prime_pct",
    ]
    dupes = df.duplicated(subset=key_cols, keep=False)
    if dupes.any():
        print(
            f"Warning: {dupes.sum()} source rows share the same rounded join key; "
            "using the first match for each key."
        )

    return df.drop_duplicates(subset=key_cols, keep="first").set_index(key_cols)


def _find_source_row(
    lookup: pd.DataFrame, prompt_info: dict[str, float]
) -> pd.Series | None:
    key = (
        int(round(prompt_info["broad_income"])),
        int(round(prompt_info["taxable_income"])),
        int(prompt_info["mtr_last_pct"]),
        int(prompt_info["mtr_this_pct"]),
    )
    try:
        row = lookup.loc[key]
    except KeyError:
        return None

    if isinstance(row, pd.DataFrame):
        return row.iloc[0]
    return row


def recover_results(
    input_dir: Path,
    source_csv: Path,
    output_csv: Path,
    start: datetime,
    end: datetime,
    model_name: str,
) -> pd.DataFrame:
    lookup = _build_source_lookup(source_csv)
    files = _select_files(input_dir, start, end)
    print(f"Selected {len(files)} raw files from {start} to {end}")

    rows: list[dict[str, object]] = []
    skipped = 0

    for path in files:
        file_mtime = _file_mtime_et(path)
        timestamp = file_mtime.strftime("%Y-%m-%d %H:%M:%S")
        df = pd.read_csv(path)

        for response_number, (_, raw_row) in enumerate(df.iterrows(), start=1):
            if str(raw_row.get("model.model", "")).strip() != model_name:
                continue

            try:
                prompt_info = _parse_prompt(
                    str(raw_row["question_text.income_responses_question_text"])
                )
            except Exception as exc:
                skipped += 1
                print(f"Skipping {path.name} row {response_number}: {exc}")
                continue

            source_row = _find_source_row(lookup, prompt_info)
            if source_row is None:
                skipped += 1
                print(
                    "Skipping unmatched scenario in "
                    f"{path.name} row {response_number}: "
                    f"broad_income={prompt_info['broad_income']}, "
                    f"taxable_income={prompt_info['taxable_income']}, "
                    f"mtr_last_pct={prompt_info['mtr_last_pct']}, "
                    f"mtr_this_pct={prompt_info['mtr_this_pct']}"
                )
                continue

            parsed = EDSLClient._parse_income_response(
                raw_row.get("answer.income_responses")
            )
            broad_income_this = parsed["broad_income"]
            taxable_income_this = parsed["taxable_income"]
            if broad_income_this is None or taxable_income_this is None:
                skipped += 1
                continue

            broad_income = float(source_row["broad_income"])
            taxable_income = float(source_row["taxable_income"])
            mtr = float(source_row["mtr"])
            mtr_prime = float(source_row["mtr_prime"])

            rows.append(
                {
                    "timestamp": timestamp,
                    "tax_unit_id": source_row["tax_unit_id"],
                    "filing_status": source_row.get("filing_status"),
                    "broad_income": broad_income,
                    "taxable_income": taxable_income,
                    "mtr": mtr,
                    "mtr_prime": mtr_prime,
                    "response_number": response_number,
                    "taxable_income_this": taxable_income_this,
                    "broad_income_this": broad_income_this,
                    "implied_eti_taxable": EDSLClient.calculate_eti(
                        mtr, mtr_prime, taxable_income, taxable_income_this
                    ),
                    "implied_eti_broad": EDSLClient.calculate_eti(
                        mtr, mtr_prime, broad_income, broad_income_this
                    ),
                    "model": raw_row.get("model.model", model_name),
                    "income_response_raw": raw_row.get("answer.income_responses"),
                }
            )

    result_df = pd.DataFrame(rows)
    if result_df.empty:
        raise RuntimeError(
            "No valid rows were recovered from the selected EDSL output files"
        )

    output_csv.parent.mkdir(exist_ok=True)
    result_df.to_csv(output_csv, index=False)
    print(f"Recovered {len(result_df)} rows; skipped {skipped} invalid rows")
    print(f"Wrote {output_csv}")
    return result_df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recover Gruber-Saez output from raw EDSL CSV files"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path(__file__).parent,
        help="Directory containing edsl_output_tax_*.csv files",
    )
    parser.add_argument(
        "--source-csv",
        type=Path,
        default=Path(__file__).parent.parent.parent
        / "policy_engine_simulation"
        / "policyengine_sample_incomes.csv",
        help="PolicyEngine input CSV used to generate the prompts",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path(__file__).parent.parent
        / "data"
        / "gruber_saez_results_deepseek-ai_DeepSeek-V3.csv",
        help="Destination CSV path",
    )
    parser.add_argument(
        "--start",
        type=str,
        default=None,
        help="Start of the time window in ISO format, interpreted as ET if naive",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="End of the time window in ISO format, interpreted as ET if naive",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help="Model name to keep from the raw CSV files",
    )
    args = parser.parse_args()

    default_start, default_end = _default_window()
    start = _parse_dt(args.start) if args.start else default_start
    end = _parse_dt(args.end) if args.end else default_end

    recover_results(
        input_dir=args.input_dir,
        source_csv=args.source_csv,
        output_csv=args.output_csv,
        start=start,
        end=end,
        model_name=args.model,
    )


if __name__ == "__main__":
    main()
