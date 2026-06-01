import json
from pathlib import Path
from scheduler.models import Scenario

def load_scenario_from_file(file_path: str) -> Scenario:
    """Load and validate a scenario from a JSON file path."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Using Pydantic v2 validation
    return Scenario.model_validate(data)

def load_scenario_by_id(scenario_dir: str, scenario_id: int) -> Scenario:
    """Load a scenario by its number (e.g., 1 to 5) from a directory."""
    path = Path(scenario_dir) / f"scenario{scenario_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Scenario file not found: {path}")
    return load_scenario_from_file(str(path))
