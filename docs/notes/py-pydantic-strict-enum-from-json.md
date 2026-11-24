Pydantic strict mode refuses "warning" for a StrEnum field when you validate a dict from json.load; mark that field Field(strict=False) or validate the raw text with model_validate_json.

Seen in M2 (`backend/suits/core/alerts.py`, Pydantic 2.14). Strict mode is useful for data files (a "20" is not a number, a typo'd key fails), but in Python mode an enum field wants an enum instance. `model_validate_json` uses JSON-mode rules, where strings for enums are allowed even under strict.

- The rules and ranges loaders use `json.load` with a duplicate-key hook, so they validate a dict: `severity: Severity = Field(strict=False)` keeps the rest strict.
- The error reads "Input should be an instance of Severity", which looks like a bad file but is not.
