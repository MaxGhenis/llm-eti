#!/usr/bin/env python3
"""
Run PKNF (2024) lab experiment replication using EDSL.
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path to import from main project
sys.path.append(str(Path(__file__).parent.parent.parent))

from llm_eti.edsl_client import EDSLClient
from llm_eti.lab_checkpoint import rate_label
from llm_eti.simulation_engine import LabExperimentSimulation

ALL_MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "deepseek-ai/DeepSeek-V3",
    "claude-haiku-4-5-20251001",
    "google/gemma-4-26B-A4B-it",
]


def main():
    parser = argparse.ArgumentParser(description="Run PKNF simulation with EDSL")
    parser.add_argument(
        "--test", action="store_true", help="Run in test mode with fewer subjects"
    )
    parser.add_argument("--model", default="gpt-4o-mini", help="LLM model to use")
    parser.add_argument(
        "--production", action="store_true", help="Run full production simulation"
    )
    parser.add_argument(
        "--cache-analysis", action="store_true", help="Analyze cache usage after run"
    )
    parser.add_argument(
        "--low-rate",
        type=float,
        default=25.0,
        help="Low marginal tax rate as a percentage (default: 25)",
    )
    parser.add_argument(
        "--high-rate",
        type=float,
        default=50.0,
        help="High marginal tax rate as a percentage (default: 50)",
    )
    parser.add_argument("--seed", type=int, default=0, help="Persisted experiment seed")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent.parent / "data",
        help="Results directory; use a new directory for incompatible experiments",
    )
    args = parser.parse_args()

    # Check for API key
    api_key = os.getenv("EXPECTED_PARROT_API_KEY")
    if not api_key:
        print("Error: EXPECTED_PARROT_API_KEY environment variable not set")
        sys.exit(1)

    # Set parameters based on mode
    if args.test:
        num_subjects = 2
        rounds = 2
    elif args.production:
        num_subjects = 100
        rounds = 16
    else:
        # Default mode - medium size
        num_subjects = 50
        rounds = 8
    # All treatments from PKNF
    treatments = [
        "Prog,Prog",
        "Prog,Flat25",
        "Prog,Flat50",
        "Flat25,Prog",
        "Flat50,Prog",
    ]

    # Initialize client and experiment
    # Initialize client and parameters
    if args.model == "all":
        model_list = ALL_MODELS
        print(f"Running with all models: {model_list}")
    else:
        model_list = [args.model]

    for model in model_list:
        client = EDSLClient(api_key=api_key, model=model, use_cache=True)
        experiment = LabExperimentSimulation(client)

        print("Running PKNF simulation with:")
        print(f"  - Model: {model}")
        print(f"  - Subjects per treatment: {num_subjects}")
        print(f"  - Total treatments: {len(treatments)}")
        print(f"  - Total rounds: {rounds}")
        print(f"  - Cache enabled: {client.use_cache}")
        print(f"  - Low rate: {args.low_rate}%")
        print(f"  - High rate: {args.high_rate}%")

        # Keep immutable attempts separate from the derived latest-row result CSV.
        output_dir = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # if model string has a slash (e.g. "deepseek-ai/DeepSeek-V3"), replace with underscore for filename
        safe_model_name = model.replace("/", "_")
        filename = (
            f"pknf_results_{safe_model_name}_{rate_label(args.low_rate)}pct_{rate_label(args.high_rate)}pct"
            f"_{rounds}rounds_seed{args.seed}"
        )
        if args.test:
            filename += "_test"

        output_path = output_dir / f"{filename}.csv"

        checkpoint_path = output_dir / "checkpoints" / f"{filename}.csv"

        # Manifest compatibility is checked before any survey request. The
        # append-only attempts file is never replaced with consolidated results.
        results_df = experiment.run_experiment(
            treatments=treatments,
            rounds=rounds,
            subjects_per_treatment=num_subjects,
            low_rate=args.low_rate,
            high_rate=args.high_rate,
            checkpoint_path=checkpoint_path,
            seed=args.seed,
        )

        # Derived snapshot only; failed attempts remain in the separate checkpoint.
        results_df.to_csv(output_path, index=False)
        print(f"Results saved to {output_path}")
        print(f"Total responses: {len(results_df)}")

    # Analyze cache if requested
    if args.cache_analysis:
        from llm_eti.cache_utils import CacheExplorer

        print("\nCache Analysis:")
        explorer = CacheExplorer()
        stats = explorer.get_cache_stats()

        if "error" not in stats:
            print(f"  - Total cache entries: {stats['total_entries']}")
            print(f"  - Models in cache: {list(stats['models'].keys())}")

            savings = explorer.estimate_cost_savings()
            if "error" not in savings:
                print(
                    f"  - Estimated cost saved: ${savings['estimated_cost_saved']:.4f}"
                )


if __name__ == "__main__":
    main()
