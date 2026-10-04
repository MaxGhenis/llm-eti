"""EDSL client for running LLM surveys."""

import ast
import logging
import os
import re
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Any, Callable, Dict, Iterable, List, Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

try:
    from edsl import (
        Agent,
        Jobs,
        Model,
        Question,
        QuestionFreeText,
        QuestionNumerical,
        Scenario,
        Survey,
    )
except ImportError:
    # For testing without EDSL installed
    Question = Survey = Agent = Model = Jobs = Scenario = None
    QuestionFreeText = None
    QuestionNumerical = None


class EDSLClient:
    """Client for conducting surveys using EDSL."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        use_cache: bool = True,
    ):
        """Initialize EDSL client.

        Args:
            api_key: Expected Parrot API key. If None, loads from environment.
            model: Model to use for surveys (default: gpt-4o-mini for cost efficiency)
            use_cache: Whether to use EDSL's universal cache (default: True)
        """
        load_dotenv()

        self.api_key = api_key or os.getenv("EXPECTED_PARROT_API_KEY")
        if not self.api_key:
            raise ValueError(
                "EXPECTED_PARROT_API_KEY not found in environment or arguments"
            )

        self.model = model
        self.use_cache = use_cache

        # Set API key for EDSL
        if self.api_key:
            os.environ["EXPECTED_PARROT_API_KEY"] = self.api_key

    def build_prompt(
        self,
        broad_income: float,
        taxable_income: float,
        mtr_last: float,
        mtr_this: float,
    ) -> str:
        mtr_last_pct = int(mtr_last * 100)
        mtr_this_pct = int(mtr_this * 100)

        prompt = f"""You are a taxpayer with the following profile:
- Last year, your broad income was ${broad_income:,.0f}
- Last year, your taxable income was ${taxable_income:,.0f}
- Last year, your marginal tax rate was {mtr_last_pct}%

Due to a change in tax law, your marginal tax rate this year will be {mtr_this_pct}%.
Your broad income before any adjustments or changes in behavior would be
approximately the same as last year.

Given this change in tax rates, you may adjust your behavior -- for example,
how much you work, your charitable contributions, retirement savings, or the
timing of income realizations like capital gains. What would your broad
income be this year? And what would your taxable income be?

Respond with exactly one JSON object and nothing else:
{{"broad_income": <number or null>, "taxable_income": <number or null>}}"""

        model_name = self.model.lower()
        if "deepseek" in model_name or "claude" in model_name or "gpt-4o" in model_name:
            prompt += (
                "\n\nDo not use null. Return your best numeric estimates even if "
                "approximate. Use whole-dollar amounts."
            )

        return prompt

    def create_tax_survey(
        self,
        broad_income: float,
        taxable_income: float,
        mtr_last: float,
        mtr_this: float,
    ) -> "Survey":
        """Create a tax survey for Gruber & Saez replication.

        Args:
            broad_income: Broad income last year
            taxable_income: Taxable income last year
            mtr_last: Marginal tax rate last year (as decimal)
            mtr_this: Marginal tax rate this year (as decimal)

        Returns:
            EDSL Survey object
        """
        prompt = self.build_prompt(broad_income, taxable_income, mtr_last, mtr_this)

        # Use free text so we can parse the model response ourselves and keep
        # the numeric contract in local code instead of relying on QuestionDict.
        q = QuestionFreeText(
            question_name="income_responses",
            question_text=prompt,
        )

        return Survey(questions=[q])

    def create_tax_survey_template(self) -> "Survey":
        """Create one scenario-backed tax survey for a large EDSL Job."""
        prompt = """You are a taxpayer with the following profile:
- Last year, your broad income was ${{ broad_income }}
- Last year, your taxable income was ${{ taxable_income }}
- Last year, your marginal tax rate was {{ mtr_last_pct }}%

Due to a change in tax law, your marginal tax rate this year will be {{ mtr_this_pct }}%.
Your broad income before any adjustments or changes in behavior would be approximately the same as last year.

Given this change in tax rates, you may adjust your behavior -- for example, how much you work,
your charitable contributions, retirement savings, or the timing of income realizations like
capital gains. What would your broad income be this year? And what would your taxable income be?

Respond with exactly one JSON object and nothing else:
{% raw %}{"broad_income": <number or null>, "taxable_income": <number or null>}{% endraw %}
"""
        if any(name in self.model.lower() for name in ("deepseek", "claude", "gpt-4o")):
            prompt += "\nDo not use null. Return your best numeric estimates even if approximate. Use whole-dollar amounts."
        return Survey(
            questions=[
                QuestionFreeText(question_name="income_responses", question_text=prompt)
            ]
        )

    def create_instructions_text(self, rounds: int, wage_per_unit: float = 20) -> str:
        """Create static instructions text for the lab experiment.

        Suitable for use as an Agent instruction (system prompt) so the game
        rules are sent once per API call rather than repeated in every question
        prompt. The round-specific income cap is omitted here because it is
        already included in each question via create_lab_experiment_survey.

        Args:
            rounds: Number of rounds in the experiment
            wage_per_unit: Wage per unit of labor (default: 20)

        Returns:
            Instructions text string
        """
        return (
            "You will now participate in a decision-making experiment on "
            + "behavior towards taxation. This experiment has a decision and "
            + "a working stage: \n"
            + f"The decision stage consists of {rounds} rounds. In each round you "
            + "will choose how much income you want to earn. The income "
            + "determines the number of tasks you have to complete later. "
            + "The task is to transcribe words. \n"
            + " You will have to pay taxes on your income. The tax rate "
            + "may, but does not have to, vary from round to round. Each of "
            + f"the {rounds} rounds is independent of each other. \n"
            + "In each round, you are first informed of the tax rate in this "
            + "round and the income that you can earn. The higher the income "
            + "you choose, the more tasks you will have to complete. The lower "
            + "the income, the earlier you can finish the experiment. "
            + f"{wage_per_unit} cents correspond to 1 task. \n"
            + "After you have entered an income, the number of tasks and the "
            + "due tax payment will be automatically calculated and shown on "
            + "the screen. The tax payment equals the chosen income "
            + "multiplied by the tax rate. After each round, you will "
            + "receive information about your payoff. Your payoff is the "
            + "chosen income minus the tax payment. \n"
            + "In the working stage, you will have to complete the number "
            + "of tasks to earn the income that you indicated in one of "
            + f"the previous {rounds} rounds. This round will be randomly selected. "
            + "It also determines how much your additional earnings from the "
            + "experiment will be. \n"
            # + "On the following screen, we will explain the working stage in "
            # + "more detail. \n"
            # + f"After the {rounds} rounds in the decision stage, you will have to "
            # + "work on the income you chose in one randomly selected round. \n"
            # + "Your task is to transcribe text sequences. Each text "
            # + "sequence consists of 10 letters, see the example below. "
            # + "The number of tasks that you will work on depends on your "
            # + f"decisions in the {rounds} rounds and on chance. A sequence is "
            # + "counted when you correctly typed in every letter. \n"
            # + "Text sequence: acyrgxrcqm \n"
        )

    def create_lab_experiment_survey(
        self,
        round_num: int,
        tax_schedule: str,
        labor_endowment: int,
        wage_per_unit: float = 20,
        rounds: int = 16,
        low_rate: float = 25,
        high_rate: float = 50,
    ) -> "Survey":
        """Create survey for PKNF lab experiment replication.

        Args:
            round_num: Round number (1-16)
            tax_schedule: Tax schedule type ("flat25", "flat50", "progressive")
            labor_endowment: Maximum labor units available
            wage_per_unit: Wage per unit of labor (default: 20)
            rounds: Number of rounds (default: 16)
            low_rate: Low marginal tax rate as a percentage (default: 25)
            high_rate: High marginal tax rate as a percentage (default: 50)

        Returns:
            EDSL Survey object
        """
        # Try to use enum for better descriptions
        # try:
        #     from llm_eti.pknf_types import TaxSchedule

        #     schedule_enum = TaxSchedule(tax_schedule)
        #     tax_schedule = schedule_enum.value
        #     tax_desc = schedule_enum.description
        # except (ImportError, ValueError):
        #     # Fallback to original logic
        #     if tax_schedule == "flat25":
        #         tax_desc = "a flat tax rate of 25%"
        #     elif tax_schedule == "flat50":
        #         tax_desc = "a flat tax rate of 50%"
        #     else:  # progressive
        #         tax_desc = "a progressive tax where income up to 400 is taxed at 25%, and income above 400 is taxed at 50%"

        if tax_schedule == "flat25":
            rate1 = low_rate
        elif tax_schedule == "flat50":
            rate1 = high_rate
        else:  # progressive
            rate1 = low_rate
            rate2 = high_rate
        bkt1 = 400

        # Create base prompt with simpler language
        if tax_schedule != "progressive":
            tax_text = (
                "In this round, the tax rate is "
                + f"{rate1}"
                + "% for all incomes. For example, for an income of "
                + f"{bkt1 + 20} cents, your tax payment will be "
                + f"{(rate1 / 100) * 420:.0f}"
                + " cents."
            )
        else:
            tax_text = (
                "In this round, the tax rate is "
                + f"{rate1}"
                + "% for incomes equal to or below "
                + f"{bkt1}"
                + " cents.  The tax rate is "
                + f"{rate2}"
                + "% on the entire income if income exceeds "
                + f"{bkt1}"
                + f" cents. For example, for an income of {bkt1 + 20} "
                + " cents, your tax payment will be "
                + f"{(rate2 / 100) * (bkt1 + 20):.0f}"
                + " cents."
            )
        prompt = (
            f"Round {round_num} of {rounds} \n"
            + tax_text
            + "\n"
            + f"You can earn an income of {labor_endowment * wage_per_unit:.0f}"
            + " cents. \n"
            + "Please indicate whether you want to work for "
            + f"{labor_endowment * wage_per_unit:.0f} cents or another income. "
            + "Reply with a single integer number of cents (e.g. 340). "
            + "Do not include any text, units, or explanation — only the number.\n"
        )

        question = QuestionNumerical(
            question_name="income_response",
            question_text=prompt,
            min_value=0,
            max_value=labor_endowment * wage_per_unit,
        )

        return Survey([question])

    def create_lab_experiment_survey_template(self) -> "Survey":
        """Create a scenario-backed PKNF question for batched execution."""
        prompt = (
            "Round {{ round_num }} of {{ rounds }}\n{{ tax_text }}\n"
            "You can earn an income of {{ max_income }} cents.\n"
            "Please indicate whether you want to work for {{ max_income }} cents or another income. "
            "Reply with a single integer number of cents (e.g. 340). "
            "Do not include any text, units, or explanation — only the number."
        )
        # QuestionNumerical validates bounds when the question is constructed,
        # so its maximum cannot vary by scenario. Validate the scenario-specific
        # cap after parsing instead.
        return Survey(
            [QuestionFreeText(question_name="income_response", question_text=prompt)]
        )

    def run_survey(self, survey: "Survey", agent: Optional["Agent"] = None) -> Any:
        """Run a single survey.

        Args:
            survey: EDSL Survey object
            agent: Optional Agent with specific traits

        Returns:
            Survey results
        """
        # Handle model creation with service names for specific providers
        if self.model.startswith("gemini-"):
            model = Model(self.model, service_name="google")
        else:
            model = Model(self.model)

        if agent:
            job = Jobs(survey=survey, agents=[agent], models=[model])
        else:
            job = Jobs(survey=survey, models=[model])

        # Run with caching enabled by default
        results = job.run(cache=self.use_cache)

        return results

    @staticmethod
    def _parse_income_response(raw_response: Any) -> Dict[str, Optional[float]]:
        """Parse EDSL tax response payloads into expected income fields."""

        def empty_response() -> Dict[str, Optional[float]]:
            return {"broad_income": None, "taxable_income": None}

        def parse_number(value: Any) -> Optional[float]:
            if value is None or value is False or value is True:
                return None
            if isinstance(value, (int, float)):
                return None if value != value else float(value)

            value_text = str(value).strip()
            if not value_text or value_text.lower() in {"nan", "none", "null"}:
                return None

            try:
                return float(value_text.replace("$", "").replace(",", ""))
            except ValueError:
                return None

        def extract_field(text: str, field_name: str) -> Optional[float]:
            pattern = re.compile(
                rf'"?{re.escape(field_name)}"?\s*:\s*'
                r"(?P<value>null|-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)",
                re.IGNORECASE,
            )
            match = pattern.search(text)
            if not match:
                return None
            return parse_number(match.group("value"))

        if raw_response is None:
            return empty_response()

        if isinstance(raw_response, float) and raw_response != raw_response:
            return empty_response()

        def parse_text_payload(response_text: str) -> Dict[str, Optional[float]]:
            text = response_text.strip()
            if not text or text.lower() in {"nan", "none", "null"}:
                return empty_response()

            # Strip code fences if the model wraps the answer in markdown.
            if text.startswith("```"):
                lines = text.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                text = "\n".join(lines).strip()

            candidate_dict = None
            try:
                candidate_dict = ast.literal_eval(text)
            except (ValueError, SyntaxError):
                try:
                    import json

                    candidate_dict = json.loads(text)
                except Exception:
                    candidate_dict = None

            if isinstance(candidate_dict, dict):
                if isinstance(candidate_dict.get("answer"), dict):
                    candidate_dict = candidate_dict["answer"]
                return {
                    "broad_income": parse_number(candidate_dict.get("broad_income")),
                    "taxable_income": parse_number(
                        candidate_dict.get("taxable_income")
                    ),
                }

            broad_income = None
            taxable_income = None
            for line in text.splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                key = key.strip().lower().replace(" ", "_")
                value = value.strip()
                if key in {"broad_income", "broadincome"}:
                    broad_income = parse_number(value)
                elif key in {"taxable_income", "taxableincome"}:
                    taxable_income = parse_number(value)

            if broad_income is None:
                broad_income = extract_field(text, "broad_income")
            if taxable_income is None:
                taxable_income = extract_field(text, "taxable_income")

            return {
                "broad_income": broad_income,
                "taxable_income": taxable_income,
            }

        if isinstance(raw_response, dict):
            response_dict = raw_response
            if isinstance(response_dict.get("answer"), dict):
                response_dict = response_dict["answer"]
            elif isinstance(response_dict.get("answer"), str):
                return parse_text_payload(response_dict["answer"])
            elif isinstance(response_dict.get("raw_model_response"), str):
                return parse_text_payload(response_dict["raw_model_response"])

            return {
                "broad_income": parse_number(response_dict.get("broad_income")),
                "taxable_income": parse_number(response_dict.get("taxable_income")),
            }

        return parse_text_payload(str(raw_response))

    def _extract_tax_result_from_row(
        self, scenario: Dict[str, Any], row: Any, attempt_number: int
    ) -> Optional[Dict[str, Any]]:
        income_response_raw = row.get("answer.income_responses")
        raw_model_response = row.get(
            "raw_model_response.income_responses_raw_model_response"
        )
        parsed = self._parse_income_response(
            income_response_raw
            if income_response_raw is not None
            and str(income_response_raw).strip().lower()
            not in {
                "nan",
                "none",
                "null",
            }
            else raw_model_response
        )

        parsed_broad_income = parsed["broad_income"]
        parsed_taxable_income = parsed["taxable_income"]
        if parsed_broad_income is None or parsed_taxable_income is None:
            return None

        result_dict = scenario.copy()
        result_dict["broad_income_this"] = parsed_broad_income
        result_dict["taxable_income_this"] = parsed_taxable_income
        result_dict["model"] = row.get("model.model", self.model)
        result_dict["income_response_raw"] = income_response_raw
        result_dict["raw_model_response"] = raw_model_response
        result_dict["response_attempt"] = attempt_number
        result_dict["implied_eti_broad"] = self.calculate_eti(
            scenario["mtr_last"],
            scenario["mtr_this"],
            scenario["broad_income"],
            parsed_broad_income,
        )
        result_dict["implied_eti_taxable"] = self.calculate_eti(
            scenario["mtr_last"],
            scenario["mtr_this"],
            scenario["taxable_income"],
            parsed_taxable_income,
        )
        return result_dict

    def _run_job_with_server_retry(
        self,
        job: Any,
        use_cache: bool,
        max_server_retries: int = 5,
        base_wait: float = 30.0,
    ) -> Any:
        """Run an EDSL job with exponential backoff for transient server errors (5xx)."""
        for attempt in range(max_server_retries):
            try:
                return job.run(cache=use_cache)
            except Exception as exc:
                exc_name = type(exc).__name__
                exc_str = str(exc)
                is_server_error = "CoopServerResponseError" in exc_name or any(
                    code in exc_str for code in ("502", "503", "504", "Bad gateway")
                )
                if is_server_error and attempt < max_server_retries - 1:
                    wait = base_wait * (2**attempt)
                    logger.warning(
                        "Server error on attempt %d/%d, retrying in %.0fs: %s",
                        attempt + 1,
                        max_server_retries,
                        wait,
                        exc,
                    )
                    print(
                        f"\n⚠️  Server error (attempt {attempt + 1}/{max_server_retries}), "
                        f"retrying in {wait:.0f}s..."
                    )
                    time.sleep(wait)
                else:
                    raise
        return None  # unreachable

    def _run_tax_survey_with_retries(
        self,
        scenario: Dict[str, Any],
        n: int,
        agents: List["Agent"],
        model: Any,
        max_attempts: int = 3,
    ) -> List[Dict[str, Any]]:
        """Run a tax survey with retries and return only valid response rows."""
        all_results: List[Dict[str, Any]] = []
        attempts = 0

        while attempts < max_attempts and len(all_results) < n:
            attempts += 1
            remaining = n - len(all_results)
            attempt_agents = agents[:remaining]
            job = Jobs(
                survey=self.create_tax_survey(**scenario),
                agents=attempt_agents,
                models=[model],
            )
            try:
                results = self._run_job_with_server_retry(
                    job, use_cache=self.use_cache if attempts == 1 else False
                )
            except Exception as exc:
                logger.error(
                    "Tax survey failed after server retries (attempt=%d/%d): %s",
                    attempts,
                    max_attempts,
                    exc,
                )
                continue
            if results is None:
                continue

            df = results.to_pandas()
            if df.empty:
                continue

            df.to_csv(
                f"edsl_output_tax_{scenario.get('mtr_this', 'round' + str(scenario.get('round_num', 'unknown')))}.csv",
                index=False,
            )

            for _, row in df.iterrows():
                result_dict = self._extract_tax_result_from_row(
                    scenario, row, attempt_number=attempts
                )
                if result_dict is not None:
                    all_results.append(result_dict)
                if len(all_results) >= n:
                    break

        return all_results

    @staticmethod
    def _is_truthy(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes"}

        try:
            if value != value:
                return False
            return bool(value)
        except (TypeError, ValueError):
            return False

    @classmethod
    def _has_validated_answers(cls, df: Any) -> Optional[bool]:
        validation_columns = [
            column for column in df.columns if column.startswith("validated.")
        ]
        if not validation_columns:
            return None

        values = df[validation_columns].to_numpy().ravel()
        return any(cls._is_truthy(value) for value in values)

    def _get_edsl_run_details(self, results: Any) -> Dict[str, Any]:
        details = {
            "job_uuid": getattr(results, "job_uuid", None),
            "results_uuid": getattr(results, "results_uuid", None),
        }
        job_uuid = details["job_uuid"]
        if not job_uuid:
            return details

        try:
            from edsl.coop import Coop

            job_status = Coop(api_key=self.api_key).new_remote_inference_get(job_uuid)
        except Exception as exc:
            details["remote_status"] = f"unavailable ({type(exc).__name__}: {exc})"
            return details

        latest_details = job_status.get("latest_job_run_details", {}) or {}
        interview_details = latest_details.get("interview_details", {}) or {}

        details.update(
            {
                "remote_status": job_status.get("status"),
                "failure_reason": latest_details.get("failure_reason"),
                "failure_description": latest_details.get("failure_description"),
                "error_report_url": latest_details.get("error_report_url"),
                "total_interviews": interview_details.get("total_interviews"),
                "completed_interviews": interview_details.get("completed_interviews"),
                "interviews_with_exceptions": interview_details.get(
                    "interviews_with_exceptions"
                ),
            }
        )
        return details

    def _raise_if_no_usable_edsl_results(
        self, df: Any, results: Any, survey_type: str, scenario: Dict[str, Any]
    ) -> None:
        if df.empty:
            details = self._get_edsl_run_details(results)
            raise RuntimeError(
                self._format_edsl_failure_message(
                    "EDSL returned an empty results table",
                    details,
                    survey_type,
                    scenario,
                    row_count=0,
                )
            )

        if survey_type == "tax":
            return

        has_validated_answers = self._has_validated_answers(df)
        if has_validated_answers is not False:
            return

        details = self._get_edsl_run_details(results)
        raise RuntimeError(
            self._format_edsl_failure_message(
                "EDSL returned no validated answers",
                details,
                survey_type,
                scenario,
                row_count=len(df),
            )
        )

    def _format_edsl_failure_message(
        self,
        reason: str,
        details: Dict[str, Any],
        survey_type: str,
        scenario: Dict[str, Any],
        row_count: int,
    ) -> str:
        parts = [
            reason,
            f"survey_type={survey_type}",
            f"model={self.model}",
            f"rows={row_count}",
        ]

        for key in (
            "job_uuid",
            "results_uuid",
            "remote_status",
            "failure_reason",
            "failure_description",
            "total_interviews",
            "completed_interviews",
            "interviews_with_exceptions",
            "error_report_url",
        ):
            value = details.get(key)
            if value is not None:
                parts.append(f"{key}={value}")

        if "mtr_this" in scenario:
            parts.append(f"mtr_this={scenario['mtr_this']}")
        elif "round_num" in scenario:
            parts.append(f"round_num={scenario['round_num']}")

        return "; ".join(parts)

    @staticmethod
    def _parse_lab_income_response(row: Any) -> Optional[float]:
        """Extract a numeric income value from a lab experiment result row.

        Tries the validated answer first, then falls back to the raw model
        response, applying string-to-number coercion (strip $, commas, etc.)
        and a regex scan for the first number in the string.
        """

        def try_float(value: Any) -> Optional[float]:
            if value is None:
                return None
            try:
                val = float(str(value).strip().replace("$", "").replace(",", ""))
                return None if val != val else val  # guard NaN
            except (TypeError, ValueError):
                return None

        # Primary: validated/parsed answer from QuestionNumerical
        answer = row.get("answer.income_response")
        parsed = try_float(answer)
        if parsed is not None:
            return parsed

        # Fallback: raw model response text
        raw = row.get("raw_model_response.income_response_raw_model_response")
        if raw is not None:
            raw_str = str(raw).strip()
            parsed = try_float(raw_str)
            if parsed is not None:
                return parsed
            # Last resort: find the first integer/decimal in the string
            match = re.search(r"-?\d+(?:\.\d+)?", raw_str)
            if match:
                return try_float(match.group())

        return None

    def _run_lab_survey_with_retries(
        self,
        scenario: Dict[str, Any],
        n: int,
        agents: List["Agent"],
        model: Any,
        max_attempts: int = 3,
    ) -> List[Dict[str, Any]]:
        """Run a lab survey with retries, returning n result dicts.

        Retries up to max_attempts times to collect n valid (numeric) responses.
        If fewer than n valid responses are obtained after all attempts, failure
        records (income=None, parse_failed=True) are appended so the caller
        always receives exactly n records.
        """
        all_results: List[Dict[str, Any]] = []
        attempts = 0
        last_raw = None

        while attempts < max_attempts and len(all_results) < n:
            attempts += 1
            remaining = n - len(all_results)
            attempt_agents = agents[:remaining]

            survey = self.create_lab_experiment_survey(**scenario)
            job = Jobs(survey=survey, agents=attempt_agents, models=[model])
            try:
                results = self._run_job_with_server_retry(
                    job, use_cache=self.use_cache if attempts == 1 else False
                )
            except Exception as exc:
                logger.error(
                    "Lab survey failed after server retries "
                    "(round=%s, attempt=%d/%d): %s",
                    scenario.get("round_num"),
                    attempts,
                    max_attempts,
                    exc,
                )
                continue

            if results is None:
                logger.warning(
                    "Lab survey returned no Results object (round=%s, attempt=%d/%d)",
                    scenario.get("round_num"),
                    attempts,
                    max_attempts,
                )
                continue

            df = results.to_pandas()
            if df.empty:
                logger.warning(
                    "Lab survey returned empty DataFrame (round=%s, attempt=%d/%d)",
                    scenario.get("round_num"),
                    attempts,
                    max_attempts,
                )
                continue

            df.to_csv(
                f"edsl_output_lab_round{scenario.get('round_num', 'unknown')}.csv",
                index=False,
            )

            for _, row in df.iterrows():
                raw = row.get("answer.income_response")
                last_raw = raw
                income = self._parse_lab_income_response(row)

                if income is not None:
                    result_dict = scenario.copy()
                    result_dict["income"] = income
                    result_dict["response_raw"] = raw
                    result_dict["model"] = row.get("model.model", self.model)
                    result_dict["response_attempt"] = attempts
                    result_dict["parse_failed"] = False
                    all_results.append(result_dict)
                else:
                    logger.warning(
                        "Non-numeric income from lab response "
                        "(round=%s, attempt=%d/%d, raw=%r)",
                        scenario.get("round_num"),
                        attempts,
                        max_attempts,
                        raw,
                    )

                if len(all_results) >= n:
                    break

        # Pad with failure records if we couldn't collect n valid results
        if len(all_results) < n:
            logger.error(
                "Lab survey: only %d/%d valid results after %d attempts (round=%s)",
                len(all_results),
                n,
                attempts,
                scenario.get("round_num"),
            )
            for _ in range(n - len(all_results)):
                failure_dict = scenario.copy()
                failure_dict["income"] = None
                failure_dict["response_raw"] = last_raw
                failure_dict["model"] = self.model
                failure_dict["response_attempt"] = attempts
                failure_dict["parse_failed"] = True
                all_results.append(failure_dict)

        return all_results

    def _make_model(self) -> Any:
        """Construct the configured EDSL model in one place."""
        if self.model.startswith("gemini-"):
            return Model(self.model, service_name="google")
        return Model(self.model)

    @staticmethod
    def _chunks(
        items: List[Dict[str, Any]], size: int
    ) -> Iterable[List[Dict[str, Any]]]:
        for start in range(0, len(items), size):
            yield items[start : start + size]

    def run_batched_surveys(
        self,
        scenarios: List[Dict[str, Any]],
        *,
        survey_type: str,
        responses_per_scenario: int = 1,
        agent_instruction: Optional[str] = None,
        batch_size: int = 100,
        max_in_flight: int = 1,
        fresh: bool = True,
        on_submit: Optional[Callable[[List[Dict[str, Any]], Any], None]] = None,
        on_chunk_complete: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute scenario chunks as bounded concurrent remote EDSL jobs.

        Each chunk is one remote Job containing many independent interviews.  In
        production ``fresh`` prevents repeated simulated subjects from silently
        becoming remote-cache hits. ``on_submit`` receives the background Results
        handle immediately, allowing callers to checkpoint its job UUID.
        """
        if batch_size < 1 or max_in_flight < 1 or responses_per_scenario < 1:
            raise ValueError(
                "batch_size, max_in_flight, and responses_per_scenario must be positive"
            )
        if not scenarios:
            return []

        survey = (
            self.create_tax_survey_template()
            if survey_type == "tax"
            else self.create_lab_experiment_survey_template()
        )
        agent = Agent(name="Batched respondent", instruction=agent_instruction)

        def submit_and_fetch(chunk: List[Dict[str, Any]]) -> Any:
            """Submit once, then tolerate temporary connection loss while polling."""
            pending = None
            for attempt in range(1, 5):
                try:
                    job = Jobs(
                        survey=survey,
                        agents=[agent],
                        models=[self._make_model()],
                        scenarios=[Scenario(scenario) for scenario in chunk],
                    )
                    pending = job.run(
                        cache=False if fresh else self.use_cache,
                        fresh=fresh,
                        disable_remote_cache=fresh,
                        background=True,
                        remote_inference_description=(
                            f"llm-eti {survey_type} batch ({len(chunk)} scenarios)"
                        ),
                    )
                    break
                except Exception as exc:
                    if attempt == 4:
                        raise
                    wait_seconds = 5 * (2 ** (attempt - 1))
                    logger.warning(
                        "Remote %s batch submission failed (%s); retrying in %ss "
                        "(%s/4)",
                        survey_type,
                        type(exc).__name__,
                        wait_seconds,
                        attempt,
                    )
                    time.sleep(wait_seconds)

            if on_submit is not None:
                on_submit(chunk, pending)

            for attempt in range(1, 5):
                try:
                    return pending.fetch(polling_interval=2.0)
                except Exception as exc:
                    if attempt == 4:
                        raise
                    wait_seconds = 5 * (2 ** (attempt - 1))
                    logger.warning(
                        "Remote %s batch polling failed (%s); retrying in %ss (%s/4)",
                        survey_type,
                        type(exc).__name__,
                        wait_seconds,
                        attempt,
                    )
                    time.sleep(wait_seconds)
            raise AssertionError("unreachable")

        results: List[Dict[str, Any]] = []
        chunks = iter(self._chunks(scenarios, batch_size))
        with ThreadPoolExecutor(max_workers=max_in_flight) as executor:
            pending = {}
            for _ in range(max_in_flight):
                try:
                    chunk = next(chunks)
                except StopIteration:
                    break
                pending[executor.submit(submit_and_fetch, chunk)] = chunk

            while pending:
                done, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in done:
                    chunk = pending.pop(future)
                    try:
                        df = future.result().to_pandas()
                    except Exception as exc:
                        raise RuntimeError(
                            f"Remote {survey_type} batch failed for {len(chunk)} scenarios"
                        ) from exc
                    scenario_by_id = {str(s["work_id"]): s for s in chunk}
                    chunk_results: List[Dict[str, Any]] = []
                    for _, row in df.iterrows():
                        scenario = scenario_by_id.get(str(row.get("scenario.work_id")))
                        if scenario is None:
                            logger.warning(
                                "Dropping EDSL result without a known work_id"
                            )
                            continue
                        if survey_type == "tax":
                            parsed = self._extract_tax_result_from_row(scenario, row, 1)
                            if parsed is not None:
                                parsed["response_number"] = (
                                    int(row.get("iteration.iteration", 0)) + 1
                                )
                                results.append(parsed)
                                chunk_results.append(parsed)
                        else:
                            income = self._parse_lab_income_response(row)
                            if (
                                income is not None
                                and not 0 <= income <= scenario["max_income"]
                            ):
                                logger.warning(
                                    "Lab income outside scenario range (work_id=%s, income=%s)",
                                    scenario["work_id"],
                                    income,
                                )
                                income = None
                            parsed = scenario.copy()
                            parsed.update(
                                {
                                    "income": income,
                                    "response_raw": row.get("answer.income_response"),
                                    "model": row.get("model.model", self.model),
                                    "response_attempt": 1,
                                    "parse_failed": income is None,
                                }
                            )
                            results.append(parsed)
                            chunk_results.append(parsed)
                    if on_chunk_complete is not None:
                        on_chunk_complete(chunk_results)
                    try:
                        next_chunk = next(chunks)
                    except StopIteration:
                        continue
                    pending[executor.submit(submit_and_fetch, next_chunk)] = next_chunk
        return results

    def run_batch_surveys(
        self,
        scenarios: List[Dict[str, Any]],
        n: int = 1,
        survey_type: str = "tax",
        agent_instruction: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Run multiple survey scenarios.

        Args:
            scenarios: List of scenario dictionaries
            n: Number of responses per scenario
            survey_type: Type of survey ("tax" or "lab")

        Returns:
            List of result dictionaries
        """
        all_results = []

        for scenario in scenarios:
            if survey_type == "tax":
                agents = [
                    Agent(name=f"Respondent_{i + 1}", instruction=agent_instruction)
                    for i in range(n)
                ]

                if self.model.startswith("gemini-"):
                    model = Model(self.model, service_name="google")
                else:
                    model = Model(self.model)

                all_results.extend(
                    self._run_tax_survey_with_retries(
                        scenario=scenario,
                        n=n,
                        agents=agents,
                        model=model,
                    )
                )
                continue

            # Create multiple agents for batch processing
            agents = [
                Agent(name=f"Respondent_{i + 1}", instruction=agent_instruction)
                for i in range(n)
            ]

            # Handle model creation with service names
            if self.model.startswith("gemini-"):
                model = Model(self.model, service_name="google")
            else:
                model = Model(self.model)

            all_results.extend(
                self._run_lab_survey_with_retries(
                    scenario=scenario,
                    n=n,
                    agents=agents,
                    model=model,
                )
            )

        return all_results

    @staticmethod
    def calculate_eti(
        initial_rate: float, new_rate: float, initial_income: float, new_income: float
    ) -> Optional[float]:
        """Calculate elasticity of taxable income.

        Args:
            initial_rate: Initial marginal tax rate
            new_rate: New marginal tax rate
            initial_income: Initial income
            new_income: New income

        Returns:
            ETI value or None if calculation fails
        """
        try:
            percent_change_income = (new_income - initial_income) / initial_income
            percent_change_net_of_tax_rate = ((1 - new_rate) - (1 - initial_rate)) / (
                1 - initial_rate
            )

            if percent_change_net_of_tax_rate == 0:
                return None

            return percent_change_income / percent_change_net_of_tax_rate
        except (ZeroDivisionError, TypeError):
            return None
