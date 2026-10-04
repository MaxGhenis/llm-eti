"""Simulation engine using EDSL for LLM surveys."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from tqdm import tqdm

from .edsl_client import EDSLClient
from .lab_checkpoint import (
    RECORD_FIELDS,
    append_record,
    build_manifest,
    checkpoint_lock,
    prepare_checkpoint,
    valid_income,
)


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

    def experiment_manifest(
        self,
        treatments: List[str],
        rounds: Optional[int] = None,
        subjects_per_treatment: int = 100,
        low_rate: float = 25.0,
        high_rate: float = 50.0,
        seed: int = 0,
    ) -> Dict:
        """Build the full offline design without issuing a survey request."""
        return build_manifest(
            self.client,
            self.config,
            treatments,
            int(self.config["rounds"]) if rounds is None else rounds,
            subjects_per_treatment,
            low_rate,
            high_rate,
            seed,
        )

    def run_experiment(
        self,
        treatments: List[str],
        rounds: Optional[int] = None,
        subjects_per_treatment: int = 100,
        low_rate: float = 25.0,
        high_rate: float = 50.0,
        checkpoint_path: Optional[Path] = None,
        seed: int = 0,
    ) -> pd.DataFrame:
        """Run or resume only a manifest-compatible experiment.

        The checkpoint is an append-only attempt ledger. Only successful rows
        count as completed; zero is a valid income. This method returns the latest
        row per planned scenario, while preserving failures/retries in the ledger.
        Legacy manifest-free CSVs are never reused or overwritten automatically.
        """
        manifest = self.experiment_manifest(
            treatments, rounds, subjects_per_treatment, low_rate, high_rate, seed
        )
        path = None if checkpoint_path is None else Path(checkpoint_path)
        with checkpoint_lock(path):
            records = prepare_checkpoint(path, manifest)
            latest = {row["scenario_id"]: row for row in records}
            with tqdm(total=len(manifest["scenarios"]), desc="Lab experiment") as pbar:
                for scenario in manifest["scenarios"]:
                    scenario_id = scenario["scenario_id"]
                    previous = latest.get(scenario_id)
                    if previous is not None and previous["status"] == "success":
                        pbar.update(1)
                        continue
                    request = {
                        "round_num": scenario["round"],
                        **{
                            key: scenario[key]
                            for key in (
                                "tax_schedule",
                                "labor_endowment",
                                "wage_per_unit",
                                "rounds",
                                "low_rate",
                                "high_rate",
                            )
                        },
                    }
                    try:
                        results = self.client.run_batch_surveys(
                            [request],
                            n=1,
                            survey_type="lab",
                            agent_instruction=manifest["spec"]["instructions"],
                        )
                    except Exception as error:
                        row = self._checkpoint_row(
                            manifest, scenario, previous, {"response_raw": repr(error)}
                        )
                        append_record(path, row)
                        raise
                    result = (
                        results[0]
                        if results and len(results) == 1
                        else {"response_raw": repr(results)}
                    )
                    row = self._checkpoint_row(manifest, scenario, previous, result)
                    append_record(path, row)
                    latest[scenario_id] = row
                    pbar.update(1)
            return pd.DataFrame(list(latest.values()), columns=RECORD_FIELDS)

    def _checkpoint_row(self, manifest, scenario, previous, result):
        income = result.get("income")
        success = (
            valid_income(income, scenario)
            and not result.get("parse_failed", False)
            and result.get("model", self.client.model) == self.client.model
        )
        if not success:
            income = None
        return {
            "experiment_id": manifest["experiment_id"],
            **scenario,
            "model": self.client.model,
            "attempt": 1 if previous is None else previous["attempt"] + 1,
            "status": "success" if success else "retryable_failure",
            "income": income,
            "labor_supply": (
                None if income is None else income / scenario["wage_per_unit"]
            ),
            "response_error": not success,
            "response_raw": str(result.get("response_raw", result)),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
