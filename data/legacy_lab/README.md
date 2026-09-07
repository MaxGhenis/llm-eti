# Retained legacy lab inputs

These files are separate from the six immutable Study 2 inputs and its 8,095
responses. They are preserved for an offline provenance audit, not accepted as
a validated replication or prospectively designed experiment.

`provenance.json` records exact bytes, hashes and recovery locations. The pickle
was already tracked in repository history. The Gemini CSV was recovered from
the original checkout's ignored `book/data` directory. No source file was edited.
The historical collector is inert `.txt` evidence and must not be executed.
It samples caps with replacement from a different menu, sends stateless prompts,
and saves observations after collection; it does not save a run-bound planned
inventory, delivered prompts or attempt/cache ledger. Its presence alongside
the pickle does not establish which revision actually generated each response.

`llm_eti.lab_archive` verifies fixed hashes before reading either archive. It
decodes only the exact known pickle with a restricted class list; provider SDK
objects become inert state containers. All stored answer strings are checked
against saved response payloads. Free text is not converted to task choices by
guessing an income. The CSV's recorded numeric choices are checked without
dropping zeros, clipping or rounding. Its raw provider answers are unavailable.

Every real-data estimation entry point in this adapter raises `DesignError`.
No full planned roster, independent subject count, standardized outcome,
bootstrap interval, missing-outcome completion range or structural notch ETI is
invented. The generated audit lists observed coverage and specific blockers.
Synthetic methods are under `llm_eti/lab_methods`; their acceptance cannot
authenticate a historical run. PR44's future checkpoint format is separate and
cannot retroactively supply these missing facts.

Run `uv run python scripts/generate_artifacts.py` to regenerate the audit and
the existing Study 2 results. Author approval and the publication checklist
still govern any eventual release; this continuation is a draft only.
