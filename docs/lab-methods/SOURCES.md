# Integrated source evidence

This host evidence supplements the earlier methods lane's
[reference source ledger](REFERENCE-SOURCES.md). The registry and instrument
were subsequently retrieved and visually checked; the earlier network blockers
are historical. Primary equation locations remain in the reference ledger.
No public human microdata or analysis code were obtained.

The source captures and visual audit remain in the local coordinator artifact
`llm-eti-human-sources/`; the paper links the official sources. Links to that
lane's other local files below are evidence locators, not bundled downloads.

---

# Source and access ledger

Access checked on **2026-09-07** with ordinary public HTTPS on the host. No sign-in, existing browser cookies, author contact, access-request submission, paid service, or access-control bypass was used. Retrieval is closed after confirming the public-data blocker. The initial web-tool registry/DOI opens failed; host requests succeeded. These are different outcomes, and the earlier DNS blocker is no longer the explanation.

Every host response is retained locally under `downloads/` with exact URL, UTC retrieval timestamp, HTTP status, byte length, and SHA256 in [retrieval-ledger.jsonl](retrieval-ledger.jsonl). A saved HTTP error page is labelled as an error, never as article content. `downloads/` and the rendered source pages in `visuals/` are excluded from git. The existing launcher/session logs are preserved and excluded too.

## Official routes inspected

| Capture ID | Public source and discovery path | Result |
| --- | --- | --- |
| `paper-2024-landing` | [CESifo/ifo working-paper record](https://www.ifo.de/en/cesifo/publications/2024/working-paper/tax-system-design-tax-reform-and-labor-supply) | Links the official 2024 PDF; no study data/code link found on this record. |
| `paper-2024-pdf` | [Official CESifo WP 11350 PDF](https://www.ifo.de/DocDL/cesifo1_wp11350.pdf), linked from the preceding record | 70 pages, 5,571,399 bytes; September 2024 benchmark. Title-page acknowledgment points to the AEA registry for data/code. |
| `registry-doi` | [Unversioned trial DOI](https://doi.org/10.1257/rct.8410), printed in the paper | Redirects successfully to trial 8410; the page's own citation identifies version 1.0. |
| `registry-8410-html` | [Official trial 8410](https://www.socialscienceregistry.org/trials/8410) | Public-data field says **No**. Program Files and External Links are empty. No public analysis-plan, attachment, or paper links. |
| `registry-history` | [Trial history](https://www.socialscienceregistry.org/trials/8410/history), linked on the trial page | One public version, 1.0, June 3, 2022. Full-trial link returns to the same record. No new archive route. |
| `article-2025-doi` | [2025 Labour Economics DOI](https://doi.org/10.1016/j.labeco.2025.102810) | Elsevier linking-hub HTML directs to ScienceDirect article S0927537125001344. |
| `article-2025-publisher` | [ScienceDirect article](https://www.sciencedirect.com/science/article/pii/S0927537125001344), identified by the DOI | Host HTTP 403, publisher error page. No retry or bypass. Search returned a publisher excerpt, but the availability finding below was independently read in the actual article PDF. |
| `article-2025-ifo` | [ifo journal-publication record](https://www.ifo.de/en/publications/2025/contribution-refereed-journal/asymmetric-labor-supply-responses-tax-rate-reform), found by exact-title search | Lists Labour Economics 97, 102810 and links the DOI. No independent replication archive link. |
| `author-kasper` | [Kasper's Walter Eucken Institute profile](https://www.eucken.de/mitarbeiter/dr-matthias-kasper-phd/), found by author search | Inspected public publication links; no target-study data/code link found. This is a limited negative claim about this page. |
| `article-2025-freidok` | [University of Freiburg repository record 272410](https://freidok.uni-freiburg.de/data/272410), found by exact-title search | Official institutional archive, not assumed to be the 2024 replication package. HTML citation metadata links two PDFs. |
| `freidok-public-page-script` | [Public landing-page script](https://freidok.uni-freiburg.de/assets/b821701d/landingpage/lp.js), explicitly loaded by the repository page | Read to identify the ordinary public metadata GET used by this JavaScript-rendered page. No experiment code; never executed. |
| `article-2025-freidok-metadata` | [Public record metadata](https://freidok.uni-freiburg.de/jsonApi/v1/publications?publicationId=272410&maxPers=25&lessPersAffiliations=true&available=issued&fieldset=lp&maxRows=1&lang=en), using the endpoint and parameters exposed by that page/script | Two files only, both PDFs; no external files, relations, or reverse relations. Archive-provided SHA256 values independently match both downloaded PDFs. |
| `article-2025-main-pdf` | [Archived publisher article](https://freidok.uni-freiburg.de/files/272410/5JdEZUZKs1su5E2w/1-s2.0-S0927537125001344-main.pdf), linked in repository metadata | 15 pages. Page 10 says: **“Data will be made available on request.”** Page 1 still points to the registry. |
| `article-2025-supplement-pdf` | [Archived online appendix](https://freidok.uni-freiburg.de/files/272410/pgUs02QPotqIhwBf/1-s2.0-S0927537125001344-mmc1.pdf), linked in repository metadata | 20-page instrument appendix, not microdata or analysis code. No PDF attachments in this or either main paper. |

The university file URLs publicly redirect to short-lived signed storage URLs; the ledger preserves the actual redirect destination. Replay downloads should start from the stable `/files/` links, not expired storage links. These were site-issued public download redirects, requiring no credentials.

## Version and licensing boundaries

The benchmark remains *Tax System Design, Tax Reform, and Labor Supply*, CESifo WP 11350, September 2024. Its SHA256 is `0e01148299bb2e7a4c372ed827f59e6ab3b3f4633cc65718e6c77cfae87756e9`. No explicit redistribution license was located for that PDF in the inspected working-paper materials.

The later article is *Asymmetric labor supply responses to tax rate reform: Experimental evidence*, Labour Economics 97 (2025), 102810. Its publisher PDF records receipt on September 15, 2024, revision on September 20, 2025, acceptance on September 25, 2025, and online availability on October 8, 2025. Do not substitute the repository's submission/issuance dates for those publication events. The main PDF hash is `c5052fed46b9a8023710777bd554c75fcfcbdb1e9faa8912c1dd738852e6baaf`; the appendix hash is `06490e002d17b3b916ca03346f628c6af2299d3f343e7ccd63e62c67508d5158`.

The 2025 article explicitly carries CC BY 4.0. Repository record-level licensing also says CC BY 4.0 and metadata licensing says CC0; its individual file-license fields are blank. **No human-data or analysis-code license was recovered**, and an article license must not be extended to an unavailable dataset. No raw participant material was obtained or redistributed.

Offline image comparison verifies that all 20 embedded instrument screenshots across 2024 PDF pp. 52-70 have identical decoded pixels to their counterparts in 2025 appendix pp. 2-20. This is a narrow, reproducible instrument-image concordance, not proof that runtime code, randomization, microdata, exclusions, or analysis versions are identical. See [validation.json](validation.json).

## Exact stopping condition

The paper's archive claim is contradicted by the inspected public registry state: there is no accessible data/code link there, and the data-publication answer is negative. The request-information notice is specifically under **Study Withdrawal**; it does not prove that hidden replication data exist or that signing in grants them. No access request was submitted.

The later publisher article establishes an on-request condition for that publication. It cannot establish the historical availability or exact licensing of the 2024 dataset. The official institutional archive supplies only papers/instruments. **No public human microdata or analysis code was recovered from the inspected routes.** This is not a claim that no copy exists anywhere. Retrieval should resume only with an authorized existing archive or a genuine new public link, not repeated attempts at these same endpoints.
