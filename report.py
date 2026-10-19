"""PDF compliance report (ReportLab)."""
import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from risk import LEVELS, compliance_percent

STATUS_COLOR = {"PASS": "#2e7d32", "PARTIAL": "#b26a00", "FAIL": "#c62828", "NOT ASSESSED": "#757575"}
LEVEL_COLOR = {"Critical": "#b71c1c", "High": "#e64a19", "Medium": "#b26a00", "Low": "#2e7d32",
               "None": "#2e7d32", "N/A": "#757575"}
NAVY = colors.HexColor("#1f2d4d")


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(18 * mm, 10 * mm, "Security Control & Compliance Assessment Platform")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _colored(text, color):
    return f'<font color="{color}"><b>{escape(str(text))}</b></font>'


def build_report(rows, ai=None, host=None) -> bytes:
    host = host or {}
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=NAVY, fontSize=22, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=NAVY, spaceBefore=12, spaceAfter=6)
    body = ParagraphStyle("body", parent=ss["BodyText"], fontSize=9.5, leading=13)
    cell = ParagraphStyle("cell", parent=ss["BodyText"], fontSize=8.5, leading=11)
    small = ParagraphStyle("small", parent=body, fontSize=8, textColor=colors.grey)

    assessed = [r for r in rows if r["status"] != "NOT ASSESSED"]
    count = lambda s: sum(1 for r in rows if r["status"] == s)
    gaps = sorted([r for r in rows if r["status"] in ("FAIL", "PARTIAL")], key=lambda r: r["risk_score"], reverse=True)
    pct = compliance_percent(rows)

    story = [Paragraph("Security Control Assessment Report", h1),
             Paragraph("Framework: NIST SP 800-53 (scoped subset)", body),
             Paragraph(escape(f"Host: {host.get('hostname', 'n/a')} | OS: {host.get('os', 'n/a')} | "
                              f"Generated: {host.get('generated', datetime.now().strftime('%Y-%m-%d %H:%M'))}"), small),
             Spacer(1, 8), Paragraph("Executive Summary", h2)]

    if ai and ai.get("summary"):
        summary = ai["summary"]
    elif gaps:
        summary = (f"{len(assessed)} of {len(rows)} controls were assessed with an overall compliance of {pct}%. "
                   f"{count('FAIL')} failed and {count('PARTIAL')} are partially met. The highest risk is "
                   f"{gaps[0]['id']} ({gaps[0]['name']}), rated {gaps[0]['risk_level']}.")
    else:
        summary = f"{len(assessed)} of {len(rows)} controls were assessed with an overall compliance of {pct}%."
    story.append(Paragraph(escape(summary), body))

    # Key figures
    fig = Table([["Overall compliance", "Assessed", "Passed", "Partial", "Failed"],
                 [f"{pct}%", f"{len(assessed)} / {len(rows)}", count("PASS"), count("PARTIAL"), count("FAIL")]],
                colWidths=[42 * mm, 32 * mm, 28 * mm, 28 * mm, 28 * mm])
    fig.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                             ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9),
                             ("FONTSIZE", (0, 1), (-1, 1), 13), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                             ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [Spacer(1, 10), fig, Paragraph("Risk Distribution", h2)]

    lv = {l: sum(1 for r in rows if r["risk_level"] == l) for l in LEVELS}
    dist = Table([list(lv.keys()), list(lv.values())], colWidths=[32 * mm] * 4)
    dist.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                              ("FONTSIZE", (0, 1), (-1, 1), 13), ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                              ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                              ("TEXTCOLOR", (0, 0), (0, 0), colors.HexColor(LEVEL_COLOR["Critical"])),
                              ("TEXTCOLOR", (1, 0), (1, 0), colors.HexColor(LEVEL_COLOR["High"])),
                              ("TEXTCOLOR", (2, 0), (2, 0), colors.HexColor(LEVEL_COLOR["Medium"])),
                              ("TEXTCOLOR", (3, 0), (3, 0), colors.HexColor(LEVEL_COLOR["Low"])),
                              ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story += [dist, Paragraph("Control Results", h2)]

    data = [["ID", "Control", "Status", "Risk", "Source"]]
    for r in rows:
        risk_txt = "-" if r["risk_score"] is None else f"{r['risk_level']} ({r['risk_score']})"
        data.append([r["id"], Paragraph(escape(r["name"]), cell),
                     Paragraph(_colored(r["status"], STATUS_COLOR[r["status"]]), cell),
                     Paragraph(_colored(risk_txt, LEVEL_COLOR[r["risk_level"]]), cell),
                     r["source"] if r["status"] != "NOT ASSESSED" else "-"])
    t = Table(data, colWidths=[16 * mm, 62 * mm, 30 * mm, 36 * mm, 26 * mm], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f5f9")]),
                           ("BOX", (0, 0), (-1, -1), 0.5, colors.grey), ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey)]))
    story.append(t)

    story.append(Paragraph("Control Gaps and Recommendations", h2))
    if not gaps:
        story.append(Paragraph("No control gaps were identified.", body))
    findings = (ai or {}).get("findings", {})
    for r in gaps:
        f = findings.get(r["id"])
        block = [Paragraph(f"<b>{escape(r['id'])} - {escape(r['name'])}</b> &nbsp; "
                           f"{_colored(r['risk_level'] + ' risk (' + str(r['risk_score']) + '/25)', LEVEL_COLOR[r['risk_level']])} "
                           f"&nbsp; {_colored(r['status'], STATUS_COLOR[r['status']])}", body),
                 Paragraph(f"<b>Requirement:</b> {escape(r['requirement'])}", cell),
                 Paragraph(f"<b>Evidence:</b> {escape(r['evidence'] or 'none recorded')}", cell)]
        if f:
            block.append(Paragraph(f"<b>Finding:</b> {escape(f['finding'])}", cell))
        block.append(Paragraph(f"<b>Recommendation:</b> {escape(f['recommendation'] if f else r['remediation'])}", cell))
        block.append(Spacer(1, 8))
        story.append(KeepTogether(block))

    todo = [r for r in rows if r["status"] == "NOT ASSESSED"]
    if todo:
        story += [Paragraph("Not Yet Assessed", h2),
                  Paragraph(escape(", ".join(f"{r['id']} ({r['name']})" for r in todo)), body)]

    if ai and ai.get("model") == "offline-template":
        ai_note = " Finding wording was generated from a built-in template using the recorded evidence (no AI model was used)."
    elif ai:
        ai_note = (f" AI-assisted wording was generated from the recorded evidence only "
                   f"(model: {escape(ai.get('model', 'n/a'))}); review before relying on it.")
    else:
        ai_note = ""
    story.append(KeepTogether([
        Paragraph("Methodology", h2),
        Paragraph("Each control is scoped to one measurable requirement. Automated controls are validated by "
                  "reading live Windows configuration; others are assessed manually with recorded evidence. "
                  "Risk = Likelihood (1-5) x Impact (1-5), scaled by status: FAIL 100%, PARTIAL 50%, PASS 0%. "
                  "Compliance counts PASS as 100%, PARTIAL as 50% and FAIL as 0% of assessed controls."
                  + ai_note, small)]))

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                      bottomMargin=18 * mm, title="Security Control Assessment Report").build(
        story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
