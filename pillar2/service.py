# pillar2/service.py

from .engine import Pillar2Engine
from .context import Pillar1Context


def run_pillar2(application_dict: dict, pillar1_output: dict):

    engine = Pillar2Engine()
    results = {}

    p1_application = pillar1_output.get("application")

    for cls in application_dict.get("classes", []):

        class_number = cls.get("class_number")
        identification = cls.get("identification", "")
        filing_basis = cls.get("filing_basis", "")

        # Try to get class_category from Pillar 1 application model
        class_category = "GOODS"

        if p1_application:
            for p1_cls in p1_application.classes:
                if p1_cls.class_number == class_number:
                    class_category = getattr(p1_cls, "class_category", "GOODS")
                    break

        context = Pillar1Context(
            class_number=class_number,
            class_category=class_category,
            filing_basis=filing_basis,
            p1_findings=pillar1_output.get("findings", [])
        )

        analysis_result = engine.analyze(identification, context)

        results[class_number] = {
            "summary": {
                "is_definite": analysis_result.is_definite,
                "errors": sum(1 for f in analysis_result.findings if f.severity == "ERROR"),
                "warnings": sum(1 for f in analysis_result.findings if f.severity == "WARNING"),
            },
            "tmep_1402_analysis": {
                "subsection_findings": [f.__dict__ for f in analysis_result.findings]
            }
        }

    return results



# # pillar2/service.py

# from .engine import Pillar2Engine
# from .context import Pillar1Context


# def run_pillar2(application_dict: dict, pillar1_output: dict):
#     """
#     Runs Pillar 2 (§1402 Identification) for all classes.

#     Returns:
#         {
#             class_number: {
#                 "summary": {...},
#                 "tmep_1402_analysis": {...}
#             }
#         }
#     """

#     engine = Pillar2Engine()
#     results = {}

#     p1_findings = pillar1_output.get("findings", [])

#     for cls in application_dict.get("classes", []):
#         class_number = cls.get("class_number")
#         identification = cls.get("identification", "")

#         # Build minimal Pillar1Context if needed
#         context = Pillar1Context(
#             class_number=class_number,
#             p1_findings=p1_findings
#         )

#         analysis_result = engine.analyze(identification, context)

#         results[class_number] = {
#             "summary": {
#                 "is_definite": analysis_result.is_definite,
#                 "errors": sum(1 for f in analysis_result.findings if f.severity == "ERROR"),
#                 "warnings": sum(1 for f in analysis_result.findings if f.severity == "WARNING"),
#             },
#             "tmep_1402_analysis": {
#                 "subsection_findings": [f.__dict__ for f in analysis_result.findings]
#             }
#         }

#     return results


# # pillar2/service.py

# from pillar2.engine import IdentificationEngine
# from pillar2.context import Pillar1Context


# def analyze_identification(text: str, pillar1_context: dict = None):

#     context_obj = None

#     if pillar1_context:
#         context_obj = Pillar1Context(**pillar1_context)

#     engine = IdentificationEngine()
#     result = engine.run(text, context_obj)

#     return {
#         "is_definite": result.is_definite,
#         "reasoning": result.reasoning,
#         "findings": [f.__dict__ for f in result.findings]
#     }
# pillar2/service.py

# from pillar2.engine import Pillar2Engine
# from pillar2.context import Pillar1Context


# def analyze_identification(text: str, pillar1_context: dict = None):

#     context_obj = None

#     if pillar1_context:
#         context_obj = Pillar1Context(**pillar1_context)

#     engine = Pillar2Engine()
#     result = engine.analyze(text, context_obj)

#     return {
#         "is_definite": result.is_definite,
#         "findings": [f.__dict__ for f in result.findings]
#     }