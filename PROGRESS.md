# Publication provenance sprint

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

## Pinned render and color backend (2026-09-07)

State: Quarto 1.9.38 verified against the official release SHA-256 and checksum
file. The initial pinned render reproduced visible RGB text despite passing
veraPDF 1.30.2 with an empty failed-rule baseline. Root's independent review
approved provenance at 6ee5cfc only; this later rendering scope is not covered.

Done: isolated the defect to stale July l3backend files shadowing matching
August l3kernel backend files in TinyTeX. A minimal document reproduces it;
selecting task-local copies of the matching files fixes it without modifying
shared TeX. Added a template behavior check (color selection must have zero
width), a PDF extracted-text gate, and four real LuaLaTeX/Poppler regressions.
Toolchain sources, hashes, minimal reproductions and signed veraPDF installation
evidence are saved in sibling toolchains/ and evidence/.

Next: commit source, regenerate with pinned Quarto and matching TeX backend,
run the full publication gate, historical reconciliation, veraPDF and visual
inspection; then update the existing draft PR43 and record final CI results.

## Host validation closure

State: the publication continuation is locally validated and prepared for a
normal fast-forward update of existing draft PR43. Main and the live PR head
were verified before work; the reviewed 6ee5cfc revision and prior dirty figure
rebuild remain intact in the original isolated worktree.

Done: `make publication` passed at 5dced8a with official Quarto 1.9.38 and
matching task-local TeX backend files: 85 tests, Black, Ruff, Mypy, source and
output provenance, all local links, generated drift, and PDF text/tagging checks.
The 21-page PDF passed veraPDF 1.30.2 PDF/UA-2 with zero failed rules and an
unchanged empty exception baseline. Visually inspected pages 2, 3, 10, 20 and 21:
blue citations and URLs are intact, no RGB operands appear, and the results
figure/table remain readable. The exported TeX ZIP compiles independently.
Historical parser reconciliation verifies its original Git source and all
8,095 responses / 16,190 numeric values with zero mismatches. Canonical data,
analysis implementation and generated numeric/text artifacts match f3b2387.

The subsequent documentation checkpoint is rerendered so its manifest binds
the final committed source. Exact final heads, remote checks, hashes, and the
review-resolution record are saved in the lane's followup-HANDOFF.md and
followup-result.md. Root's independent approval is restricted to provenance
at 6ee5cfc; it does not approve the later render safeguards or a paper release.

Next: review the existing draft and retain all author/release gates in
PUBLICATION_CHECKLIST.md. No release tag, Pages deployment, paper submission,
merge, model collection or estimator redesign is authorized by this checkpoint.

## CI rendering-regression coverage

The initial updated PR43 head 1111dfe passed both CI jobs and actual PDF/UA-2
validation. Downloaded CI artifacts match all 97 local source hashes and their
output checksums. CI built the PR merge commit 0f542a3, whose source tree matches
the continuation. Its four optional TeX tests skipped because Quarto finds
TinyTeX outside PATH. The build job now explicitly requires the installed
LuaLaTeX path and supplies it to those tests; Python 3.12 compatibility can
still skip them when no TeX installation is present. This closes a discovered
CI coverage gap, without relaxing any output gate.

## State

2026-09-07: PR43 provenance implementation is complete locally on
`codex/pr43-provenance-20260907`, based on reviewed head
`f3b23873f7240491cb40d6378c9080cbd23fd726`. Release/remote closure is blocked:
GitHub and the independent-review provider cannot resolve from this sandbox;
local Quarto is 1.9.36 instead of required 1.9.38. No live PR/check status or
independent approval is claimed. No push, publication, merge, model collection,
paid compute, usage reset, or reset-setting change occurred.

## Done

- Read global/project instructions and the independent PR43/PR44 reviews.
- Inspected status, branch, remotes and cached base before edits. Original
  `/Users/maxghenis/llm-eti` remains clean on `ti_resolved` and untouched.
- Created this isolated worktree from the exact reviewed PR43 commit. Cached
  `origin/main` (`899daa612cecaee08dbf9a279d4b03ea4c5fb6d2`) is already an ancestor.
  Live lookup/fetch attempts failed with GitHub DNS errors; cached is not live.
- Reproduced dirty manuscript attribution and staged generated drift in a
  disposable Git repository; saved `../evidence/before-regressions.json`.
- Required clean source against HEAD, checked both index and worktree, hashed
  all tracked sources, bound the manifest to actual source and commit, and
  checked source identity before/after rendering. Only the ten named existing
  generated image outputs may differ by platform and are separately hashed.
- Added direct Git-blob/executable-bit comparisons after two additional tests
  showed assume-unchanged/skip-worktree can hide dirty manuscript bytes.
- Added a repeatable historical-parser audit: all 8,095 records / 16,190 income
  values match; zero mismatches. Verified the parser excerpt byte-for-byte with
  historical commit `b23f2cb882d33f79d706afbdcca836b3905361f8`.
- 81 tests pass (baseline 55); Black, Ruff, Mypy pass. Generated prose/numeric
  artifacts and variables have zero drift from HEAD and the index.
- Rendered the entire publication with an explicitly opted-out Quarto 1.9.36
  for diagnostics: HTML, tagged 22-page PDF, retained TeX, source ZIP and hashes.
  Strict check correctly rejects that version. Remaining integrity checks pass
  when only that version expectation is changed in memory for diagnostics.
- Visually inspected PDF pages 1, 3, 10 and 22. Main results/figure are readable,
  but citations visibly contain stray `0.0 0.0 1.0` values in this off-pin local
  toolchain. The preview is not suitable for release. No full veraPDF run.
- One bounded semantic Subfleet review was attempted on pinned Thesis
  `.codex-5`; run `20260907-170228-review-md` could not connect to chatgpt.com.
  Stopped its network retries (exit 130); no verdict or approval. Initial
  detached launch produced no review/run output.

## Next

1. Restore permitted network access and fetch/verify live PR43 head, base,
   checks, and draft state before updating any remote branch. Safely integrate
   any new head/base changes; never overwrite the original checkout.
2. Run `make publication` with Quarto 1.9.38 and a compatible LaTeX environment,
   inspect citation rendering, then run the existing veraPDF/UA-2 CI gate.
3. Obtain the bounded independent review when the subscription lane is reachable.
4. Use the prepared draft update and patch/bundle in the lane directory; do not
   publish or merge. Author/redistribution approval conditions remain intact.
5. Optional PR44 manifest/checkpoint work belongs in a separate isolated branch,
   without estimator changes, model collection, or claims of validated ETIs.

Generated figure modifications visible in this worktree are this sprint's
platform rebuild outputs, intentionally uncommitted under the documented
exception. They are not manuscript or analysis changes. All six canonical
inputs and numerical results are unchanged.

Durable evidence and final report:
`/Users/maxghenis/capacity-sprint-20260907/llm-eti/result.md` and `evidence/` beside
this worktree. Preserve `no-reset.json` and `auto_reset.enabled=false` after the
21:00 America/New_York sprint deadline.
