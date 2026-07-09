import hashlib
import json
from pathlib import Path

from scripts.generate_artifacts import main

ROOT = Path(__file__).resolve().parents[1]


def test_artifact_generator_is_complete_and_has_no_fallbacks():
    main()

    generated = ROOT / "paper" / "generated"
    figures = ROOT / "paper" / "figures"
    required_text = [
        "abstract.md",
        "boundary_outputs.md",
        "completion.md",
        "design_diagnostics.md",
        "hero_metrics.html",
        "key_findings.md",
        "main_narrative.md",
        "model_provenance.md",
        "partial_run_note.md",
        "primary_panel.md",
        "recovery_diagnostics.md",
        "response_diagnostics.md",
        "response_friction.md",
        "sample_characteristics.md",
        "sample_flow.html",
        "same_rate_check.md",
        "scenario_sample.md",
        "slope_results.md",
        "sensitivity.md",
        "sensitivity_narrative.md",
        "treatment_diagnostics.md",
        "year_coverage.md",
    ]
    required_figures = [
        "completion_by_model.png",
        "completion_by_model.svg",
        "completion_by_model.pdf",
        "model_response_slopes.png",
        "model_response_slopes.svg",
        "model_response_slopes.pdf",
        "response_patterns.png",
        "response_patterns.svg",
        "response_patterns.pdf",
    ]
    forbidden = ["Placeholder for:", "No ETI data available", "Run full simulations"]

    for name in required_text:
        text = (generated / name).read_text()
        assert text.strip()
        assert not any(phrase in text for phrase in forbidden)
    for name in required_figures:
        assert (figures / name).stat().st_size > 10_000

    summary = json.loads((generated / "analysis_summary.json").read_text())
    assert summary["primary_analysis_scenario_count"] == 603
    assert summary["archived_response_row_count"] == 8_095
    assert summary["deduplicated_analysis_row_count"] == 8_087


def test_generator_contains_no_legacy_discovery_or_placeholder_path():
    source = (ROOT / "scripts" / "generate_artifacts.py").read_text()
    assert 'glob("*/")' not in source
    assert "placeholder" not in source.lower()
    assert "simulation_4o" not in source


def test_artifact_generator_is_byte_deterministic():
    paths = [
        *(ROOT / "paper" / "figures").glob("*"),
        ROOT / "assets" / "social-card.png",
    ]
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}

    main()

    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    assert after == before
