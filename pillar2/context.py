# # pillar2/context.py

# from dataclasses import dataclass


# @dataclass
# class Pillar1Context:
#     class_number: int
#     class_title: str
#     class_category: str
#     filing_basis: str
#     specimen_description: str = ""
#     has_class_error: bool = False
#     error_summary: str = ""
# i have added p1_findings: list = None in pillar2/context.py but now new error occur see below then fix it -
# Pipeline import error:

# Traceback (most recent call last):
#   File "D:\TMEP_Assist\inputLayer\app.py", line 227, in <module>
#     state = run_full_pipeline(result["data"])
#             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "D:\TMEP_Assist\run_pipeline.py", line 29, in run_full_pipeline
#     p2_output = run_pillar2(application_dict, p1_output)
#                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "D:\TMEP_Assist\pillar2\service.py", line 30, in run_pillar2
#     context = Pillar1Context(
#               ^^^^^^^^^^^^^^^
# TypeError: Pillar1Context.__init__() missing 2 required positional arguments: 'class_category' and 'filing_basis
# analyse vs-code output:(tmep-assist) PS D:\TMEP_Assist> streamlit run inputLayer/app.py

#   You can now view your Streamlit app in your browser.

#   Local URL: http://localhost:8501
#   Network URL: http://10.194.185.158:8501

# 2026-03-01 01:31:37,862 | INFO | trademark_engine | Starting full trademark examination pipeline.
# 2026-03-01 01:31:37,862 | INFO | trademark_engine | Running Pillar 1 — Classification Engine.
# 2026-03-01 01:31:38,066 | INFO | trademark_engine | Running Pillar 2 — Identification Engine.
# pillar2/context.py

from dataclasses import dataclass


@dataclass
class Pillar1Context:
    class_number: int
    class_category: str
    filing_basis: str
    specimen_description: str = ""
    has_class_error: bool = False
    p1_findings: list = None