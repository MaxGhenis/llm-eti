# Scope of the scientific correction

The reference methods were independently reviewed at
`1f6c23a0c00f0c197cd16e5b235f1e8420d9ee49`. Their integration into this repository
requires a separate coordinator scientific/code review. Passing synthetic tests
does not validate an empirical estimator, human replication or LLM treatment.

The package `llm_eti.lab_methods` ports the reviewed reference core, finite-menu
utility counterexamples, exact KW roots, subject-resampling diagnostics,
completion bounds and synthetic CSV reader. Its original 54 regressions are
retained in `tests/test_lab_methods.py`. `reference-provenance.json` records
original file hashes and integration changes. The standalone reference report
CLI and its generated data are not copied; tests generate explicitly synthetic
fixtures locally. The saved documents preserve the original scientific contract;
module paths now live under the package. Current host source evidence supplements
the reference lane's earlier source-access limitations.

The only real-data adapter is `llm_eti.lab_archive`. It accepts two exact byte
streams for auditing and rejects both for estimation. No new treatment is
declared from these old rows. No support subset is selected after inspecting
outcomes or missing cells. Full missingness bounds also remain unavailable:
completed rows cannot reveal entirely missing planned subjects.

The paper adds a budget/identification correction and generated archive audit.
Its existing Study 2 estimators, sample definitions, six raw inputs and numerical
results remain unchanged. PR44's checkpoint work and old paper artifacts are
preserved as separate scope. Legacy notch-ETI/bound claims are not supported by
this draft; the correction does not attribute that identification argument to
the human-study authors.

For a future compatible archive, record the actual immutable run/instrument,
planned subjects and all attempts, cap/round assignments, parsed/raw choices,
state/history and independent-draw/cache evidence. Declare target cap weights,
zero handling and sequence comparison before estimating. The current reviewed
reference is conditional on a complete selected subject×phase×cap grid, not a
general estimator for arbitrary randomized or incomplete human panels.
