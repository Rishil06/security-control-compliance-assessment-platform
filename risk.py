"""Risk engine: Likelihood x Impact, scaled by assessment status."""

STATUSES = ["NOT ASSESSED", "PASS", "PARTIAL", "FAIL"]
STATUS_FACTOR = {"PASS": 0.0, "PARTIAL": 0.5, "FAIL": 1.0}
COMPLIANCE_POINTS = {"PASS": 1.0, "PARTIAL": 0.5, "FAIL": 0.0}
LEVELS = ["Critical", "High", "Medium", "Low"]


def risk_score(status, likelihood, impact):
    """0-25. FAIL counts fully, PARTIAL half, PASS zero. None if not assessed."""
    if status not in STATUS_FACTOR:
        return None
    return round(likelihood * impact * STATUS_FACTOR[status], 1)


def risk_level(score):
    if score is None:
        return "N/A"
    if score == 0:
        return "None"
    if score <= 6:
        return "Low"
    if score <= 12:
        return "Medium"
    if score <= 19:
        return "High"
    return "Critical"


def compliance_percent(rows):
    """PASS=100%, PARTIAL=50%, FAIL=0%. Unassessed controls are excluded."""
    assessed = [r for r in rows if r["status"] in COMPLIANCE_POINTS]
    if not assessed:
        return 0.0
    return round(100 * sum(COMPLIANCE_POINTS[r["status"]] for r in assessed) / len(assessed), 1)
