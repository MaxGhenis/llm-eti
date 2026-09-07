# Offline lab checkpoint contract

This patch addresses experiment identity and restart correctness only. It does
not validate the legacy experiment against the human PKNF study or repair the
ETI estimators and published claims flagged in the independent PR44 review.
Do not interpret fixture outputs as model observations or validated ETIs.

Before any survey request, the runner constructs every planned subject/round
scenario and atomically persists `<checkpoint>.manifest.json`. The experiment
digest covers the full design, round count and effective midpoint reform timing,
treatments, subject count, precise rates, wage/endowment configuration, explicit
seed, PCG64/NumPy identity, requested model, cache setting, instruction text,
prompt/client/engine source hashes, and installed EDSL version. Scenario IDs
bind individual rows to that design. The seeded endowments are stable across
processes and Python hash seeds. This is a new deterministic design: it cannot
recover the unrecorded random seeds of historical checkpoint files.

Existing checkpoints must have an exactly matching manifest. Every row is
validated against its planned scenario before any request. Missing manifests,
different experiments, malformed/truncated rows, unknown scenarios, altered
tax schedules, invalid income values, duplicate successes and out-of-order
attempts fail closed. Existing CSVs are never erased after a read error and no
automatic migration invents historical provenance. Preserve legacy files and
choose a new output directory for a new experiment.

The CSV is an append-only attempt ledger with stable experiment/scenario IDs,
monotonic per-scenario attempts, status, raw response, and UTC record time.
Only a successful finite income in the offered range completes a scenario;
zero is valid. Empty/unparseable replies remain retryable. Transport exceptions
are recorded as failures and then re-raised. A resumed run retries failed rows
and retains prior failure records. CSV writes are flushed and fsynced; a local
nonblocking POSIX file lock prevents simultaneous writers. A complete manifest
with no CSV can resume after interruption before the first request. A partially
written CSV requires explicit investigation instead of silently losing rows.

`run_experiment` returns the latest row per scenario. The CLI stores its derived
result snapshot in the selected output directory and keeps the append-only
checkpoint in `checkpoints/`, outside the result CSV glob. Filenames distinguish
round count, seed and precise tax rates. `--output-dir` supports a separate
directory for an intentionally incompatible run. Never overwrite the ledger
with the returned dataframe.

Offline verification (uses the existing local environment; no API calls):

```bash
python -m pytest -q tests/test_lab_checkpoint.py
```

The tests use `tests/offline_lab_client.py`, which borrows the real instruction
and prompt-construction methods but returns explicit synthetic responses. They
cover the eight-round/16-round mixing regression, pre-request design persistence,
prompt/config/model/cache/seed incompatibility, successful zero responses,
retryable failures with quoted multiline raw text, interrupted transport,
malformed CSVs, duplicate rows, competing writers, and three fresh interpreters
with different `PYTHONHASHSEED` values.

Remaining limits: moving provider aliases are not immutable model revisions;
historical cache hits and transport subattempts inside EDSL are not recovered.
A process killed during a request before writing its response may retry that
request on restart, and independence of cached repeated prompts is not
established. These are checkpoint compatibility guarantees, not a complete
prospective request ledger or a validated new experimental protocol. The lock
requires POSIX and assumes a local filesystem. PR44's estimator, zero-selection,
provider-metadata parsing, and scientific-validation findings remain open.
