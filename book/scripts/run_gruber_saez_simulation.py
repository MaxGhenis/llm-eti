#!/usr/bin/env python3
"""
Run Gruber & Saez (2002) observational study replication using EDSL.
"""

import argparse
import os
import sys
from pathlib import Path

from llm_eti.edsl_client import EDSLClient
from llm_eti.simulation_engine import SimulationParams, TaxSimulation

# Add parent directory to path to import from main project
sys.path.append(str(Path(__file__).parent.parent.parent))

# set constants
CSV_PATH = (
    Path(__file__).parent.parent.parent
    / "policy_engine_simulation"
    / "policyengine_sample_incomes.csv"
)
ALL_MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "deepseek-ai/DeepSeek-V3",
    "claude-haiku-4-5-20251001",
    "google/gemma-4-26B-A4B-it",
]


def main():
    parser = argparse.ArgumentParser(
        description="Run Gruber & Saez simulation with EDSL"
    )
    parser.add_argument(
        "--test", action="store_true", help="Run in test mode with fewer scenarios"
    )
    parser.add_argument("--model", default="gpt-4o-mini", help="LLM model to use")
    parser.add_argument(
        "--production", action="store_true", help="Run full production simulation"
    )
    parser.add_argument(
        "--responses", type=int, default=1, help="LLM responses per household"
    )
    parser.add_argument(
        "--cache-analysis", action="store_true", help="Analyze cache usage after run"
    )
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--max-in-flight", type=int, default=1)
    args = parser.parse_args()

    # Check for API key
    api_key = os.getenv("EXPECTED_PARROT_API_KEY")
    if not api_key:
        print("Error: EXPECTED_PARROT_API_KEY environment variable not set")
        sys.exit(1)

    if not CSV_PATH.exists():
        print(f"Error: input CSV not found at {CSV_PATH}")
        sys.exit(1)

    print(f"Running Gruber & Saez simulation with {args.model}...")
    print(f"Input CSV: {CSV_PATH}")

    # Initialize client and parameters
    if args.model == "all":
        model_list = ALL_MODELS
        print(f"Running with all models: {model_list}")
    else:
        model_list = [args.model]

    for model in model_list:
        client = EDSLClient(api_key=api_key, model=model, use_cache=True)
        params = SimulationParams(
            responses_per_household=args.responses,
            test_mode=args.test,
            batch_size=args.batch_size,
            max_in_flight=args.max_in_flight,
        )

        print("Running simulation with:")
        print(f"  - Model: {model}")
        print(f"  - Responses per household: {args.responses}")
        print(f"  - Cache enabled: {client.use_cache}")
        print("  - Fresh responses: True")
        print(f"  - Batch size: {args.batch_size}")
        print(f"  - Max in-flight jobs: {args.max_in_flight}")

        # Run simulation
        simulation = TaxSimulation(client, params)
        results_df = simulation.run_bulk_simulation(CSV_PATH)
        if results_df.empty:
            raise RuntimeError(
                "Simulation produced no result rows; refusing to write empty CSV "
                f"for model {model}"
            )

        # Save results
        output_dir = Path(__file__).parent.parent / "data"
        output_dir.mkdir(exist_ok=True)

        # if model string has a slash (e.g. "deepseek-ai/DeepSeek-V3"), replace with underscore for filename
        safe_model_name = model.replace("/", "_")
        filename = f"gruber_saez_results_{safe_model_name}"
        if args.test:
            filename += "_test"

        results_df.to_csv(output_dir / f"{filename}.csv", index=False)
        print(f"Results saved to {output_dir / f'{filename}.csv'}")
        print(f"Total responses: {len(results_df)}")
        print(f"Cache usage enabled: {client.use_cache}")

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
