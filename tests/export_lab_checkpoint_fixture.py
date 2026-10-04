"""Export synthetic checkpoint evidence: python -m tests.export_lab_checkpoint_fixture DIR."""

import importlib.metadata
import json
import platform
import sys
from pathlib import Path

from llm_eti.simulation_engine import LabExperimentSimulation
from tests.offline_lab_client import OfflineLabClient


def main():
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=False)
    client = OfflineLabClient()
    client.fail_rounds = {3}
    experiment = LabExperimentSimulation(client)
    design = dict(
        treatments=["Prog,Flat25", "Flat25,Prog"],
        rounds=16,
        subjects_per_treatment=2,
        seed=314,
    )
    first = experiment.run_experiment(**design, checkpoint_path=output / "attempts.csv")
    initial_calls = len(client.calls)
    client.fail_rounds.clear()
    final = experiment.run_experiment(**design, checkpoint_path=output / "attempts.csv")
    manifest = experiment.experiment_manifest(**design)
    assert len(final) == 64 and final["status"].eq("success").all()
    assert len(client.calls) - initial_calls == 4
    assert final["income"].eq(0).sum() == 4
    final.to_csv(output / "latest-results.csv", index=False)
    (output / "design-readable.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    report = {
        "synthetic_test_fixture_not_research_results": True,
        "scenario_count": len(final),
        "initial_fake_requests": initial_calls,
        "retry_fake_requests": len(client.calls) - initial_calls,
        "initial_failures": int(first["status"].eq("retryable_failure").sum()),
        "final_successes": int(final["status"].eq("success").sum()),
        "zero_income_successes": int(final["income"].eq(0).sum()),
        "python": platform.python_version(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("numpy", "pandas", "pytest", "edsl")
        },
        "experiment_id": manifest["experiment_id"],
    }
    (output / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "README.md").write_text(
        "# Synthetic offline checkpoint fixture\n\n"
        "These are fake-client test responses, not model observations or research findings.\n"
        "64 planned scenarios; four intentional parse failures retained and retried once.\n"
        "The latest snapshot has 64 successes, including four zeros. No model API was called.\n"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
