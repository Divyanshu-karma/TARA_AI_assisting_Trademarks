# pipeline/__init__.py
"""
Pipeline Package — Structural-to-Substantive Bridge

Public API (what callers use):

    from pipeline.StructuralToSubstantiveGate import build_normalized_application
    from pipeline.pipeline_runner              import run_second_half

Full flow:
    state          = PipelineState(raw_input, p1_out, p2_out, p3_out)
    normalized_app = build_normalized_application(state)
    result         = run_second_half(normalized_app)
"""

from pipeline.StructuralToSubstantiveGate import build_normalized_application
from pipeline.pipeline_runner              import run_second_half

__all__ = ["build_normalized_application", "run_second_half"]
