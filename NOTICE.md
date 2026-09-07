# Third-party notices and data boundaries

The Unlicense applies only to original code and text contributed to this
repository. It does not state terms for third-party material.

## Archived response corpus

The five CSVs under `data/responses/` are currently distributed in this
repository as the frozen research inputs analyzed by the paper. The archived
runs used EDSL 1.0.7 with its universal cache enabled for first attempts and
disabled for parser retries. The retained technical provenance chain is
recorded in `data/run_manifest.json`: collection dates, source commit and pull
request, cache settings and unknown cache fields, prompt hashes, parser
provenance, record counts, and file checksums. In particular, the manifest
records that per-response cache-hit status was not retained.

Model-provider and Expected Parrot terms require provider-by-provider review
before deciding how to redistribute archived model outputs. This repository
does not yet record such a completed audit or state whether those terms permit
or restrict redistribution for any provider. The corpus's current inclusion is
a description of repository contents, not a conclusion about third-party
terms.

## Other third-party boundaries

- Model names and trademarks belong to their respective owners.
- The scenario sample was derived from PolicyEngine-US data. PolicyEngine-US and
  its upstream datasets retain their own licenses and attribution requirements.
- No figures or tables copied from third-party publications are distributed in
  the publication build.

Users should review applicable provider and dataset terms before redistributing
raw responses or source-derived data.

## Retained legacy laboratory archives

`data/legacy_lab/` preserves a previously tracked response pickle and a recovered
local numeric CSV for a separate provenance audit. These are not the five
Study 2 response CSVs described above, and their collection provenance does
not inherit that corpus's EDSL version or cache settings. The adjacent manifest
records exact hashes and known recovery locations. The same provider-by-provider
author review remains required before any eventual release of these outputs;
their inclusion in this review draft does not resolve third-party terms.
The cited human articles and registry are source evidence only. No participant
microdata or human analysis code has been obtained or redistributed.
