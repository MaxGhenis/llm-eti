"""Check that every number inside each paper table's tabular body matches a
fresh regeneration from the frozen inputs.

Captions, labels, notes and spacing may be edited by hand in Overleaf; the
numbers inside \\begin{tabular}...\\end{tabular} may not.

Usage: python scripts/check_paper_tables.py REGENERATED_DIR PAPER_TABLES_DIR NAME=REGEN_NAME ...
"""

import re
import sys
from pathlib import Path

NUMBER = re.compile(r"-?\d[\d,]*\.?\d*")
TABULAR = re.compile(r"\\begin\{tabular\}.*?\\end\{tabular\}", re.S)


def numbers(path: Path) -> list[str]:
    text = path.read_text()
    bodies = TABULAR.findall(text)
    if not bodies:
        raise SystemExit(f"{path}: no tabular environment")
    # Ignore column specs such as {lrrr} and spacing like \\[10pt].
    body = re.sub(r"\\\\\[\d+pt\]", r"\\\\", "".join(bodies))
    return NUMBER.findall(body)


def main(argv: list[str]) -> int:
    regenerated, paper, pairs = Path(argv[0]), Path(argv[1]), argv[2:]
    failures = 0
    for pair in pairs:
        name, _, regen_name = pair.partition("=")
        expected, actual = numbers(regenerated / (regen_name or name)), numbers(
            paper / name
        )
        if expected != actual:
            failures += 1
            diff = [
                (i, e, a)
                for i, (e, a) in enumerate(zip(expected, actual))
                if e != a
            ][:5]
            print(
                f"MISMATCH {name}: {len(expected)} vs {len(actual)} numbers; "
                f"first differences {diff}"
            )
        else:
            print(f"ok {name}: {len(actual)} numbers match")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
