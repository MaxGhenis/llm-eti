"""No API client construction or model execution: fixtures for checkpoint tests."""

from llm_eti.edsl_client import EDSLClient


class OfflineLabClient:
    model = "offline-regression-fixture"
    use_cache = False
    create_instructions_text = EDSLClient.create_instructions_text
    create_lab_experiment_survey = EDSLClient.create_lab_experiment_survey

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
