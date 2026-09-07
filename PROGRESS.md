# Publication provenance sprint

## State

2026-09-07: Offline continuation on `codex/pr43-provenance-20260907` of PR43's
exact independently reviewed head `f3b23873f7240491cb40d6378c9080cbd23fd726`.
Live head/base/check verification is blocked by GitHub DNS/network access.
Cached `origin/main` is `899daa612cecaee08dbf9a279d4b03ea4c5fb6d2` and is an
ancestor of that head; no cached-base integration is needed. The original
`/Users/maxghenis/llm-eti` checkout is clean on `ti_resolved` and untouched.

## Done

- Read global and project instructions and the independent PR43 review.
- Inspected original status, branches, remotes and cached base; attempted live
  PR lookup and fetch (both failed: GitHub could not be resolved).
- Created an isolated worktree from the exact reviewed commit.
- Confirmed reset prevention remains enabled and automatic resets disabled.

## Next

1. Reproduce dirty-manuscript attestation and staged-generated-drift failures.
2. Enforce truthful release provenance and HEAD-based drift checks; regressions.
3. Regenerate and validate the publication and historical-parser reconciliation
   of all 8,095 archived responses without inference or paid compute.
4. Prepare review-ready branch/patch and evidence; reverify live PR state before
   any remote update. No publication, merge, or collaborator messaging.
5. If PR43 closes with time remaining, isolate PR44 manifest/checkpoint work.

Final lane report: `/Users/maxghenis/capacity-sprint-20260907/llm-eti/result.md`.
Stop launching work at 21:00 America/New_York; preserve no-reset controls.
