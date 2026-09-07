# Offline checkpoint compatibility sprint

## State

2026-09-07: isolated branch `codex/pr44-checkpoint-manifest-20260907` from PR44's
reviewed commit `cf102a2a221c13b36283a8a6a20fad4b547d4f3c`. Cached `origin/main`
`899daa612cecaee08dbf9a279d4b03ea4c5fb6d2` is already an ancestor. GitHub live
verification/fetch is blocked by network/DNS. This is an offline continuation,
not a claim of current live PR state or validated experimental results.

## Done

- Read global/project instructions and the independent PR44 review.
- Inspected clean original checkout, branch, remotes and cached base.
- Kept PR43 provenance fixes in their separate branch/worktree; that local
  implementation is complete, with external publication/review gates blocked.
- Created this fresh isolated continuation; no original checkout modifications.

- Reproduced the original eight-round →16-round checkpoint mixing with a fake
  client (eight new calls, wrong rounds 5–8 retained); evidence in
  `../evidence/pr44-before.json`.
- Implemented a full deterministic PCG64 scenario manifest, prompt/config/model/
  source fingerprinting, fail-closed checkpoint compatibility, an append-only
  attempt ledger, retryable failure handling, preserved zeros, and a local
  exclusive writer lock. The CLI keeps attempts separate from derived results.
- First targeted suite: 24 tests pass using the existing Python 3.12 environment,
  including three fresh interpreter hash-seed comparisons. Added further input,
  fractional-rate-label, prompt-source, and actual process-resume regressions.
  Expanded suite: 35 passed; changed-area Black/Ruff and core Mypy pass.

## Next

1. Reproduce eight-round/16-round checkpoint mixing with a fake client.
2. Persist experiment identity and full deterministic scenario design before
   requests; reject incompatible or manifest-free existing checkpoints.
3. Cover config, prompt, model, seed, malformed rows and interrupted writes
   using realistic offline regressions. Never run paid model collection.
4. Commit reviewable code and handoff. Leave all estimators/results unchanged;
   PR44's methodological findings remain unresolved and ETIs unvalidated.

Final lane report: `/Users/maxghenis/capacity-sprint-20260907/llm-eti/result.md`.
Preserve no-reset controls; stop launching new work at 21:00 America/New_York.
