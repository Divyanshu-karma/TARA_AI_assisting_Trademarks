"""
main.py
========
Primary API entry point for TMEP Assist Examination Engine.

This file exposes clean callable functions for:
- Pillar 1 only
- Full 3-pillar pipeline
- Future extension to §800, §704.02, §1200 etc.

No CLI.
No Streamlit.
Pure orchestration layer.
"""

from typing import Dict, Any

from run_pipeline import run_full_pipeline
from pillar1.service import run_pillar1


# ─────────────────────────────────────────────
# PILLAR 1 ONLY
# ─────────────────────────────────────────────

def assess_classification(application_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs only Pillar 1 (§1401 Classification).
    Used by Streamlit lightweight validation.
    """
    return run_pillar1(application_dict)


# ─────────────────────────────────────────────
# FULL ENGINE
# ─────────────────────────────────────────────

def assess_full_examination(application_dict: Dict[str, Any]):
    """
    Runs full 3-pillar structural examination.

    Returns:
        PipelineState
    """
    return run_full_pipeline(application_dict, save_result=True)