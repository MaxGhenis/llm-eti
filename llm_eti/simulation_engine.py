"""Simulation engine using EDSL for LLM surveys."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from tqdm import tqdm

from .edsl_client import EDSLClient


@dataclass
class SimulationParams:
    responses_per_household: int
    test_mode: bool = False


class TaxSimulation:
    """Tax simulation using EDSL surveys.  Inputs from PolicyEngine CSV
    of broad incomes and tax rates, outputs DataFrame with simulated
    taxable incomes and implied ETI."""

    def __init__(self, edsl_client: EDSLClient, params: SimulationParams):
        self.client = edsl_client
        self.params = params

    def load_scenarios(self, csv_path: Path) -> pd.DataFrame:
        """Load and validate scenarios from PolicyEngine CSV.

        Filters out rows where broad_income or taxable_income is zero,
        as these produce invalid QuestionNumerical ranges.

        Args:
            csv_path: Path to policyengine_sample_incomes.csv

        Returns:
            Filtered DataFrame of valid scenarios
        """
        df = pd.read_csv(csv_path)

        n_before = len(df)
        df = df[(df["broad_income"] > 0) & (df["taxable_income"] > 0)]
        n_after = len(df)

        if n_before != n_after:
            print(
                f"Filtered {n_before - n_after} zero-income rows ({n_after} remaining)"
            )

        if self.params.test_mode:
            df = df.sample(n=1, random_state=42)
            print("Test mode: sampled 1 row")

        return df.reset_index(drop=True)

    def run_single_simulation(self, row: Dict) -> List[Dict]:
        """Run simulation for a single household scenario.

        Args:
            row: Dict with broad_income, taxable_income, mtr, mtr_prime

        Returns:
            List of result dicts (one per LLM response)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Create scenario for EDSL
        scenario = {
            "broad_income": row["broad_income"],
            "taxable_income": row["taxable_income"],
            "mtr_last": row["mtr"],
            "mtr_this": row["mtr_prime"],
        }

        # Run survey with EDSL
        results = self.client.run_batch_surveys(
            [scenario],
            n=self.params.responses_per_household,
            survey_type="tax",
        )

        # Format results to match existing structure
        formatted_results = []
        for i, result in enumerate(results):
            formatted_results.append(
                {
                    "timestamp": timestamp,
                    "tax_unit_id": row.get("tax_unit_id"),
                    "filing_status": row.get("filing_status"),
                    "broad_income": row["broad_income"],
                    "taxable_income": row["taxable_income"],
                    "mtr": row["mtr"],
                    "mtr_prime": row["mtr_prime"],
                    "response_number": i + 1,
                    "taxable_income_this": result.get("taxable_income_this"),
                    "broad_income_this": result.get("broad_income_this"),
                    "implied_eti_taxable": result.get("implied_eti_taxable"),
                    "implied_eti_broad": result.get("implied_eti_broad"),
                    "model": result.get("model", self.client.model),
                    "income_response_raw": result.get("income_response_raw"),
                }
            )

        if not formatted_results:
            print(
                "Warning: skipping household with no valid tax responses "
                f"for income {row['broad_income']} and rate {row['mtr_prime']}"
            )

        return formatted_results

    def run_bulk_simulation(self, csv_path: Path) -> pd.DataFrame:
        """Run simulations for all households in the CSV.

        Args:
            csv_path: Path to policyengine_sample_incomes.csv

        Returns:
            DataFrame of all results
        """
        scenarios_df = self.load_scenarios(csv_path)
        all_results = []

        with tqdm(total=len(scenarios_df), desc="Running simulations") as pbar:
            for _, row in scenarios_df.iterrows():
                results = self.run_single_simulation(row.to_dict())
                all_results.extend(results)
                pbar.update(1)

        return pd.DataFrame(all_results)


# Lab experiment simulation for PKNF replication
class LabExperimentSimulation:
    """PKNF lab experiment simulation using EDSL.

    This class replicates the experimental framework of Pfeil, Kasper, Necker & Feld (2024),
    which measures labor supply responses to changes in tax schedules. The experiment consists of:

    - 16 rounds of decision-making
    - Tax reform after round 8 (either adding or removing a notch)
    - Randomized labor endowments (14-30 units per round)
    - Wage of 20 ECU per unit of labor

    References:
        Pfeil, K., Kasper, M., Necker, S., & Feld, L. P. (2024).
        Tax System Design, Tax Reform, and Labor Supply. CESifo Working Paper No. 11350.
    """

    def __init__(self, edsl_client: EDSLClient):
        self.client = edsl_client
        # Import here to avoid circular imports
        from .config import Config

        self.config = Config.PKNF_CONFIG

    def run_experiment(
        self,
        treatments: List[str],
        rounds: Optional[int] = None,
        subjects_per_treatment: int = 100,
        low_rate: float = 25.0,
        high_rate: float = 50.0,
        checkpoint_path: Optional[Path] = None,
    ) -> pd.DataFrame:
        """Run the full lab experiment simulation.

        Args:
            treatments: List of treatment labels to run (e.g., ["Prog,Prog", "Prog,Flat25"])
            rounds: Number of rounds (default: 16 from config)
            subjects_per_treatment: Number of subjects per treatment group
            low_rate: Low marginal tax rate as a percentage (default: 25)
            high_rate: High marginal tax rate as a percentage (default: 50)

        Returns:
            DataFrame with experiment results
        """
        from .pknf_types import Treatment

        if rounds is None:
            rounds = int(self.config["rounds"])

        instructions = self.client.create_instructions_text(
            rounds=rounds, wage_per_unit=self.config["wage_per_unit"]
        )

        # Load checkpoint if it exists
        all_results: List[Dict] = []
        completed_set: set = set()
        if checkpoint_path is not None and Path(checkpoint_path).exists():
            try:
                existing_df = pd.read_csv(checkpoint_path)
                if not existing_df.empty:
                    all_results = existing_df.to_dict("records")
                    for row in all_results:
                        completed_set.add(
                            (str(row["treatment"]), int(row["subject_id"]), int(row["round"]))
                        )
                    print(
                        f"Resuming from checkpoint: {len(all_results)} results loaded "
                        f"({len(completed_set)} (treatment, subject, round) tuples completed)"
                    )
            except Exception as e:
                print(f"Warning: Could not load checkpoint {checkpoint_path}: {e}")
                all_results = []
                completed_set = set()

        total_sims = len(treatments) * subjects_per_treatment * rounds
        with tqdm(total=total_sims, desc="Lab experiment") as pbar:
            for treatment_label in treatments:
                try:
                    treatment = Treatment.from_label(treatment_label)
                except ValueError:
                    print(f"Warning: Unknown treatment '{treatment_label}', skipping")
                    pbar.update(rounds * subjects_per_treatment)
                    continue

                # Compute output label once per treatment (doesn't vary by round)
                output_label = treatment.label.replace(
                    "Flat25", f"Flat{int(low_rate)}"
                ).replace("Flat50", f"Flat{int(high_rate)}")

                for subject_id in range(subjects_per_treatment):
                    # Deterministic seed per (treatment, subject) for reproducible endowments
                    seed = abs(hash(treatment_label)) % (2**32) + subject_id
                    rng = np.random.default_rng(seed)
                    labor_endowments = rng.integers(
                        int(self.config["labor_endowment_min"]),
                        int(self.config["labor_endowment_max"]) + 1,
                        size=rounds,
                    )

                    for round_idx in range(rounds):
                        round_num = round_idx + 1  # 1-based round number

                        # Skip rounds already saved to checkpoint
                        if (output_label, subject_id, round_num) in completed_set:
                            pbar.update(1)
                            continue

                        completed = pbar.n
                        remaining = total_sims - completed
                        pbar.set_description(
                            f"Treatment {treatment_label} | "
                            f"Subject {subject_id + 1}/{subjects_per_treatment} | "
                            f"Round {round_num}/{rounds} | "
                            f"{remaining} remaining"
                        )

                        # Get tax schedule for this round
                        schedule = treatment.get_schedule_for_round(round_num, rounds)

                        scenario = {
                            "round_num": round_num,
                            "tax_schedule": schedule.value,
                            "labor_endowment": int(labor_endowments[round_idx]),
                            "wage_per_unit": self.config["wage_per_unit"],
                            "rounds": rounds,
                            "low_rate": low_rate,
                            "high_rate": high_rate,
                        }

                        # Run survey
                        results = self.client.run_batch_surveys(
                            [scenario],
                            n=1,
                            survey_type="lab",
                            agent_instruction=instructions,
                        )

                        if results:
                            result = results[0]
                            income_choice = result.get("income")

                            row_data = {
                                "treatment": output_label,
                                "subject_id": subject_id,
                                "round": round_num,
                                "tax_schedule": schedule.value,
                                "labor_endowment": int(labor_endowments[round_idx]),
                                "labor_supply": (
                                    income_choice / self.config["wage_per_unit"]
                                    if income_choice is not None
                                    else None
                                ),
                                "income": income_choice,
                                "post_reform": round_num > rounds // 2,
                                "model": result.get("model", self.client.model),
                                "response_error": result.get("parse_failed", False),
                            }
                            all_results.append(row_data)
                            completed_set.add((output_label, subject_id, round_num))

                            # Append to checkpoint immediately so progress survives crashes
                            if checkpoint_path is not None:
                                checkpoint_df = pd.DataFrame([row_data])
                                write_header = not Path(checkpoint_path).exists()
                                checkpoint_df.to_csv(
                                    checkpoint_path,
                                    mode="a",
                                    header=write_header,
                                    index=False,
                                )

                        pbar.update(1)

        return pd.DataFrame(all_results)
