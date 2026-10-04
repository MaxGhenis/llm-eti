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
    batch_size: int = 100
    max_in_flight: int = 1


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
        scenarios = []
        for index, row in scenarios_df.iterrows():
            scenario = row.to_dict()
            scenario.update(
                {
                    "work_id": f"tax-{index}",
                    "mtr_last_pct": int(float(row["mtr"]) * 100),
                    "mtr_this_pct": int(float(row["mtr_prime"]) * 100),
                }
            )
            scenarios.append(scenario)

        raw_results = self.client.run_batched_surveys(
            scenarios,
            survey_type="tax",
            responses_per_scenario=self.params.responses_per_household,
            batch_size=self.params.batch_size,
            max_in_flight=self.params.max_in_flight,
            fresh=True,
        )
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        all_results = [
            {
                "timestamp": timestamp,
                "tax_unit_id": result.get("tax_unit_id"),
                "filing_status": result.get("filing_status"),
                "broad_income": result["broad_income"],
                "taxable_income": result["taxable_income"],
                "mtr": result["mtr"],
                "mtr_prime": result["mtr_prime"],
                "response_number": result["response_number"],
                "taxable_income_this": result.get("taxable_income_this"),
                "broad_income_this": result.get("broad_income_this"),
                "implied_eti_taxable": result.get("implied_eti_taxable"),
                "implied_eti_broad": result.get("implied_eti_broad"),
                "model": result.get("model", self.client.model),
                "income_response_raw": result.get("income_response_raw"),
            }
            for result in raw_results
        ]
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
        execution: str = "serial",
    ) -> Dict:
        """Build the full offline design without issuing a survey request.

        ``execution`` ("serial" or "batched") selects the prompt builder and
        executor whose source is bound into the manifest, so a ledger written
        by one path can never be resumed by the other.
        """
        return build_manifest(
            self.client,
            self.config,
            treatments,
            int(self.config["rounds"]) if rounds is None else rounds,
            subjects_per_treatment,
            low_rate,
            high_rate,
            seed,
            execution=execution,
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
        batch_size: Optional[int] = None,
        max_in_flight: int = 1,
    ) -> pd.DataFrame:
        """Run or resume only a manifest-compatible experiment.

        The checkpoint is an append-only attempt ledger. Only successful rows
        count as completed; zero is a valid income. This method returns the latest
        row per planned scenario, while preserving failures/retries in the ledger.
        Legacy manifest-free CSVs are never reused or overwritten automatically.

        ``batch_size=None`` issues one request per scenario (serial path). An
        integer submits pending scenarios as concurrent remote EDSL jobs of that
        size (``max_in_flight`` at a time); every returned row is written to the
        same ledger as each chunk completes.
        """
        execution = "serial" if batch_size is None else "batched"
        manifest = self.experiment_manifest(
            treatments,
            rounds,
            subjects_per_treatment,
            low_rate,
            high_rate,
            seed,
            execution=execution,
        )
        path = None if checkpoint_path is None else Path(checkpoint_path)
        with checkpoint_lock(path):
            records = prepare_checkpoint(path, manifest)
            latest = {row["scenario_id"]: row for row in records}
            if batch_size is not None:
                self._run_batched(manifest, path, latest, batch_size, max_in_flight)
                return pd.DataFrame(list(latest.values()), columns=RECORD_FIELDS)
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

    def _run_batched(
        self,
        manifest: Dict,
        path: Optional[Path],
        latest: Dict,
        batch_size: int,
        max_in_flight: int,
    ) -> None:
        """Submit pending scenarios in chunks; append each result to the ledger."""
        by_id = {
            scenario["scenario_id"]: scenario for scenario in manifest["scenarios"]
        }
        requests = []
        for scenario in manifest["scenarios"]:
            previous = latest.get(scenario["scenario_id"])
            if previous is not None and previous["status"] == "success":
                continue
            if scenario["tax_schedule"] == "progressive":
                tax_text = (
                    f"In this round, the tax rate is {scenario['low_rate']}% for incomes equal to or below 400 cents. "
                    f"The tax rate is {scenario['high_rate']}% on the entire income if income exceeds 400 cents."
                )
            else:
                rate = (
                    scenario["low_rate"]
                    if scenario["tax_schedule"] == "flat25"
                    else scenario["high_rate"]
                )
                tax_text = f"In this round, the tax rate is {rate}% for all incomes."
            requests.append(
                {
                    **scenario,
                    "work_id": scenario["scenario_id"],
                    "round_num": scenario["round"],
                    "max_income": int(
                        scenario["labor_endowment"] * scenario["wage_per_unit"]
                    ),
                    "tax_text": tax_text,
                }
            )
        if not requests:
            return

        def record(scenario_id: str, result: Dict) -> None:
            row = self._checkpoint_row(
                manifest, by_id[scenario_id], latest.get(scenario_id), result
            )
            append_record(path, row)
            latest[scenario_id] = row

        returned: set = set()

        def checkpoint_chunk(chunk_results: List[Dict]) -> None:
            # Runs on the caller's thread, which holds the checkpoint lock.
            for result in chunk_results:
                scenario_id = str(result.get("work_id"))
                if scenario_id not in by_id or scenario_id in returned:
                    continue
                returned.add(scenario_id)
                record(scenario_id, result)

        self.client.run_batched_surveys(
            requests,
            survey_type="lab",
            agent_instruction=manifest["spec"]["instructions"],
            batch_size=batch_size,
            max_in_flight=max_in_flight,
            fresh=True,
            on_chunk_complete=checkpoint_chunk,
        )
        # A completed job that silently omitted a scenario is a failed attempt.
        for request in requests:
            if request["work_id"] not in returned:
                record(
                    request["work_id"],
                    {"response_raw": "no result returned by batched EDSL job"},
                )

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
