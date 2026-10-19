import os
import platform
from datetime import datetime

import pandas as pd
import streamlit as st

import ai
import checks
import db
import demo
import report
import ui
from risk import STATUSES, compliance_percent

st.set_page_config(page_title=ui.APP_NAME, layout="wide", initial_sidebar_state="expanded")
db.init_db()
ui.md(st, ui.CSS)


# ------------------------------------------------------------------ helpers
def host_info():
    return {"hostname": platform.node(), "os": f"{platform.system()} {platform.release()}",
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M")}


def last_scan(rows):
    times = [r["updated_at"] for r in rows if r["source"] == "automated" and r["updated_at"]]
    return max(times).replace("T", " ") if times else "never"


def show_msgs():
    """Messages from the last action are shown once, then cleared."""
    for kind, text in st.session_state.pop("msgs", []):
        getattr(st, kind)(text)


def run_automated():
    try:
        results = checks.run_all_checks()
    except checks.CheckError as e:
        st.session_state["msgs"] = [("error", str(e))]
        return
    msgs, ok = [], 0
    for r in results:
        if r.status == "ERROR":
            msgs.append(("warning", f"**{r.control_id}** could not be checked: {r.evidence}"))
        else:
            db.save_assessment(r.control_id, r.status, r.evidence, source="automated")
            ok += 1
    msgs.insert(0, ("success", f"{ok} of {len(results)} automated checks completed."))
    st.session_state["msgs"] = msgs


# ------------------------------------------------------------------ pages
def page_start():
    from controls import CONTROLS
    ui.md(st, ui.page_header("Start here", "What this tool does, how to use it, and why these controls"))
    show_msgs()
    ui.md(st, ui.prose_card("What this tool does", [
        "Companies write security rules, but a rule on paper proves nothing. This tool checks whether the rules are "
        "actually followed on a real computer.",
        "It takes security controls from <b>NIST SP 800-53</b> (a well-known catalogue of security rules), looks at the "
        "matching <b>settings on this Windows PC</b>, marks each control <b>Pass, Partial or Fail</b>, scores how risky "
        "each gap is, and writes a PDF report with fixes.",
    ]))
    st.write("")
    st.markdown("**How to use it**")
    s = st.columns(4)
    ui.md(s[0], ui.step(1, "Run the checks", "Click <b>Run automated checks</b> in the sidebar. The tool reads this PC's real "
                           "settings. Open it as Administrator for full coverage. No Windows? Click <b>Load demo data</b>."))
    ui.md(s[1], ui.step(2, "Answer 2 questions", "Open <b>Assessment</b> and scroll to <b>Manual controls</b>. "
                           "Two controls can't be read from the PC, so you answer them yourself."))
    ui.md(s[2], ui.step(3, "Read the results", "<b>Summary</b> shows your score and biggest risks. <b>Assessment</b> shows each "
                           "rule, what was checked, what was found and how to fix it."))
    ui.md(s[3], ui.step(4, "Fix, re-run, report", "Change a setting in Windows, run the checks again and watch Fail "
                           "become Pass. Then download the PDF from <b>Report</b>."))
    st.write("")
    ui.md(st, ui.prose_card("Why these 10 controls?", [
        "NIST SP 800-53 has hundreds of controls in 20 families, written for whole organisations rather than one PC. "
        "Checking all of them isn't realistic, so this tool uses a <b>starter set of 10</b>.",
        "They were picked because they (1) cover the basics of a secure Windows machine: who can get in, what is recorded, "
        "what blocks attacks, and safe settings; (2) can be measured from a real setting; and (3) appear in common Windows "
        "hardening guides such as the CIS Benchmarks.",
        "So this is a focused slice, not a full NIST assessment. Thresholds like 12-character passwords come from common "
        "hardening practice, not from NIST itself.",
    ]))
    st.write("")
    ui.md(st, ui.controls_overview(CONTROLS))
    st.write("")
    ui.md(st, ui.prose_card("What are the manual controls?", [
        "<b>AC-1</b> (a written access policy) and <b>IA-2</b> (multi-factor sign-in) can't be proven by reading a Windows "
        "setting. A policy is a document, and MFA depends on how accounts are set up. Real assessments mix automated checks "
        "with human review, and these two are the human part.",
        "<b>What you do:</b> open <b>Assessment</b>, scroll to Manual controls, read the question, pick Pass, Partial or Fail "
        "using the guide shown, add one line of evidence and press Save. You can skip them. They then show as Not assessed "
        "and are left out of the score.",
    ]))


def page_summary():
    rows = db.get_assessments()
    assessed = [r for r in rows if r["status"] != "NOT ASSESSED"]
    ui.md(st, ui.page_header("Summary", "How well this system meets the selected NIST controls"))
    show_msgs()
    if not assessed:
        ui.md(st, '<div class="empty"><b>No results yet.</b> New here? Open <b>Start here</b> first. Quick version:<br>'
                  '1. Click <b>Run automated checks</b> in the sidebar (Windows, as Administrator), '
                  'or <b>Load demo data</b> to explore.<br>'
                  '2. Open <b>Assessment</b> to see each rule, what was checked and what was found.<br>'
                  '3. Open <b>Report</b> to download a PDF.</div>')
        return
    pct = compliance_percent(rows)
    count = lambda s: sum(1 for r in rows if r["status"] == s)
    k = st.columns(4)
    ui.md(k[0], ui.kpi("Compliance", f"{pct:.0f}%", ui.score_color(pct), f"{len(assessed)} of {len(rows)} controls assessed"))
    ui.md(k[1], ui.kpi("Passed", count("PASS"), ui.STATUS_COLOR["PASS"], "requirement met"))
    ui.md(k[2], ui.kpi("Partial", count("PARTIAL"), ui.STATUS_COLOR["PARTIAL"], "partly met"))
    ui.md(k[3], ui.kpi("Failed", count("FAIL"), ui.STATUS_COLOR["FAIL"], "not met"))
    st.write("")
    a, b = st.columns(2)
    ui.md(a, ui.card("Top risks (score out of 25)", ui.top_risks(rows), mh=250))
    ui.md(b, ui.card("Results", ui.breakdown(rows), mh=250))
    st.caption("Compliance counts Pass as 100%, Partial as 50% and Fail as 0%, averaged over assessed controls. "
               "Risk = likelihood × impact, scaled by result.")


def page_assessment():
    rows = db.get_assessments()
    ui.md(st, ui.page_header("Assessment", "Each row links one NIST control to the Windows setting we check"))
    show_msgs()
    only = st.toggle("Show only problems (failed or partial)", key="only_problems")
    shown = [r for r in rows if r["status"] in ("FAIL", "PARTIAL")] if only else rows
    if shown:
        ui.md(st, ui.assessment_table(shown))
    else:
        ui.md(st, '<div class="empty">No failed or partial controls.</div>')

    manual = [r for r in rows if not r["auto"]]
    st.write("")
    st.subheader("Manual controls", anchor=False)
    st.caption("These two can't be read from a Windows setting. Read the question, pick a result using the guide, "
               "add one line of evidence and press Save. Skipping them is fine: they stay Not assessed and are left out of the score.")
    for r in manual:
        with st.container(border=True):
            ui.md(st, ui.manual_guide(r))
            with st.form(f"form_{r['id']}", border=False):
                c1, c2 = st.columns([1, 3])
                status = c1.selectbox("Result", STATUSES, index=STATUSES.index(r["status"]))
                evidence = c2.text_input("Evidence / note", value=r["evidence"])
                if st.form_submit_button("Save"):
                    db.save_assessment(r["id"], status, evidence, source="manual")
                    st.session_state["msgs"] = [("success", f"{r['id']} saved.")]
                    st.rerun()

    with st.expander("Change history"):
        hist = db.get_history()
        if not hist:
            st.caption("Nothing yet. Every saved result is logged here, so you can show a control moving from Fail to Pass.")
        else:
            pick = st.selectbox("Control", ["All"] + sorted({h["control_id"] for h in hist}), key="hist_filter")
            st.dataframe(pd.DataFrame([h for h in hist if pick == "All" or h["control_id"] == pick]), hide_index=True)


def page_report():
    rows = db.get_assessments()
    ui.md(st, ui.page_header("Report", "Write the findings summary, then download a PDF"))
    show_msgs()
    ui.md(st, ui.card("Step 1 · Written summary (optional)",
                      "Turns the recorded evidence into a plain-English summary and a finding for each gap. "
                      "It uses AI if you add an API key, otherwise a built-in template. Either way it only uses your recorded evidence."))
    with st.expander("API key (optional)"):
        st.text_input("Anthropic API key", type="password", key="api_key", value=os.getenv("ANTHROPIC_API_KEY", ""),
                      help="Held only in this browser session.")
    if st.button("Generate written summary", key="btn_ai"):
        with st.spinner("Writing..."):
            analysis, note = ai.analyze(rows, st.session_state.get("api_key") or None)
        db.save_ai_analysis(analysis)
        st.session_state["msgs"] = [("info", note)]
        st.rerun()
    saved = db.get_ai_analysis()
    if saved:
        ui.md(st, ui.card("Summary", f'<div style="font-size:.95rem;line-height:1.55">{ui.e(saved["summary"])}</div>'
                          f'<div class="sub" style="margin-top:8px">Generated {ui.e(saved["generated_at"])} · '
                          f'source: {ui.e(saved["model"])}</div>'))
        with st.expander("Preview findings"):
            for r in ai.get_gaps(rows):
                if r["id"] in saved["findings"]:
                    ui.md(st, ui.gap_card(r, saved["findings"][r["id"]]))
        st.caption("Generate again after changing results so the text matches.")

    st.write("")
    ui.md(st, ui.card("Step 2 · PDF report", "Includes the summary, every control result, each gap with evidence and "
                      "recommendation, and the methodology."))
    if st.button("Generate PDF report", key="btn_pdf", type="primary"):
        st.session_state["pdf"] = report.build_report(rows, ai=db.get_ai_analysis(), host=host_info())
        st.session_state["pdf_time"] = datetime.now().strftime("%Y%m%d_%H%M")
    if "pdf" in st.session_state:
        st.download_button("Download report (PDF)", data=st.session_state["pdf"],
                           file_name=f"security_assessment_{st.session_state['pdf_time']}.pdf",
                           mime="application/pdf")


# ------------------------------------------------------------------ navigation + sidebar
nav = st.navigation([
    st.Page(page_start, title="Start here", default=True),
    st.Page(page_summary, title="Summary"),
    st.Page(page_assessment, title="Assessment"),
    st.Page(page_report, title="Report"),
])

with st.sidebar:
    ui.md(st, '<div class="sbl" style="margin-top:14px">Scan</div>')
    on_windows = checks.is_windows()
    if st.button("Run automated checks", key="btn_run", type="primary", disabled=not on_windows):
        with st.spinner("Inspecting system configuration..."):
            run_automated()
        st.rerun()
    if st.button("Load demo data", key="btn_demo"):
        st.session_state["msgs"] = [("info", "Demo data loaded (sample results, not from this system).")]
        demo.load_demo()
        st.rerun()
    if st.button("Reset assessments", key="btn_reset"):
        db.reset_all()
        for k in ("msgs", "pdf", "pdf_time"):
            st.session_state.pop(k, None)
        st.rerun()
    if not on_windows:
        st.caption("Automated checks need Windows.")
    elif not checks.is_admin():
        st.caption("Not running as Administrator: audit policy, password complexity and SMBv1 can't be fully verified.")
    ui.md(st, f'<div class="hostcard" style="margin-top:18px">{ui.e(platform.node())}<br>'
              f'{platform.system()} {platform.release()} · Admin: {"yes" if checks.is_admin() else "no"}</div>')

ui.md(st, ui.topbar(platform.node(), last_scan(db.get_assessments())))
nav.run()
