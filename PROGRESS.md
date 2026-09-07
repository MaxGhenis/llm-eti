# Offline checkpoint compatibility sprint

## Host follow-up state

2026-09-07: Network access restored. Live PR heads and fetched main verified:
PR43 f3b23873f7240491cb40d6378c9080cbd23fd726; PR44
cf102a2a221c13b36283a8a6a20fad4b547d4f3c; main
899daa612cecaee08dbf9a279d4b03ea4c5fb6d2. Each reviewed continuation already
contains its live head and current main. New isolated host continuation preserves
reviewed revisions 6ee5cfc/e71e837 and the original worktrees; PR43 figure changes
were snapshotted to sibling evidence/followup-start before any further build.

Done: live PR43 remains draft, prior checks passed; PR44 is an open contributor
PR with maintainer edits allowed and a prior lint failure. No remote writes yet.
Root is supplying a host review of the two exact reviewed commits.

Next: use task-local verified official Quarto 1.9.38; diagnose citation color
rendering and validate PDF/UA; apply host findings; safely fast-forward the
existing PR branches as drafts after review, with accurate final evidence.
No nested reviewers, model collection, paid jobs, resets, publication or merges.
Final host report: sibling followup-result.md.

## State

2026-09-07: local implementation and offline verification complete on
`codex/pr44-checkpoint-manifest-20260907`, from reviewed PR44 commit
`cf102a2a221c13b36283a8a6a20fad4b547d4f3c`. Cached `origin/main`
`899daa612cecaee08dbf9a279d4b03ea4c5fb6d2` is an ancestor. Live head/base/check
verification and remote submission remain blocked by GitHub network/DNS.
This is an isolated continuation, separate from the PR43 provenance patch.

## Done

- Read global/project instructions and the independent PR44 review. Inspected
  original status/branch/remotes/base and left that clean checkout untouched.
- Reproduced eight-round →16-round checkpoint mixing with a fake client:
  only eight new calls, with wrong treatment assignments retained for rounds
  5–8. Evidence: `../evidence/pr44-before.json`.
- Persisted complete deterministic PCG64 scenario designs and an experiment
  digest covering configuration, effective reform timing, prompts, model/cache,
  implementation sources, seed and package versions before requests.
- Added strict row/manifest compatibility, scenario identities, crash-safe
  manifest replacement, append-only/fsynced attempts and a POSIX writer lock.
  Successful zeros remain completed; failures are retained and retried.
- Separated CLI attempt ledgers from derived results, included round count,
  seed and precise rates in filenames, and added an output-directory option.
- Added 35 targeted tests, including four fresh-interpreter checks, real quoted
  multiline CSV fixtures, corrupt/legacy checkpoint rejection, prompt/config/
  model drift, failures, zeros and concurrent writers. All pass in the frozen
  Python 3.13.9 environment with pinned EDSL 1.0.7, installed entirely offline.
  They also passed in the preexisting Python 3.12 environment (EDSL 1.0.1).
- Fixed the preexisting E402 import-order CI failure in `edsl_client.py` without
  changing API/parse behavior. Whole-repository Ruff and Black now pass; Mypy
  passes for the three changed implementation/runner files with imports skipped.
- Added a repeatable synthetic-fixture exporter: 64 scenarios, four retained
  parse failures, four successful retries, and four successful zeros. These are
  fake-client regression artifacts, explicitly not model observations or ETIs.
- Documented the contract and remaining limits in `CHECKPOINT_COMPATIBILITY.md`.
  No estimator, manuscript/result claim, historical CSV, or model collection
  was changed. No API key is used by these tests or fixture exports.

## Next

1. Fetch and verify live PR44 head/base/checks when GitHub is reachable; integrate
   new head/base commits safely before any remote draft update.
2. Review the isolated manifest patch using the saved draft update and bundle.
   No independent semantic approval is claimed: the single sprint review attempt
   on PR43 was blocked by provider connectivity; no additional lane was launched.
3. Keep PR44's economic estimators, valid-zero selection, provider-metadata
   parsing and human-validation findings open. The legacy protocol is explicitly
   unvalidated. No publication or merge is authorized by this handoff.
4. A production protocol still needs immutable provider revisions, explicit
   cache independence, and an attempt ledger spanning in-flight/EDSL subrequests.
   A kill during a model request can cause that request to be retried on restart.

Final report: `/Users/maxghenis/capacity-sprint-20260907/llm-eti/result.md`.
Durable detailed handoff: sibling `HANDOFF.md`; tests/logs: sibling `evidence/`;
synthetic fixture: sibling `artifacts/pr44-synthetic-fixture-frozen/`.
Preserve no-reset.json and auto_reset.enabled=false after the 21:00 deadline.
