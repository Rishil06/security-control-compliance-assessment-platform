# Demo script, interview prep and CV text

## 5-minute demo (Windows, run as Administrator)

1. **Setup (before the demo):** deliberately weaken two things so there is something to fix, e.g. turn the **Public firewall profile off** (Windows Security > Firewall) and run `net accounts /lockoutthreshold:0`.
2. **Intro (30s):** "This checks whether security controls from NIST SP 800-53 are actually implemented, scores the risk and reports the gaps."
3. **Run automated checks (60s):** click it. Statuses and evidence fill in automatically. Point out the compliance % and risk counts.
4. **Open a failed control (45s):** Assessment page -> SC-7 row: rule, what we checked, real evidence ("Public profile: OFF"), risk 20/25 Critical, recommendation.
5. **Fix it live (60s):** turn the Public firewall back on, run `net accounts /lockoutthreshold:5`, click **Run automated checks** again. SC-7 and AC-7 flip to PASS, compliance rises. Open **Change history** at the bottom of Assessment to show FAIL -> PASS. This proves the data is live, not mocked.
6. **Manual controls (30s):** scroll to **Manual controls** on Assessment, set AC-1 or IA-2 and add evidence ("MFA not enabled").
7. **AI + report (60s):** Report -> Generate written summary, then Generate PDF -> download and open it.

## Interview Q&A

**Why NIST SP 800-53?** It is a widely used control catalogue with clear IDs and families, so findings map to something auditors recognise. I scoped it to 10 controls.

**How do you turn a control into an automated check?** I define one measurable requirement per control (e.g. SC-7 -> firewall enabled on all profiles), pick a collector (PowerShell/auditpol/secedit), and write an analyzer that maps the raw output to PASS/PARTIAL/FAIL plus evidence. Analyzers are pure functions with unit tests.

**How is risk calculated?** Likelihood x Impact (1-5 each), scaled by status. It is a simple qualitative model; the ratings are analyst judgments I would calibrate against threat data in a real programme.

**What are the limitations?** Single host, point-in-time, simplified controls, size used as a proxy for retention, English-locale assumption for auditpol.

**How did you handle AI safely?** The prompt restricts the model to supplied evidence, output must be JSON and is validated against real control IDs, and there is an offline fallback. A human still reviews the findings.

**How does this connect to your SOC lab?** The SOC lab shows I understand detection technically; this shows I can express requirements as controls, measure them, and report risk. Next step: feed Wazuh evidence into AU-2.

**How would you scale it?** Agent or API-based collection across many hosts, central database, scheduled scans with trend reporting, mapping to CIS/ISO.

## CV text (use only what is built and working)

[Security Control & Compliance Assessment Platform:](https://github.com/Rishil06/REPO_NAME)
NIST SP 800-53 Control Assessment and Risk Scoring

* •Built a GRC automation platform in Python and Streamlit that assesses security controls against NIST SP 800-53 and runs automated checks on a Windows system (firewall, password and lockout policy, audit policy, Defender, UAC/SMBv1). Identified control gaps, calculated likelihood-impact risk scores, and generated AI-assisted remediation recommendations and PDF compliance reports.

Tech stack: Python, Streamlit, SQLite, Pandas, ReportLab, PowerShell, NIST SP 800-53, LLM API

Honesty notes: drop "AI-assisted" and "LLM API" if you only use the offline template; drop PowerShell only if you remove those checks.

## Before you put it on your CV / GitHub

- [ ] Run it on your Windows machine as Administrator; confirm every check returns a sensible result
- [ ] Weaken then fix a setting and confirm FAIL -> PASS
- [ ] Take 3-4 screenshots (dashboard, gap detail, history, PDF) into a `screenshots/` folder and reference them in the README
- [ ] Create the GitHub repo, push (grc.db and keys are git-ignored), update the CV link
