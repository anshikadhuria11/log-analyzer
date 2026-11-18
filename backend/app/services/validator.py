# Validator service – checks that cited lines in the report match the original input.
# It can operate in normal mode (fix texts) or validation‑only mode (used for raw baseline).

from typing import List, Tuple

from ..schemas import AnalysisReport, EvidenceItem, TimelineItem, ValidationInfo


def _normalize(text: str) -> str:
    # Collapse whitespace for fuzzy matching
    return " ".join(text.strip().split())


def validate_report(report: AnalysisReport, raw_lines: List[str], validate_only: bool = False) -> Tuple[AnalysisReport, ValidationInfo]:
    """Validate citation line numbers and texts.

    * `raw_lines` is a list where index = line_no - 1.
    * Returns a possibly‑modified report and a ValidationInfo object.
    * In normal mode, mismatched evidence `text` is replaced with the true line content.
      Invalid evidence items are dropped.
    * In `validate_only` mode the report is left untouched and only counts are returned.
    """
    cited = 0
    valid = 0
    invalid = 0
    corrected = 0
    dropped = 0
    new_evidence: List[EvidenceItem] = []
    for ev in report.evidence:
        cited += 1
        line_no = ev.line_number
        if line_no <= 0 or line_no > len(raw_lines):
            invalid += 1
            dropped += 1
            continue
        real_text = raw_lines[line_no - 1]
        if _normalize(ev.text) == _normalize(real_text):
            valid += 1
            new_evidence.append(ev)
        else:
            # mismatch – in normal mode we fix the text, otherwise count as invalid
            if not validate_only:
                ev.text = real_text
                corrected += 1
                valid += 1
                new_evidence.append(ev)
            else:
                invalid += 1
    # Timeline line number validation
    for tl in report.timeline:
        if tl.line_number is not None:
            if tl.line_number <= 0 or tl.line_number > len(raw_lines):
                tl.line_number = None
    # Build ValidationInfo
    val_info = ValidationInfo(
        cited=cited,
        valid=valid,
        invalid=invalid,
        retried=False,
        corrected=corrected,
        dropped=dropped,
    )
    if not validate_only:
        report.evidence = new_evidence
    return report, val_info
