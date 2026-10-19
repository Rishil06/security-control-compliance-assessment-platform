"""AI-assisted gap analysis.

Uses the Anthropic API when a key is provided; otherwise (or on any failure)
falls back to a deterministic template so the feature always works offline.
The model is told to use ONLY the supplied facts, and its output is validated
against the real control IDs so it cannot invent findings for unknown controls.
"""
import json
import os

from risk import compliance_percent

DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")

SYSTEM = (
    "You are a senior GRC (governance, risk and compliance) analyst. You are given assessed security "
    "control gaps for one system. Use ONLY the facts provided. Do not invent evidence, tools, systems, "
    "versions or incidents that are not in the input. Write clear, professional, plain English. "
    "Return ONLY valid JSON, no markdown fences, in exactly this shape: "
    '{"summary": "2-3 sentence executive summary", "findings": [{"control_id": "AC-7", '
    '"finding": "1-2 sentences: what is wrong and why it matters (business/security impact)", '
    '"recommendation": "1-2 sentences: specific remediation"}]}. '
    "Include exactly one finding per control provided."
)


def get_gaps(rows):
    gaps = [r for r in rows if r["status"] in ("FAIL", "PARTIAL")]
    return sorted(gaps, key=lambda r: r["risk_score"], reverse=True)


def offline_analysis(rows):
    gaps = get_gaps(rows)
    total = sum(1 for r in rows if r["status"] != "NOT ASSESSED")
    if not gaps:
        summary = f"All {total} assessed controls passed. No control gaps were identified."
    else:
        top = gaps[0]
        summary = (f"{len(gaps)} of {total} assessed controls have gaps; overall compliance is "
                   f"{compliance_percent(rows)}%. The highest risk is {top['id']} ({top['name']}), "
                   f"rated {top['risk_level']}. Address the Critical and High items first.")
    findings = {}
    for r in gaps:
        kind = "not met" if r["status"] == "FAIL" else "only partially met"
        findings[r["id"]] = {
            "finding": (f"{r['name']} ({r['id']}) is {kind}, rated {r['risk_level']} risk ({r['risk_score']}/25). "
                        f"{r['why']}"),
            "recommendation": r["remediation"],
        }
    return {"summary": summary, "findings": findings, "model": "offline-template"}


def llm_analysis(rows, api_key, model=DEFAULT_MODEL):
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("The 'anthropic' package is not installed (pip install anthropic).")
    gaps = get_gaps(rows)
    payload = {"overall_compliance_percent": compliance_percent(rows),
               "gaps": [{"control_id": r["id"], "control": r["name"], "requirement": r["requirement"],
                         "status": r["status"], "evidence": r["evidence"], "risk_level": r["risk_level"],
                         "risk_score_out_of_25": r["risk_score"]} for r in gaps]}
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(model=model, max_tokens=2500, system=SYSTEM,
                                 messages=[{"role": "user", "content": json.dumps(payload)}])
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    data = json.loads(text[text.index("{"): text.rindex("}") + 1])

    base = offline_analysis(rows)          # used to fill anything the model omitted
    findings = dict(base["findings"])
    for f in data.get("findings", []):
        cid = f.get("control_id")
        if cid in findings and isinstance(f.get("finding"), str) and isinstance(f.get("recommendation"), str):
            findings[cid] = {"finding": f["finding"].strip(), "recommendation": f["recommendation"].strip()}
    summary = data.get("summary") if isinstance(data.get("summary"), str) else base["summary"]
    return {"summary": summary.strip(), "findings": findings, "model": model}


def analyze(rows, api_key=None):
    """Returns (analysis_dict, note). Never raises; falls back to the offline template."""
    if not get_gaps(rows):
        return offline_analysis(rows), "No gaps to analyze."
    if not api_key:
        return offline_analysis(rows), "No API key set - used the offline template."
    try:
        return llm_analysis(rows, api_key), "Generated with the LLM."
    except Exception as e:
        return offline_analysis(rows), f"LLM call failed ({type(e).__name__}: {e}) - used the offline template."
