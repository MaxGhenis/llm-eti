#!/usr/bin/env python3
"""Reapply the archived parser to every response, without inference or API access."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import re
import subprocess
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
PARSER_COMMIT = "b23f2cb882d33f79d706afbdcca836b3905361f8"
PARSER_PATH = "llm_eti/edsl_client.py"
PARSER_SHA256 = "7c274bd9d6796aef6c60473f8800a1a8ed9ebc1345db7c58e3742611ee02f399"
IncomeParser = Callable[[object], dict[str, float | None]]


def archived_parser(root: Path, *, verify_git_origin: bool = False) -> IncomeParser:
    archive = (root / "protocols/legacy_income_parser.md").read_text()
    (excerpt,) = re.findall(r"````python\n(.*?)````", archive, re.DOTALL)
    if hashlib.sha256(excerpt.encode()).hexdigest() != PARSER_SHA256:
        raise ValueError("Historical parser excerpt hash mismatch")
    if verify_git_origin:
        historical = subprocess.run(
            ["git", "show", f"{PARSER_COMMIT}:{PARSER_PATH}"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        (method,) = (
            node
            for node in ast.walk(ast.parse(historical))
            if isinstance(node, ast.FunctionDef)
            and node.name == "_parse_income_response"
        )
        first_line = min(
            [method.lineno, *(node.lineno for node in method.decorator_list)]
        )
        original_excerpt = "".join(
            historical.splitlines(keepends=True)[first_line - 1 : method.end_lineno]
        )
        if original_excerpt != excerpt:
            raise ValueError("Archived parser does not match its Git origin")
    # Execute only the hash-pinned method, never import the historical API client.
    tree = ast.parse("from __future__ import annotations\n" + textwrap.dedent(excerpt))
    method_node = tree.body[1]
    assert isinstance(method_node, ast.FunctionDef)
    method_node.decorator_list = []
    namespace: dict[str, object] = {"ast": ast, "re": re}
    exec(compile(tree, "protocols/legacy_income_parser.md", "exec"), namespace)
    return cast(IncomeParser, namespace["_parse_income_response"])


def _stored_number(value: str) -> float | None:
    if not value.strip():
        return None
    numeric = float(value)
    return None if math.isnan(numeric) else numeric


def reconcile_file(path: Path, parser: IncomeParser) -> dict[str, object]:
    """Use CSV record numbers, not line counts: raw responses can contain newlines."""
    mismatches = []
    rows = 0
    with path.open(newline="", encoding="utf-8") as stream:
        for rows, row in enumerate(csv.DictReader(stream), start=1):
            parsed = parser(row["income_response_raw"])
            for field in ("broad_income", "taxable_income"):
                stored = _stored_number(row[f"{field}_this"])
                observed = parsed[field]
                if observed != stored:
                    mismatches.append(
                        {
                            "record": rows,
                            "field": field,
                            "stored": stored,
                            "reparsed": observed,
                        }
                    )
    return {
        "rows": rows,
        "numeric_values_compared": 2 * rows,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


def reconcile_archive(
    root: Path, *, verify_git_origin: bool = False
) -> dict[str, object]:
    parser = archived_parser(root, verify_git_origin=verify_git_origin)
    manifest = json.loads((root / "data/run_manifest.json").read_text())
    paths = sorted((root / "data/responses").glob("*.csv"))
    expected = {
        name for name in manifest["files"] if name.startswith("data/responses/")
    }
    if {path.relative_to(root).as_posix() for path in paths} != expected:
        raise ValueError("Response file inventory does not match the frozen manifest")
    files = {}
    total_rows = total_values = total_mismatches = 0
    for path in paths:
        name = path.relative_to(root).as_posix()
        result = reconcile_file(path, parser)
        if result["sha256"] != manifest["files"][name]["sha256"]:
            raise ValueError(f"Frozen response hash mismatch: {name}")
        if result["rows"] != manifest["files"][name]["records"]:
            raise ValueError(f"Frozen response record count mismatch: {name}")
        files[name] = result
        total_rows += cast(int, result["rows"])
        total_values += cast(int, result["numeric_values_compared"])
        total_mismatches += cast(int, result["mismatch_count"])
    return {
        "parser_commit": PARSER_COMMIT,
        "parser_path": PARSER_PATH,
        "parser_excerpt_sha256": PARSER_SHA256,
        "git_origin_verified": verify_git_origin,
        "response_rows": total_rows,
        "numeric_values_compared": total_values,
        "mismatch_count": total_mismatches,
        "files": files,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-git-origin", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = reconcile_archive(ROOT, verify_git_origin=args.verify_git_origin)
    rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(rendered)
    else:
        print(rendered, end="")
    if report["mismatch_count"]:
        raise SystemExit("Archived responses differ from the historical parser")


if __name__ == "__main__":
    main()
