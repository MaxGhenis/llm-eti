"""No API client construction or model execution: fixtures for checkpoint tests."""

from llm_eti.edsl_client import EDSLClient


class OfflineLabClient:
    model = "offline-regression-fixture"
    use_cache = False
    create_instructions_text = EDSLClient.create_instructions_text
    create_lab_experiment_survey = EDSLClient.create_lab_experiment_survey
    create_lab_experiment_survey_template = (
        EDSLClient.create_lab_experiment_survey_template
    )

    def __init__(self):
        self.calls = []
        self.fail_rounds = set()
        self.raise_rounds = set()
        self.before_request = None

    def run_batch_surveys(self, scenarios, **kwargs):
        scenario = scenarios[0]
        if self.before_request is not None:
            self.before_request(scenario)
        self.calls.append(scenario)
        if scenario["round_num"] in self.raise_rounds:
            raise RuntimeError("Offline transport interruption")
        if scenario["round_num"] in self.fail_rounds:
            return [
                {
                    "income": None,
                    "parse_failed": True,
                    "response_raw": 'provider returned "invalid"\nsecond line',
                }
            ]
        income = 0 if scenario["round_num"] == 1 else 200
        return [{"income": income, "model": self.model, "response_raw": str(income)}]

    def run_batched_surveys(
        self, scenarios, *, batch_size, on_chunk_complete=None, **kwargs
    ):
        """Offline stand-in for chunked remote jobs; same per-round outcomes."""
        self.batch_sizes = getattr(self, "batch_sizes", [])
        results = []
        for start in range(0, len(scenarios), batch_size):
            chunk = scenarios[start : start + batch_size]
            self.batch_sizes.append(len(chunk))
            chunk_results = []
            for scenario in chunk:
                if self.before_request is not None:
                    self.before_request(scenario)
                self.calls.append(scenario)
                if scenario["round_num"] in self.raise_rounds:
                    raise RuntimeError("Offline batch failure")
                if scenario["round_num"] in getattr(self, "omit_rounds", set()):
                    continue
                parsed = scenario.copy()
                if scenario["round_num"] in self.fail_rounds:
                    parsed.update(
                        {"income": None, "parse_failed": True, "response_raw": "bad"}
                    )
                else:
                    income = 0 if scenario["round_num"] == 1 else 200
                    parsed.update(
                        {
                            "income": income,
                            "model": self.model,
                            "response_raw": str(income),
                            "parse_failed": False,
                        }
                    )
                chunk_results.append(parsed)
                results.append(parsed)
            if on_chunk_complete is not None:
                on_chunk_complete(chunk_results)
        return results
