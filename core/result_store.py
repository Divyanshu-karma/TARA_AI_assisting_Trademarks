# # core/result_store.py

# import json
# import os
# from typing import Dict
# from core.pipeline_state import PipelineState


# class ResultStore:
#     """
#     Persistence layer for pipeline outputs.
#     Currently JSON-based.
#     Can be upgraded to DB-backed storage later.
#     """

#     def __init__(self, storage_dir: str = "storage"):
#         self.storage_dir = storage_dir
#         os.makedirs(self.storage_dir, exist_ok=True)

#     def save(self, state: PipelineState, filename: str) -> str:
#         """
#         Save pipeline state to JSON file.
#         """
#         filepath = os.path.join(self.storage_dir, f"{filename}.json")

#         with open(filepath, "w", encoding="utf-8") as f:
#             json.dump(state.to_dict(), f, indent=2)

#         return filepath

#     def load(self, filename: str) -> Dict:
#         """
#         Load stored JSON state.
#         """
#         filepath = os.path.join(self.storage_dir, f"{filename}.json")

#         if not os.path.exists(filepath):
#             raise FileNotFoundError(f"No stored result found for {filename}")

#         with open(filepath, "r", encoding="utf-8") as f:
#             return json.load(f)

# core/result_store.py
"""
ResultStore — Persistence layer for pipeline results.

Saves PipelineState and full 2nd-half results to JSON files.
Used at the end of run_pipeline.py for audit trail and replay.

Output path:  results/<application_serial>_<timestamp>.json
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RESULTS_DIR = Path("results")


class ResultStore:
    """
    Saves and loads complete pipeline results.

    Usage:
        store = ResultStore()
        path  = store.save(state, serial)
        data  = store.load(serial)
    """

    def __init__(self, results_dir: Path = RESULTS_DIR):
        self.results_dir = results_dir
        self.results_dir.mkdir(exist_ok=True)

    def save(self, state_or_result: Any, serial: str) -> str:
        """
        Saves a PipelineState or any JSON-serialisable result dict.

        Args:
            state_or_result: PipelineState (calls .to_dict()) or plain dict.
            serial:          Application serial number — used in filename.

        Returns:
            Path to the saved file.
        """
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"{serial}_{ts}.json"
        filepath = self.results_dir / filename

        # Support both PipelineState objects and plain dicts
        if hasattr(state_or_result, "to_dict"):
            data = state_or_result.to_dict()
        elif isinstance(state_or_result, dict):
            data = state_or_result
        else:
            data = {"result": str(state_or_result)}

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        return str(filepath)

    def load(self, serial: str) -> dict | None:
        """
        Loads the most recent saved result for a given serial number.

        Args:
            serial: Application serial number.

        Returns:
            Result dict, or None if not found.
        """
        matches = sorted(self.results_dir.glob(f"{serial}_*.json"), reverse=True)
        if not matches:
            return None
        with open(matches[0], encoding="utf-8") as f:
            return json.load(f)

    def list_results(self) -> list[str]:
        """Returns list of all saved result filenames."""
        return sorted(str(p.name) for p in self.results_dir.glob("*.json"))