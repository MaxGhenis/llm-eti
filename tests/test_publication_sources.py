from pathlib import Path

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


def test_publication_is_offline_and_has_no_model_secret_workflow():
    workflows = "\n".join(
        path.read_text() for path in (ROOT / ".github" / "workflows").glob("*.yml")
    )
    assert "EXPECTED_PARROT_API_KEY" not in workflows
    assert "placeholder" not in workflows.lower()
