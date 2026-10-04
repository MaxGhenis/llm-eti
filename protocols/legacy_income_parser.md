# Archived June 2026 income-response parser

The fenced excerpt below is copied byte-for-byte from
`b23f2cb882d33f79d706afbdcca836b3905361f8:llm_eti/edsl_client.py`, lines
298–409. The normal runner and the DeepSeek recovery script both called this
`EDSLClient._parse_income_response` method. Including its final line feed, the
4,545-byte excerpt has SHA-256
`7c274bd9d6796aef6c60473f8800a1a8ed9ebc1345db7c58e3742611ee02f399`.
The surrounding Markdown fence and this provenance header are not part of that
digest.

````python
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
````
