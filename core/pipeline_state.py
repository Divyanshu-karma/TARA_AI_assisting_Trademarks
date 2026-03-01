# core/pipeline_state.py
"""
PipelineState — Unified container for the entire 3-pillar structural examination.

This object is the ONLY input the 1st half hands to the 2nd half.
All downstream engines, gates, and runners read from this single object.

Produced by:  Pillar 1 (Classification) + Pillar 2 (Identification)
              + Pillar 3 (Multi-class structural) + §800 (Procedural)

Consumed by:  StructuralToSubstantiveGate → build_normalized_application(state)
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class PipelineState:
    """
    Unified container for the entire 3-pillar structural examination.

    This object is the ONLY input to:
        - §800 Procedural Engine
        - §704.02 Search Engine
        - §1200 Substantive Engines
        - §904 Specimen Engine
        - Decision Aggregator
        - Office Action Generator
    """

    # RAW INPUT
    raw_input: Dict[str, Any]

    # PILLAR OUTPUTS
    pillar1_output: Dict[str, Any]
    pillar2_output: Dict[int, Dict[str, Any]]
    pillar3_output: Any

    # METADATA
    created_at:       str = field(default_factory=lambda: datetime.utcnow().isoformat())
    pipeline_version: str = "1.0.0"

    def is_structurally_clean(self) -> bool:
        p1_errors = self.pillar1_output.get("summary", {}).get("errors", 0)
        p3_errors = getattr(self.pillar3_output, "total_errors", 0)
        return p1_errors == 0 and p3_errors == 0

    def get_confirmed_classes(self):
        return sorted(str(int(k)).zfill(3) for k in self.pillar2_output.keys())

    def get_partial_refusal_classes(self):
        return getattr(self.pillar3_output, "partial_refusal_classes", [])

    def get_division_candidates(self):
        return getattr(self.pillar3_output, "division_eligible_classes", [])

    def get_clean_classes(self):
        refused = set(str(c).zfill(3) for c in self.get_partial_refusal_classes())
        return [c for c in self.get_confirmed_classes() if c not in refused]

    def get_identification_by_class(self):
        mapping = {}
        for cls, result in self.pillar2_output.items():
            analysis = result.get("tmep_1402_analysis", {})
            segments = analysis.get("identified_goods_services", [])
            mapping[cls] = segments
        return mapping

    def to_dict(self) -> Dict[str, Any]:
        def safe(obj):
            if hasattr(obj, "__dict__"):
                return asdict(obj) if hasattr(obj, "__dataclass_fields__") else obj.__dict__
            return obj

        return {
            "raw_input": self.raw_input,
            "pillar1_output": {
                "application": safe(self.pillar1_output.get("application")),
                "summary":     self.pillar1_output.get("summary"),
                "report":      self.pillar1_output.get("report"),
            },
            "pillar2_output":  self.pillar2_output,
            "pillar3_output":  asdict(self.pillar3_output)
                               if hasattr(self.pillar3_output, "__dataclass_fields__")
                               else self.pillar3_output,
            "created_at":       self.created_at,
            "pipeline_version": self.pipeline_version,
        }


# # core/pipeline_state.py

# from dataclasses import dataclass, field, asdict
# from typing import Dict, Any, Optional
# from datetime import datetime


# @dataclass
# class PipelineState:
#     """
#     Unified container for the entire 3-pillar structural examination.

#     This object is the ONLY input to:
#         - §800 Procedural Engine
#         - §704.02 Search Engine
#         - §1200 Substantive Engines
#         - §904 Specimen Engine
#         - Decision Aggregator
#         - Office Action Generator
#     """

#     # ───────────────────────────────────────────────
#     # RAW INPUT
#     # ───────────────────────────────────────────────
#     raw_input: Dict[str, Any]

#     # ───────────────────────────────────────────────
#     # PILLAR OUTPUTS
#     # ───────────────────────────────────────────────
#     pillar1_output: Dict[str, Any]          # exact return of Pillar 1
#     pillar2_output: Dict[int, Dict[str, Any]]  # per-class result
#     pillar3_output: Any                     # Pillar3AssessmentResult

#     # ───────────────────────────────────────────────
#     # METADATA
#     # ───────────────────────────────────────────────
#     created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
#     pipeline_version: str = "1.0.0"

#     # ============================================================
#     # COMPUTED STATE HELPERS (FOR NEXT LAYERS)
#     # ============================================================

#     def is_structurally_clean(self) -> bool:
#         """
#         True only if:
#             - No Pillar 1 errors
#             - No Pillar 3 errors
#         """
#         p1_errors = self.pillar1_output.get("summary", {}).get("errors", 0)
#         p3_errors = getattr(self.pillar3_output, "total_errors", 0)

#         return p1_errors == 0 and p3_errors == 0

#     def get_confirmed_classes(self):
#         """
#         Returns list of confirmed class numbers.
#         """
#         return sorted(self.pillar2_output.keys())

#     def get_partial_refusal_classes(self):
#         return getattr(self.pillar3_output, "partial_refusal_classes", [])

#     def get_division_candidates(self):
#         return getattr(self.pillar3_output, "division_eligible_classes", [])

#     def get_clean_classes(self):
#         refused = set(self.get_partial_refusal_classes())
#         return [c for c in self.get_confirmed_classes() if c not in refused]

#     def get_identification_by_class(self):
#         """
#         Used by §704.02 search engine and §1207 engine.
#         """
#         mapping = {}
#         for cls, result in self.pillar2_output.items():
#             analysis = result.get("tmep_1402_analysis", {})
#             segments = analysis.get("identified_goods_services", [])
#             mapping[cls] = segments
#         return mapping

#     # ============================================================
#     # SERIALIZATION
#     # ============================================================

#     # def to_dict(self) -> Dict[str, Any]:
#     #     return {
#     #         "raw_input": self.raw_input,
#     #         "pillar1_output": self.pillar1_output,
#     #         "pillar2_output": self.pillar2_output,
#     #         "pillar3_output": asdict(self.pillar3_output)
#     #         if hasattr(self.pillar3_output, "__dict__") else self.pillar3_output,
#     #         "created_at": self.created_at,
#     #         "pipeline_version": self.pipeline_version
#     #     }
#     def to_dict(self) -> Dict[str, Any]:

#         def safe(obj):
#             if hasattr(obj, "__dict__"):
#                 return asdict(obj) if hasattr(obj, "__dataclass_fields__") else obj.__dict__
#             return obj

#         return {
#             "raw_input": self.raw_input,

#             "pillar1_output": {
#                 "application": safe(self.pillar1_output.get("application")),
#                 "summary": self.pillar1_output.get("summary"),
#                 "report": self.pillar1_output.get("report"),
#             },

#             "pillar2_output": self.pillar2_output,

#             "pillar3_output": asdict(self.pillar3_output)
#             if hasattr(self.pillar3_output, "__dataclass_fields__")
#             else self.pillar3_output,

#             "created_at": self.created_at,
#             "pipeline_version": self.pipeline_version
#         }