# Third-party notices and data boundaries

The Unlicense applies only to original code and text contributed to this
repository. It does not state terms for third-party material.

## Archived response corpus

The five CSVs under `data/responses/` are currently distributed in this
repository as the frozen research inputs analyzed by the paper. They were
exported through EDSL's universal-cache path. The retained technical provenance
chain is recorded in `data/run_manifest.json`: collection dates, EDSL version,
source commit and pull request, cache settings and unknown cache fields, prompt
hashes, parser provenance, record counts, and file checksums. In particular,
the manifest records that per-response cache-hit status was not retained.

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
