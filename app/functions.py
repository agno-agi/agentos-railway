"""
Workflow Step Functions
=======================

Deterministic building blocks for Studio-built workflows, registered in the
Studio registry's `functions` slot (app/registry.py). Each function is a step
executor: the runtime calls it as `func(step_input)` with a `StepInput`, and it
returns a string (the step's content) or a `StepOutput` when the step attaches
a downloadable file artifact. No model calls, no tokens, no side effects — a
function step's behavior is exactly its code.

Agent Builder discovers these through `list_functions`, which surfaces each
function's name, docstring, and signature. The docstring is the contract a
builder relies on, so keep its first line precise about input and output.
"""

import csv
import io
import json
import re
from typing import Any

from agno.media import File
from agno.workflow import StepInput, StepOutput

_URL_PATTERN = re.compile(r"https?://[^\s<>\"')\]]+")
_TABLE_ROW_CAP = 50


def _step_text(step_input: StepInput) -> str:
    """The text a function step operates on: the previous step's output, else the workflow input."""
    if step_input.previous_step_content is not None:
        return str(step_input.previous_step_content)
    return step_input.get_input_as_string() or ""


def _first_json_value(text: str) -> Any:
    """Decode the first JSON object or array found in text; raise ValueError when none decodes."""
    decoder = json.JSONDecoder()
    for match in re.finditer(r"[\[{]", text):
        try:
            value, _ = decoder.raw_decode(text, match.start())
        except json.JSONDecodeError:
            continue
        return value
    raise ValueError("no valid JSON object or array in the previous step's output")


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def route_component_type(step_input: StepInput) -> str:
    """Suggest agent, team, or workflow for the request in the previous step's output (or the workflow input)."""
    lower = _step_text(step_input).lower()
    if any(word in lower for word in ("daily", "schedule", "pipeline", "approval", "steps", "workflow")):
        return "workflow"
    if any(word in lower for word in ("team", "specialists", "debate", "reviewers", "coordinate")):
        return "team"
    return "agent"


def score_eval_status(step_input: StepInput) -> str:
    """PASS when the eval report in the previous step's output shows every case passed, FAIL otherwise.

    Reads JSON `passed`/`total` keys, or an `N/M passed` line like the run-evals report emits.
    """
    text = _step_text(step_input)
    passed = total = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict) and isinstance(data.get("passed"), int) and isinstance(data.get("total"), int):
        passed, total = data["passed"], data["total"]
    else:
        match = re.search(r"(\d+)\s*/\s*(\d+)\s*passed", text)
        if match:
            passed, total = int(match.group(1)), int(match.group(2))
    if passed is None or total is None or total <= 0:
        return "FAIL"
    return "PASS" if passed == total else "FAIL"


def extract_json(step_input: StepInput) -> str:
    """Return the first JSON object or array found in the previous step's output, validated and pretty-printed.

    Errors when the previous step produced no parseable JSON — put this step between a
    gathering agent and any step that needs structured input.
    """
    return json.dumps(_first_json_value(_step_text(step_input)), indent=2, ensure_ascii=False)


def extract_urls(step_input: StepInput) -> str:
    """Return the URLs found in the previous step's output, deduplicated in order, one per line."""
    urls = dict.fromkeys(url.rstrip(".,;:!?") for url in _URL_PATTERN.findall(_step_text(step_input)))
    return "\n".join(urls)


def json_to_csv(step_input: StepInput) -> StepOutput:
    """Convert a JSON array of objects from the previous step's output into a downloadable data.csv file artifact.

    Columns are the union of the objects' keys in first-appearance order; nested values are
    JSON-encoded in their cell. Errors when the previous step holds no JSON array of objects.
    """
    value = _first_json_value(_step_text(step_input))
    if isinstance(value, dict):
        # Tolerate a single-array wrapper like {"rows": [...]}.
        arrays = [item for item in value.values() if isinstance(item, list)]
        if len(arrays) == 1:
            value = arrays[0]
    if not isinstance(value, list) or not value or not all(isinstance(row, dict) for row in value):
        raise ValueError("expected a JSON array of objects in the previous step's output")
    header: list[str] = []
    for row in value:
        for key in row:
            if key not in header:
                header.append(key)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=header, extrasaction="ignore")
    writer.writeheader()
    for row in value:
        writer.writerow({key: _cell(row.get(key)) for key in header})
    data = buffer.getvalue()
    return StepOutput(
        content=f"data.csv: {len(value)} rows, columns: {', '.join(header)}",
        files=[File(content=data.encode(), mime_type="text/csv", filename="data.csv")],
    )


def csv_to_markdown_table(step_input: StepInput) -> str:
    """Render CSV text from the previous step's output as a markdown table (capped at 50 data rows)."""
    rows = [row for row in csv.reader(io.StringIO(_step_text(step_input))) if row]
    if len(rows) < 2:
        raise ValueError("expected CSV with a header row and at least one data row")

    def line(cells: list[str]) -> str:
        return "| " + " | ".join(cell.replace("|", "\\|").strip() for cell in cells) + " |"

    header, data = rows[0], rows[1:]
    lines = [line(header), "| " + " | ".join("---" for _ in header) + " |"]
    lines += [line(row) for row in data[:_TABLE_ROW_CAP]]
    if len(data) > _TABLE_ROW_CAP:
        lines.append(f"… {len(data) - _TABLE_ROW_CAP} more rows")
    return "\n".join(lines)


def content_to_file(step_input: StepInput) -> StepOutput:
    """Attach the previous step's output unchanged as a downloadable output.md file artifact.

    The content also flows through as the step's output, so this works as a final
    "publish the result" step without breaking the chain.
    """
    text = _step_text(step_input)
    if not text.strip():
        raise ValueError("previous step produced no content to save")
    return StepOutput(
        content=text,
        files=[File(content=text.encode(), mime_type="text/markdown", filename="output.md")],
    )
