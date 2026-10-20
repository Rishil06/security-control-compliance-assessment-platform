# Security Control & Compliance Assessment Platform

A GRC automation tool that assesses security controls against **NIST SP 800-53**, runs **automated technical checks** on a Windows machine, identifies **control gaps**, calculates **risk scores**, and produces **remediation guidance, AI-assisted analysis and PDF reports**.

```
Framework -> Control -> Assessment (manual / automated) -> Gap -> Risk -> Remediation -> Report
```

## Quick start (Windows)

1. Install Python 3.10+ from python.org (tick "Add python.exe to PATH").
2. Unzip the project, open **PowerShell as Administrator** in the folder, then:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   streamlit run app.py
   ```
   (If activation is blocked: `Set-ExecutionPolicy -Scope Process Bypass`.)
   Or simply right-click `run.bat` -> **Run as administrator**.
3. The app opens at http://localhost:8501. Click **Run automated checks**.

Administrator rights are needed for the audit policy (AU-2), password complexity (IA-5) and SMBv1 (CM-6). Without them those items show a warning or are partially verified; everything else still works.

**Not on Windows?** Click **Load demo data** in the sidebar to explore every feature with sample results.

## Interface

Four pages in a sidebar menu, under a top bar showing the tool name (change `APP_NAME` in `ui.py`):

- **Start here** - what the tool does, how to use it in 4 steps, why these 10 controls, and what the manual controls are.
- **Summary** - compliance %, passed / partial / failed, top risks and a "fix first" hint.
- **Assessment** - one table: Rule | What we checked | What we found | Result | Risk | How to fix. Each row is the NIST-to-Windows mapping. Manual controls (AC-1, IA-2) are recorded in a small form below, and change history is in a collapsible section.
- **Report** - optional written summary (AI or built-in template), then PDF download.

Sidebar buttons: Run automated checks, Load demo data, Reset. Fonts are IBM Plex Sans and Mono, loaded from Google Fonts (falls back to system fonts offline). Colours and fonts live in `ui.py` and `.streamlit/config.toml`.

## Controls and checks

| Control | Requirement (scoped) | How it is assessed |
|---|---|---|
| SC-7 | Firewall enabled on all profiles | `Get-NetFirewallProfile` |
| IA-5 | Min password length >= 12 + complexity | `secedit` (admin) / `net accounts` |
| AC-7 | Lockout after <= 5 failed logons | `secedit` / `net accounts` |
| AU-2 | Logon, account mgmt, process creation audited | `auditpol` (admin) |
| AU-4 | Security log capacity >= 192 MB | `wevtutil gl Security` |
| SI-3 | Defender on, real-time protection, signatures <= 7 days | `Get-MpComputerStatus` |
| CM-6 | UAC enabled, SMBv1 disabled | `reg query`, `Get-SmbServerConfiguration` |
| AC-2 | Guest and built-in Administrator disabled | `Get-LocalUser` |
| AC-1 | Access control policy documented | Manual |
| IA-2 | Unique accounts + MFA | Manual |

Status logic: all sub-checks OK = PASS, some = PARTIAL, none = FAIL.

## Risk model

`Risk = Likelihood (1-5) x Impact (1-5) x status factor` (FAIL 1.0, PARTIAL 0.5, PASS 0). Levels: 0 None, <=6 Low, <=12 Medium, <=19 High, >=20 Critical.
Compliance % = PASS 100%, PARTIAL 50%, FAIL 0%, averaged over assessed controls.
Likelihood/impact values live in `controls.py` and are easy to tune.

## AI analysis

Report page -> expand "API key (optional)" and paste an Anthropic key (or set `ANTHROPIC_API_KEY`), then click **Generate written summary**.
The model sees only your recorded evidence, is told not to invent facts, and its output is validated against real control IDs. Without a key (or if the call fails) a deterministic offline template is used, so the feature never breaks. Optionally set `ANTHROPIC_MODEL` to change the model.

## Project layout

```
app.py        Streamlit app: top bar, sidebar navigation, one function per page (Start here, Summary, Assessment, Report)
ui.py         HTML/CSS components, colours and fonts
checks.py     Windows collectors + pure analyzers (unit-tested)
controls.py   NIST control catalog + likelihood/impact
risk.py       Risk scoring and compliance %
db.py         SQLite: assessments, change history, AI results
ai.py         LLM analysis + offline fallback
report.py     PDF generation (ReportLab)
demo.py       Sample data
tests/        22 unit/integration tests
docs/         Demo script, interview prep, CV text
```

## Tests

```
python -m unittest discover -s tests -v
```
Parsers are tested against realistic command output, so the logic is verified on any OS. The live Windows commands themselves can only be verified on Windows (see troubleshooting).

## Troubleshooting

| Symptom | Fix |
|---|---|
| AU-2 / IA-5 warning "needs Administrator" | Restart the terminal as Administrator |
| A check says "could not be checked" | Read the message; run that command manually in PowerShell to see its raw output |
| AU-2 "No audit policy returned" | Non-English Windows: `auditpol` names are localized; edit `REQUIRED_AUDIT` in `checks.py` |
| SI-3 "Defender status unavailable" | A third-party antivirus is active; assess SI-3 manually |
| `pip` / `python` not found | Reinstall Python with "Add to PATH", reopen the terminal |
| Streamlit page blank / port busy | `streamlit run app.py --server.port 8502` |
| Want a clean slate | Sidebar -> Reset, or delete `grc.db` |

## Limitations

- Each security control is evaluated against a defined set of measurable requirements rather than the full scope of the corresponding NIST SP 800-53 control.
- Automated assessments currently target a single Windows host and reflect its state at the time of execution.
- Risk scores are based on configured likelihood, impact, and assessment status values; they are not derived from live threat intelligence.
- Security log capacity is estimated using log-size information as a proxy.

## Future Enhancements

- Extend control mappings to additional frameworks, including CIS Controls and ISO/IEC 27001.
- Introduce Linux security assessment capabilities.
- Add scheduled assessments and historical compliance trend analysis.
- Integrate security evidence from tools such as Wazuh and Sysmon.