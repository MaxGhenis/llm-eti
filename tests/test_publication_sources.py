import csv
import hashlib
import json
import re
from pathlib import Path

import pandas as pd

import llm_eti

ROOT = Path(__file__).resolve().parents[1]


def test_package_version_matches_citation():
    citation = (ROOT / "CITATION.cff").read_text()
    assert llm_eti.__version__ == "0.2.0"
    assert "version: 0.2.0" in citation


def test_only_canonical_manuscript_and_pipeline_remain():
    assert (ROOT / "paper" / "index.qmd").exists()
    assert (ROOT / "_quarto.yml").exists()
    paper_config = (ROOT / "paper" / "_quarto.yml").read_text()
    assert "render:\n    - index.qmd" in paper_config
    assert not (ROOT / "book").exists()
    assert not (ROOT / "results").exists()
    assert not (ROOT / "llm_eti" / "paper_results.py").exists()
    assert not (ROOT / "policy_engine_simulation").exists()


def test_web_paper_has_a_skip_link_to_its_main_landmark():
    title_block = (ROOT / "paper" / "title-block.html").read_text()
    manuscript = (ROOT / "paper" / "index.qmd").read_text()
    paper_css = (ROOT / "assets" / "paper.css").read_text()
    assert 'class="skip-link" href="#paper-content"' in title_block
    assert '{#paper-content role="main"}' in manuscript
    assert ".skip-link:focus" in paper_css


def test_manuscript_uses_model_output_framing():
    manuscript = "\n".join(
        path.read_text()
        for path in [
            ROOT / "paper" / "index.qmd",
            *(ROOT / "paper" / "sections").glob("*.md"),
        ]
    )
    assert "model-implied" in manuscript.lower()
    assert "not human elasticities" in manuscript.lower()
    assert "PKNF" not in manuscript
    assert "factorial" not in manuscript.lower()
    assert "common prior" not in manuscript.lower()


def test_manuscript_describes_the_implemented_estimator():
    methods = (ROOT / "paper" / "sections" / "methods.md").read_text()
    primary_panel = (ROOT / "paper" / "generated" / "primary_panel.md").read_text()
    assert "response-level log changes" in methods
    assert "cluster" in methods.lower()
    assert "{{< include generated/primary_panel.md >}}" in methods
    assert "603 scenarios" in primary_panel
    assert "600 year–tax-unit clusters" in primary_panel
    assert "HC3" not in methods
    assert "not preregistered" in methods
    assert "use_correction=True" in methods
    assert "use_t=False" in methods
    assert "standard-normal critical" in methods
    assert "working-model regression uncertainty" in methods
    assert "archived scenarios and outputs" in methods


def test_exact_prompt_is_in_manuscript_appendix():
    appendix = (ROOT / "paper" / "sections" / "appendix.md").read_text()
    protocol = (ROOT / "protocols" / "legacy_tax_prompt.md").read_text()
    marker = "You are a taxpayer with the following profile:"
    response_contract = (
        '{"broad_income": <number or null>, "taxable_income": <number or null>}'
    )
    for text in [marker, response_contract]:
        assert text in protocol
        assert text in appendix

    expected_hashes = [
        "52754080153c4982d9a43349560a853a9fac791d8d84abcc3adb6ba3ffe4973d",
        "3d9029a7e0f0d559f5bf87eef621541588792c5a4649fe95de109277670d4011",
    ]
    suffix = (
        "Do not use null. Return your best numeric estimates even if approximate. "
        "Use whole-dollar amounts."
    )
    protocol_blocks = re.findall(r"```text\n(.*?)\n```", protocol, re.DOTALL)
    appendix_blocks = re.findall(r"```text\n(.*?)\n```", appendix, re.DOTALL)
    assert protocol_blocks == appendix_blocks
    assert len(protocol_blocks) == 2
    assert protocol_blocks[1] == protocol_blocks[0] + "\n\n" + suffix
    assert [
        hashlib.sha256(block.encode()).hexdigest() for block in protocol_blocks
    ] == expected_hashes
    for digest in expected_hashes:
        assert digest in protocol
        assert digest in appendix


def test_historical_parser_archive_is_verbatim_and_provenanced():
    archive = (ROOT / "protocols" / "legacy_income_parser.md").read_text()
    (parser_block,) = re.findall(r"````python\n(.*?)````", archive, re.DOTALL)
    assert len(parser_block.encode()) == 4_545
    assert hashlib.sha256(parser_block.encode()).hexdigest() == (
        "7c274bd9d6796aef6c60473f8800a1a8ed9ebc1345db7c58e3742611ee02f399"
    )
    assert "b23f2cb882d33f79d706afbdcca836b3905361f8" in archive
    assert "llm_eti/edsl_client.py" in archive

    manifest = json.loads((ROOT / "data" / "run_manifest.json").read_text())
    assert manifest["historical_parser"]["excerpt_sha256"] == (
        "7c274bd9d6796aef6c60473f8800a1a8ed9ebc1345db7c58e3742611ee02f399"
    )


def test_data_dictionary_documents_every_frozen_csv_column():
    readme = (ROOT / "data" / "README.md").read_text()
    scenario_path = ROOT / "data" / "scenarios.csv"
    response_paths = sorted((ROOT / "data" / "responses").glob("*.csv"))

    with scenario_path.open(newline="") as scenario_file:
        scenario_columns = next(csv.reader(scenario_file))
    with response_paths[0].open(newline="") as response_file:
        response_columns = next(csv.reader(response_file))

    for column in [*scenario_columns, *response_columns]:
        assert f"`{column}`" in readme
    for path in response_paths:
        with path.open(newline="") as response_file:
            assert next(csv.reader(response_file)) == response_columns
        filing_status = pd.read_csv(path, usecols=["filing_status"])["filing_status"]
        assert filing_status.isna().all()

    for statement in [
        "Timezone-naive collection string",
        "Blank in all 8,095 archived response rows",
        "archived raw answer",
        "parsed numeric fields",
        "Deprecated legacy derivative",
    ]:
        assert statement in readme


def test_declarations_state_no_human_participation():
    declarations = (ROOT / "paper" / "sections" / "declarations.md").read_text()
    normalized = " ".join(declarations.split())
    assert "Human-subjects statement" in declarations
    assert "No human participants were recruited" in declarations
    assert (
        "Human-subjects review and participant consent were therefore not applicable"
        in normalized
    )


def test_argyle_reference_uses_corrected_doi():
    references = (ROOT / "paper" / "references.bib").read_text()
    assert "10.1017/pan.2023.2" in references
    assert "10.1017/pan.2022.37" not in references


def test_publication_is_offline_and_has_no_model_secret_workflow():
    workflows = "\n".join(
        path.read_text() for path in (ROOT / ".github" / "workflows").glob("*.yml")
    )
    assert "EXPECTED_PARROT_API_KEY" not in workflows
    assert "placeholder" not in workflows.lower()
