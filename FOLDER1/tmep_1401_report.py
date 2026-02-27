"""
TMEP 1401 — PROFESSIONAL LEGAL REPORT GENERATOR
================================================
Output layer only. Zero logic. Zero validation.
All findings sourced from TMEP1401Assessor unchanged.
"""

from datetime import datetime
from tmep_1401_assessor import AssessmentFinding, TrademarkApplication


class TMEP1401ReportGenerator:

    # Severity symbols kept minimal
    _SEV = {"ERROR": "■", "WARNING": "▲", "INFO": "◆", "OK": "✓"}

    # Only sections that carry user-visible legal meaning
    _SECTION_LABELS = {
        "§1401.01": "Filing Authority",
        "§1401.02": "Classification System",
        "§1401.03": "Class Designation",
        "§1401.04": "Filing Fees",
        "§1401.05": "Classification Basis",
        "§1401.06": "Specimen — Class Alignment",
        "§1401.07": "Specimen — Reclassification",
        "§1401.08": "Class / Identification Alignment",
        "§1401.09": "Nice Edition Compliance",
        "§1401.10": "ID Manual Currency",
        "§1401.11": "Class 42 Restructuring (8th Ed.)",
        "§1401.12": "9th Edition Changes",
        "§1401.13": "10th Edition Changes",
        "§1401.14": "11th Edition Changes",
        "§1401.15": "12th Edition (Current)",
    }

    def __init__(self, application: TrademarkApplication,
                 findings: list[AssessmentFinding]):
        self.app = application
        self.findings = findings
        self.generated_at = datetime.now().strftime("%B %d, %Y")

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC ENTRY — called by assess_trademark_application()
    # ─────────────────────────────────────────────────────────────────────────

    def generate_full_report(self) -> str:
        blocks = [
            self._header(),
            self._application_summary(),
            self._overall_status(),
            self._key_findings(),
            self._classwise_evaluation(),
            self._critical_observations(),
            self._final_recommendation(),
            self._footer(),
        ]
        return "\n".join(b for b in blocks if b.strip())

    # ─────────────────────────────────────────────────────────────────────────
    # 1. HEADER
    # ─────────────────────────────────────────────────────────────────────────

    def _header(self) -> str:
        line = "─" * 70
        return (
            f"\n{line}\n"
            f"  TRADEMARK CLASSIFICATION ASSESSMENT\n"
            f"  TMEP Chapter 1400  |  November 2025 Edition\n"
            f"  Prepared: {self.generated_at}\n"
            f"{line}"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 2. APPLICATION SUMMARY
    # ─────────────────────────────────────────────────────────────────────────

    def _application_summary(self) -> str:
        from nice_classification_db import get_class_info
        app = self.app

        classes_str = "  ".join(
            f"Class {c.class_number} ({get_class_info(c.class_number)['title'] if get_class_info(c.class_number) else '?'})"
            for c in sorted(app.classes, key=lambda x: x.class_number)
        )

        lines = [
            "\nAPPLICATION SUMMARY",
            f"  Applicant        :  {app.applicant_name or '—'}",
            f"  Mark             :  {app.mark_text or '—'}",
            f"  Serial Number    :  {app.application_serial or 'Not yet assigned'}",
            f"  Filing Date      :  {app.filing_date or '—'}",
            f"  Filing Basis     :  {app.filing_type}",
            f"  Classes Filed    :  {classes_str}",
        ]

        # Only show fee line if there is a mismatch
        unique_count = len(set(c.class_number for c in app.classes))
        if app.fees_paid_count > 0 and app.fees_paid_count != unique_count:
            lines.append(
                f"  Fees             :  {app.fees_paid_count} paid / "
                f"{unique_count} required  ⚠ MISMATCH"
            )

        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. OVERALL STATUS
    # ─────────────────────────────────────────────────────────────────────────

    def _overall_status(self) -> str:
        errors   = sum(1 for f in self.findings if f.severity == "ERROR")
        warnings = sum(1 for f in self.findings if f.severity == "WARNING")

        if errors:
            verdict = "REQUIRES CORRECTION"
            note    = f"{errors} mandatory issue(s) must be resolved before registration can proceed."
        elif warnings:
            verdict = "REVIEW RECOMMENDED"
            note    = f"{warnings} advisory issue(s) identified. Address before submission."
        else:
            verdict = "COMPLIANT"
            note    = "No classification errors detected. Application may proceed."

        return (
            f"\nOVERALL STATUS\n"
            f"  {verdict}\n"
            f"  {note}"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 4. KEY FINDINGS  (errors + warnings only, grouped by legal topic)
    # ─────────────────────────────────────────────────────────────────────────

    def _key_findings(self) -> str:
        actionable = [f for f in self.findings
                      if f.severity in ("ERROR", "WARNING")]
        if not actionable:
            return "\nKEY FINDINGS\n  No issues requiring action."

        lines = ["\nKEY FINDINGS"]
        seen = set()

        for f in actionable:
            # Deduplicate near-identical messages
            key = (f.tmep_section, f.severity, f.class_number)
            if key in seen:
                continue
            seen.add(key)

            sym   = self._SEV[f.severity]
            label = self._SECTION_LABELS.get(f.tmep_section, f.tmep_section)
            cls   = f"Class {f.class_number} — " if f.class_number > 0 else ""

            # One-line summary: symbol + section + class + concise issue
            issue = self._condense(f.finding, 110)
            lines.append(f"  {sym} [{label}]  {cls}{issue}")
            # Action on next line, indented
            action = self._condense(f.recommendation, 110)
            lines.append(f"      → {action}")

        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. CLASS-WISE EVALUATION
    # ─────────────────────────────────────────────────────────────────────────

    def _classwise_evaluation(self) -> str:
        from nice_classification_db import get_class_info
        lines = ["\nCLASS-WISE EVALUATION"]

        for cls_entry in sorted(self.app.classes, key=lambda x: x.class_number):
            info     = get_class_info(cls_entry.class_number)
            title    = info["title"] if info else "Unknown"
            category = info["category"] if info else "?"

            cls_findings = [f for f in self.findings
                            if f.class_number == cls_entry.class_number]
            errors   = sum(1 for f in cls_findings if f.severity == "ERROR")
            warnings = sum(1 for f in cls_findings if f.severity == "WARNING")

            if errors:
                status = f"■ ERRORS ({errors})"
            elif warnings:
                status = f"▲ WARNINGS ({warnings})"
            else:
                status = "✓ Clear"

            lines.append(
                f"\n  Class {cls_entry.class_number}  {title}  [{category}]"
                f"  —  {status}"
            )
            lines.append(
                f"  Identification: "
                f"{self._condense(cls_entry.identification, 100)}"
            )
            lines.append(
                f"  Specimen:  {cls_entry.specimen_type or 'Not provided'}"
                f"   |  Basis: {cls_entry.filing_basis}"
            )

            # Surface only the highest-severity issue per class (not all noise)
            top = self._top_finding(cls_findings)
            if top:
                lines.append(f"  Issue:  {self._condense(top.finding, 110)}")

        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # 6. CRITICAL OBSERVATIONS  (legal notes that cross all classes)
    # ─────────────────────────────────────────────────────────────────────────

    def _critical_observations(self) -> str:
        # Surface only non-redundant INFO findings with legal weight
        legal_sections = {
            "§1401.07", "§1401.08", "§1401.11",
            "§1401.13", "§1401.14", "§1401.15"
        }
        notable = [
            f for f in self.findings
            if f.severity in ("ERROR", "WARNING", "INFO")
            and f.tmep_section in legal_sections
        ]

        if not notable:
            return ""

        lines = ["\nCRITICAL OBSERVATIONS"]
        seen_text = set()
        for f in notable:
            short = self._condense(f.finding, 120)
            if short in seen_text:
                continue
            seen_text.add(short)
            label = self._SECTION_LABELS.get(f.tmep_section, f.tmep_section)
            lines.append(f"  [{label}]  {short}")

        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # 7. FINAL RECOMMENDATION
    # ─────────────────────────────────────────────────────────────────────────

    def _final_recommendation(self) -> str:
        errors   = [f for f in self.findings if f.severity == "ERROR"]
        warnings = [f for f in self.findings if f.severity == "WARNING"]

        lines = ["\nFINAL RECOMMENDATION"]

        if not errors and not warnings:
            lines.append(
                "  The application meets classification requirements under TMEP §1401.\n"
                "  Proceed to examination. No corrective action required at this stage."
            )
            return "\n".join(lines)

        if errors:
            lines.append("  The following corrections are mandatory before this application")
            lines.append("  can proceed to registration:\n")
            for i, e in enumerate(errors[:6], 1):   # cap at 6 for brevity
                label = self._SECTION_LABELS.get(e.tmep_section, e.tmep_section)
                cls   = f"Class {e.class_number}: " if e.class_number > 0 else ""
                lines.append(
                    f"  {i}. [{label}]  {cls}"
                    f"{self._condense(e.recommendation, 100)}"
                )
            if len(errors) > 6:
                lines.append(f"     ... and {len(errors) - 6} additional error(s) — see Key Findings.")

        if warnings:
            lines.append(
                f"\n  {len(warnings)} advisory item(s) should be reviewed prior to submission. "
                "These do not block registration but may cause delays."
            )

        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # 8. FOOTER
    # ─────────────────────────────────────────────────────────────────────────

    def _footer(self) -> str:
        return (
            "\n" + "─" * 70 + "\n"
            "  This assessment is generated under TMEP November 2025 Edition.\n"
            "  It does not constitute legal advice. Consult a trademark attorney\n"
            "  for representation before the USPTO.\n"
            "  Reference: https://tmep.uspto.gov  |  https://idm.uspto.gov\n"
            + "─" * 70
        )

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _condense(text: str, limit: int) -> str:
        """Trim to limit chars, ending at a word boundary."""
        text = text.replace("\n", " ").strip()
        if len(text) <= limit:
            return text
        trimmed = text[:limit].rsplit(" ", 1)[0]
        return trimmed + "…"

    @staticmethod
    def _top_finding(findings: list) -> AssessmentFinding | None:
        """Return the single most severe finding from a list."""
        order = {"ERROR": 0, "WARNING": 1, "INFO": 2, "OK": 3}
        actionable = [f for f in findings if f.severity in ("ERROR", "WARNING")]
        if not actionable:
            return None
        return sorted(actionable, key=lambda x: order.get(x.severity, 9))[0]


# """
# TMEP 1401 ASSESSMENT REPORT GENERATOR
# ======================================
# Generates a formatted, structured report from AssessmentFinding objects.
# Includes summary, per-section findings, severity breakdown, and action items.
# """

# from datetime import datetime
# from tmep_1401_assessor import AssessmentFinding, TrademarkApplication


# # ═══════════════════════════════════════════════════════════════════════════════
# # REPORT GENERATOR
# # ═══════════════════════════════════════════════════════════════════════════════

# class TMEP1401ReportGenerator:

#     SEVERITY_SYMBOLS = {
#         "ERROR":   "🔴 ERROR",
#         "WARNING": "🟡 WARNING",
#         "INFO":    "🔵 INFO",
#         "OK":      "✅ OK"
#     }

#     SEVERITY_ORDER = {"ERROR": 0, "WARNING": 1, "INFO": 2, "OK": 3}

#     SECTION_TITLES = {
#         "§1401.01": "Statutory Authority",
#         "§1401.02": "International Trademark Classification Adopted",
#         "§1401.03": "Designation of Class",
#         "§1401.04": "Classification Determines Number of Fees",
#         "§1401.05": "Criteria on Which International Classification Is Based",
#         "§1401.06": "Specimen(s) as Related to Classification",
#         "§1401.07": "Specimen Discloses Special Characteristics",
#         "§1401.08": "Classification and the Identification of Goods and Services",
#         "§1401.09": "Implementation of Changes to the Nice Agreement",
#         "§1401.10": "Effective Date of Changes to USPTO ID Manual",
#         "§1401.11": "Changes Based on Restructuring of Class 42 (8th Edition)",
#         "§1401.12": "General Summary of Major Changes (9th Edition)",
#         "§1401.13": "General Summary of Major Changes (10th Edition)",
#         "§1401.14": "General Summary of Major Changes (11th Edition)",
#         "§1401.15": "General Summary of Major Changes (12th Edition — Current)",
#     }

#     def __init__(self, application: TrademarkApplication,
#                  findings: list[AssessmentFinding]):
#         self.app = application
#         self.findings = findings
#         self.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#     def generate_full_report(self) -> str:
#         """Generate the complete formatted assessment report."""
#         lines = []
#         lines.append(self._header())
#         lines.append(self._application_summary())
#         lines.append(self._severity_dashboard())
#         lines.append(self._findings_by_section())
#         lines.append(self._action_items())
#         lines.append(self._class_summary_table())
#         lines.append(self._footer())
#         return "\n".join(lines)

#     # ─────────────────────────────────────────────────────────────────────────
#     # HEADER
#     # ─────────────────────────────────────────────────────────────────────────

#     def _header(self) -> str:
#         border = "═" * 90
#         return f"""
# {border}
#   TRADEMARK APPLICATION ASSESSMENT REPORT
#   TMEP CHAPTER 1400 — PILLAR 1: CLASSIFICATION (§1401.01–§1401.15)
#   Based on: TMEP November 2025 Edition | 12th Nice Agreement Edition
#   Generated: {self.generated_at}
# {border}"""

#     # ─────────────────────────────────────────────────────────────────────────
#     # APPLICATION SUMMARY
#     # ─────────────────────────────────────────────────────────────────────────

#     def _application_summary(self) -> str:
#         app = self.app
#         classes_str = ", ".join(
#             f"Class {c.class_number}" for c in sorted(app.classes, key=lambda x: x.class_number)
#         )
#         lines = [
#             "\n" + "─" * 90,
#             "  📋 APPLICATION OVERVIEW",
#             "─" * 90,
#             f"  Applicant Name        : {app.applicant_name or '(Not specified)'}",
#             f"  Trademark/Mark        : {app.mark_text or '(Not specified)'}",
#             f"  Mark Type             : {app.mark_type}",
#             f"  Serial Number         : {app.application_serial or '(Not assigned)'}",
#             f"  Filing Date           : {app.filing_date or '(Not specified)'}",
#             f"  Filing Type           : {app.filing_type}",
#             f"  Nice Edition Claimed  : {app.nice_edition_claimed}",
#             f"  Classes Filed         : {classes_str}",
#             f"  Total Classes         : {len(set(c.class_number for c in app.classes))}",
#             f"  Fees Paid Count       : {app.fees_paid_count}",
#             f"  Multi-Class App       : {'Yes' if app.is_multi_class else 'No'}",
#             "",
#             "  CLASSES BREAKDOWN:",
#         ]

#         from nice_classification_db import get_class_info
#         for cls_entry in sorted(app.classes, key=lambda x: x.class_number):
#             class_info = get_class_info(cls_entry.class_number)
#             title = class_info["title"] if class_info else "Unknown"
#             category = class_info["category"] if class_info else "?"
#             lines.append(f"    • Class {cls_entry.class_number:02d} [{category:8s}] {title}")
#             lines.append(f"         ID: {cls_entry.identification[:80]}{'...' if len(cls_entry.identification) > 80 else ''}")
#             lines.append(f"         Specimen: {cls_entry.specimen_type or 'None provided'}")
#             lines.append(f"         Filing Basis: {cls_entry.filing_basis}")

#         return "\n".join(lines)

#     # ─────────────────────────────────────────────────────────────────────────
#     # SEVERITY DASHBOARD
#     # ─────────────────────────────────────────────────────────────────────────

#     def _severity_dashboard(self) -> str:
#         counts = {"ERROR": 0, "WARNING": 0, "INFO": 0, "OK": 0}
#         for f in self.findings:
#             counts[f.severity] = counts.get(f.severity, 0) + 1

#         total = len(self.findings)
#         errors = counts["ERROR"]
#         warnings = counts["WARNING"]

#         # Determine overall status
#         if errors > 0:
#             overall = "🔴 REQUIRES CORRECTION — Errors must be resolved before registration"
#         elif warnings > 0:
#             overall = "🟡 REVIEW NEEDED — Warnings should be addressed"
#         else:
#             overall = "🟢 CLASSIFICATION APPEARS COMPLIANT"

#         lines = [
#             "\n" + "─" * 90,
#             "  📊 ASSESSMENT DASHBOARD",
#             "─" * 90,
#             f"  Overall Status : {overall}",
#             f"  Total Findings : {total}",
#             f"  🔴 Errors      : {counts['ERROR']}  (require mandatory correction)",
#             f"  🟡 Warnings    : {counts['WARNING']}  (should be reviewed/resolved)",
#             f"  🔵 Info Notes  : {counts['INFO']}  (informational — no action required)",
#             f"  ✅ OK          : {counts['OK']}  (compliant — no issues)",
#         ]
#         return "\n".join(lines)

#     # ─────────────────────────────────────────────────────────────────────────
#     # FINDINGS BY SECTION
#     # ─────────────────────────────────────────────────────────────────────────

#     def _findings_by_section(self) -> str:
#         lines = [
#             "\n" + "─" * 90,
#             "  📑 DETAILED FINDINGS BY TMEP SECTION",
#             "─" * 90,
#         ]

#         # Group findings by section
#         sections_order = [
#             "§1401.01", "§1401.02", "§1401.03", "§1401.04", "§1401.05",
#             "§1401.06", "§1401.07", "§1401.08", "§1401.09", "§1401.10",
#             "§1401.11", "§1401.12", "§1401.13", "§1401.14", "§1401.15"
#         ]

#         for section in sections_order:
#             section_findings = [f for f in self.findings if f.tmep_section == section]
#             if not section_findings:
#                 continue

#             title = self.SECTION_TITLES.get(section, section)
#             lines.append(f"\n  ┌{'─'*86}┐")
#             lines.append(f"  │  {section} — {title}")
#             lines.append(f"  └{'─'*86}┘")

#             # Sort by severity within section
#             section_findings.sort(key=lambda x: self.SEVERITY_ORDER.get(x.severity, 99))

#             for i, finding in enumerate(section_findings, 1):
#                 sym = self.SEVERITY_SYMBOLS.get(finding.severity, finding.severity)
#                 class_label = f"[Class {finding.class_number:02d}]" if finding.class_number > 0 else "[Application]"

#                 lines.append(f"\n  [{i}] {sym} — {class_label}")
#                 lines.append(f"      Item       : {finding.item}")

#                 # Handle multi-line finding text
#                 finding_text = finding.finding
#                 finding_lines = finding_text.split("\n")
#                 lines.append(f"      Finding    : {finding_lines[0]}")
#                 for fl in finding_lines[1:]:
#                     lines.append(f"                   {fl}")

#                 lines.append(f"      Action     : {finding.recommendation}")

#         return "\n".join(lines)

#     # ─────────────────────────────────────────────────────────────────────────
#     # ACTION ITEMS (Errors and Warnings only)
#     # ─────────────────────────────────────────────────────────────────────────

#     def _action_items(self) -> str:
#         errors = [f for f in self.findings if f.severity == "ERROR"]
#         warnings = [f for f in self.findings if f.severity == "WARNING"]

#         if not errors and not warnings:
#             return (
#                 "\n" + "─" * 90 + "\n"
#                 "  ✅ ACTION ITEMS\n"
#                 "─" * 90 + "\n"
#                 "  No errors or warnings found. No mandatory action items.\n"
#             )

#         lines = [
#             "\n" + "─" * 90,
#             "  🚨 ACTION ITEMS REQUIRED",
#             "─" * 90,
#         ]

#         if errors:
#             lines.append("\n  MANDATORY CORRECTIONS (Errors — Must Resolve):")
#             for i, e in enumerate(errors, 1):
#                 class_label = f"Class {e.class_number}" if e.class_number > 0 else "Application-level"
#                 lines.append(f"    {i}. [{e.tmep_section}] {class_label}: {e.item}")
#                 lines.append(f"       → {e.recommendation}")

#         if warnings:
#             lines.append("\n  RECOMMENDED REVIEWS (Warnings — Should Resolve):")
#             for i, w in enumerate(warnings, 1):
#                 class_label = f"Class {w.class_number}" if w.class_number > 0 else "Application-level"
#                 lines.append(f"    {i}. [{w.tmep_section}] {class_label}: {w.item}")
#                 lines.append(f"       → {w.recommendation}")

#         return "\n".join(lines)

#     # ─────────────────────────────────────────────────────────────────────────
#     # CLASS SUMMARY TABLE
#     # ─────────────────────────────────────────────────────────────────────────

#     def _class_summary_table(self) -> str:
#         from nice_classification_db import get_class_info

#         lines = [
#             "\n" + "─" * 90,
#             "  📊 PER-CLASS ASSESSMENT SUMMARY",
#             "─" * 90,
#             f"  {'Class':7} {'Title':30} {'Category':10} {'Status':12} {'Issues'}",
#             "  " + "-" * 85,
#         ]

#         for cls_entry in sorted(self.app.classes, key=lambda x: x.class_number):
#             class_info = get_class_info(cls_entry.class_number)
#             title = (class_info["title"][:28] + "..") if class_info and len(class_info["title"]) > 30 else (class_info["title"] if class_info else "Unknown")
#             category = class_info["category"] if class_info else "?"

#             class_findings = [f for f in self.findings
#                              if f.class_number == cls_entry.class_number]
#             class_errors = sum(1 for f in class_findings if f.severity == "ERROR")
#             class_warnings = sum(1 for f in class_findings if f.severity == "WARNING")

#             if class_errors > 0:
#                 status = "🔴 ERRORS"
#             elif class_warnings > 0:
#                 status = "🟡 WARNINGS"
#             else:
#                 status = "✅ OK"

#             issues = []
#             if class_errors > 0:
#                 issues.append(f"{class_errors} error(s)")
#             if class_warnings > 0:
#                 issues.append(f"{class_warnings} warning(s)")
#             issues_str = ", ".join(issues) if issues else "None"

#             lines.append(f"  Class {cls_entry.class_number:02d}  {title:30} {category:10} {status:12} {issues_str}")

#         return "\n".join(lines)

#     # ─────────────────────────────────────────────────────────────────────────
#     # FOOTER
#     # ─────────────────────────────────────────────────────────────────────────

#     def _footer(self) -> str:
#         border = "═" * 90
#         return f"""
# {border}
#   LEGAL DISCLAIMER
#   This assessment is generated for informational purposes based on TMEP Chapter 1400
#   (November 2025 Edition) and the 12th Edition of the Nice Agreement. It does not
#   constitute legal advice and should not be used as a substitute for consultation
#   with a qualified trademark attorney. For official USPTO guidance, refer to:
#     • TMEP: https://tmep.uspto.gov
#     • ID Manual: https://idm.uspto.gov
#     • USPTO: https://www.uspto.gov
# {border}
#   END OF TMEP §1401 CLASSIFICATION ASSESSMENT REPORT
# {border}
# """
