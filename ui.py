"""HTML/CSS building blocks (no chart libraries). Light, flat, enterprise-style.
Fonts: IBM Plex Sans + IBM Plex Mono via Google Fonts, with system fallbacks.
Rename the product by changing APP_NAME."""
import html

from risk import COMPLIANCE_POINTS

e = html.escape

APP_NAME = "ControlScope"
APP_TAGLINE = "Security control assessment"

STATUS_COLOR = {"PASS": "#2e7d5b", "PARTIAL": "#b7791f", "FAIL": "#c53030", "NOT ASSESSED": "#718096"}
STATUS_LABEL = {"PASS": "Pass", "PARTIAL": "Partial", "FAIL": "Fail", "NOT ASSESSED": "Not assessed"}
LEVEL_COLOR = {"Critical": "#9b2c2c", "High": "#c05621", "Medium": "#b7791f", "Low": "#2f855a",
               "None": "#2f855a", "N/A": "#718096"}
MUTED = "#667085"

LOGO = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.5 4.5 5.6v5.6c0 4.7 3.2 8.9 7.5 10.3 '
        '4.3-1.4 7.5-5.6 7.5-10.3V5.6L12 2.5z"/><path d="m8.6 12.2 2.4 2.4 4.5-4.8"/></svg>')

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');
html,body,.stApp,p,li,label,h1,h2,h3,h4,input,textarea,button,[data-baseweb="select"] div,
[data-testid="stSidebarNavLink"] span{font-family:"IBM Plex Sans","Segoe UI",-apple-system,Roboto,Arial,sans-serif !important}
.block-container{padding-top:1.6rem;max-width:1240px}
footer{visibility:hidden}
[data-testid="stAppDeployButton"],.stDeployButton{display:none}
header[data-testid="stHeader"]{background:transparent}
[data-testid="stSidebar"]{background:#ffffff;border-right:1px solid #e3e7ec}
[data-testid="stSidebar"] .stButton>button{width:100%;border-radius:6px}
.sbl{font-size:.68rem;text-transform:uppercase;letter-spacing:.1em;color:#667085;font-weight:600;margin:6px 0 8px}
.topbar{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;background:#13233f;
border-radius:8px;padding:12px 18px;margin-bottom:24px}
.brand{display:flex;align-items:center;gap:12px}
.mark{width:34px;height:34px;border-radius:8px;background:#2f6fdd;display:flex;align-items:center;justify-content:center}
.bn{font-weight:600;font-size:1.06rem;line-height:1.2;color:#fff;letter-spacing:.005em}
.bt{font-size:.72rem;color:#9fb0cc}
.chips{display:flex;gap:8px;flex-wrap:wrap}
.chip2{font-size:.72rem;padding:4px 10px;border:1px solid rgba(255,255,255,.22);border-radius:5px;color:#cfd9ea;white-space:nowrap}
.ph{margin-bottom:20px}
.ph h1{margin:0;padding:0;font-size:1.55rem;font-weight:600;color:#111827;letter-spacing:-.01em;line-height:1.25}
.ph .sub{margin-top:4px;font-size:.88rem;color:#667085}
.card{background:#fff;border:1px solid #e3e7ec;border-radius:8px;padding:16px 18px}
.ctitle{font-size:.68rem;text-transform:uppercase;letter-spacing:.1em;color:#667085;font-weight:600;margin-bottom:12px}
.kpi .value{font-size:1.9rem;font-weight:600;line-height:1.1;font-variant-numeric:tabular-nums;color:#111827}
.kpi .sub,.sub{font-size:.78rem;color:#667085;margin-top:3px}
.st{display:inline-flex;align-items:center;gap:7px;font-size:.8rem;font-weight:600;white-space:nowrap}
.st i{width:8px;height:8px;border-radius:50%;display:inline-block}
.tag{display:inline-block;padding:1px 8px;border-radius:4px;font-size:.66rem;color:#667085;border:1px solid #d5dae1;white-space:nowrap}
.cid{font-family:"IBM Plex Mono",Consolas,"SF Mono",Menlo,monospace;font-weight:600;font-size:.88rem;color:#1f4f99}
.brow{display:grid;grid-template-columns:var(--lw,120px) 1fr 44px;gap:12px;align-items:center;margin:11px 0;font-size:.85rem}
.blabel{overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.bar{height:6px;border-radius:3px;background:#e8ebef;overflow:hidden}
.bar>span{display:block;height:100%;border-radius:3px}
.bval{text-align:right;font-weight:600;font-variant-numeric:tabular-nums}
.stack{display:flex;height:12px;border-radius:6px;overflow:hidden;background:#e8ebef;margin:4px 0 14px}
.stack span{display:block;height:100%}
.legend{display:flex;flex-wrap:wrap;gap:8px 18px;font-size:.84rem}
.hint{margin-top:16px;padding:10px 12px;border-radius:6px;background:#f3f6fb;border:1px solid #dfe6f1;font-size:.85rem;line-height:1.5}
.tblwrap{overflow-x:auto}
.tbl{width:100%;border-collapse:separate;border-spacing:0;table-layout:fixed;background:#fff;border:1px solid #e3e7ec;
border-radius:8px;overflow:hidden;font-size:.82rem}
.tbl th{text-align:left;font-size:.64rem;text-transform:uppercase;letter-spacing:.08em;color:#667085;font-weight:600;
padding:10px 12px;background:#f9fafb;border-bottom:1px solid #e3e7ec}
.tbl td{padding:13px 12px;vertical-align:top;border-bottom:1px solid #eef0f3;line-height:1.5;word-wrap:break-word}
.tbl tr:last-child td{border-bottom:none}
.tbl .pn{margin-top:3px;color:#344054}
.muted{color:#98a2b3}
.empty{padding:30px 28px;border:1px dashed #cbd2da;border-radius:8px;color:#475467;background:#fff;line-height:1.9}
.stepn{width:26px;height:26px;border-radius:50%;background:#1f4f99;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:.8rem;margin-bottom:10px}
.sttl{font-weight:600;margin-bottom:6px;color:#111827}
.stxt{font-size:.84rem;color:#475467;line-height:1.55}
.prose{font-size:.93rem;line-height:1.7;color:#344054}
.hostcard{font-size:.76rem;color:#667085;line-height:1.7}
</style>"""


def md(target, markup):
    """Render HTML safely: always start with a <div> so markdown never mangles it."""
    if not markup.lstrip().startswith(("<div", "<style")):
        markup = f"<div>{markup}</div>"
    target.markdown(markup, unsafe_allow_html=True)


def topbar(host, last_scan):
    return (f'<div class="topbar"><div class="brand"><div class="mark">{LOGO}</div>'
            f'<div><div class="bn">{e(APP_NAME)}</div><div class="bt">{e(APP_TAGLINE)}</div></div></div>'
            f'<div class="chips"><span class="chip2">NIST SP 800-53 Rev. 5</span>'
            f'<span class="chip2">Host: {e(host)}</span><span class="chip2">Last scan: {e(last_scan)}</span></div></div>')


def page_header(title, subtitle=""):
    return f'<div class="ph"><h1>{e(title)}</h1><div class="sub">{e(subtitle)}</div></div>'


def pill(text, color):
    return f'<span class="st"><i style="background:{color}"></i>{e(str(text))}</span>'


def status_pill(status):
    return pill(STATUS_LABEL.get(status, status), STATUS_COLOR.get(status, MUTED))


def level_pill(level, score=None):
    label = level if score is None else f"{level} · {score:g}"
    return pill(label, LEVEL_COLOR.get(level, MUTED))


def tag(text):
    return f'<span class="tag">{e(str(text))}</span>'


def card(title, inner, mh=None):
    style = f' style="min-height:{mh}px"' if mh else ""
    return f'<div class="card"{style}><div class="ctitle">{e(title)}</div>{inner}</div>'


def kpi(label, value, color=None, sub=""):
    style = f' style="color:{color}"' if color else ""
    return (f'<div class="card kpi"><div class="ctitle">{e(label)}</div>'
            f'<div class="value"{style}>{e(str(value))}</div><div class="sub">{e(sub)}</div></div>')


def score_color(pct):
    return STATUS_COLOR["PASS"] if pct >= 80 else STATUS_COLOR["PARTIAL"] if pct >= 50 else STATUS_COLOR["FAIL"]


def bar_row(label, frac, color, right, lw=120):
    frac = max(0.0, min(1.0, frac))
    return (f'<div class="brow" style="--lw:{lw}px"><div class="blabel" title="{e(label)}">{e(label)}</div>'
            f'<div class="bar"><span style="width:{frac * 100:.0f}%;background:{color}"></span></div>'
            f'<div class="bval">{e(str(right))}</div></div>')


def top_risks(rows, n=5):
    gaps = sorted([r for r in rows if r["risk_score"]], key=lambda r: r["risk_score"], reverse=True)[:n]
    if not gaps:
        return '<div class="sub">No open risks.</div>'
    return "".join(bar_row(f"{r['id']}  {r['plain']}", r["risk_score"] / 25, LEVEL_COLOR[r["risk_level"]],
                           f"{r['risk_score']:g}", lw=250) for r in gaps)


def breakdown(rows):
    total = max(len(rows), 1)
    order = ["PASS", "PARTIAL", "FAIL", "NOT ASSESSED"]
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in order}
    segs = "".join(f'<span style="width:{counts[s] / total * 100:.1f}%;background:{STATUS_COLOR[s]}"></span>'
                   for s in order if counts[s])
    legend = "".join(f'<span class="st"><i style="background:{STATUS_COLOR[s]}"></i>{STATUS_LABEL[s]} · {counts[s]}</span>'
                     for s in order)
    gaps = sorted([r for r in rows if r["risk_score"]], key=lambda r: r["risk_score"], reverse=True)
    if gaps:
        g = gaps[0]
        hint = (f'<div class="hint"><b>Fix first:</b> {e(g["id"])} {e(g["plain"])} '
                f'({e(g["risk_level"])}, {g["risk_score"]:g}/25). {e(g["remediation"])}</div>')
    else:
        hint = '<div class="hint">No open gaps in the assessed controls.</div>'
    return f'<div class="stack">{segs}</div><div class="legend">{legend}</div>{hint}'


def step(n, title, text, mh=190):
    return (f'<div class="card" style="min-height:{mh}px"><div class="stepn">{n}</div>'
            f'<div class="sttl">{e(title)}</div><div class="stxt">{text}</div></div>')


def prose_card(title, paragraphs):
    body = "".join(f'<p style="margin:0 0 10px">{p}</p>' for p in paragraphs)
    return f'<div class="card"><div class="ctitle">{e(title)}</div><div class="prose">{body}</div></div>'


def controls_overview(controls):
    heads = ["Control", "In plain words", "Why it matters", "How it is checked"]
    widths = [12, 23, 36, 29]
    out = ['<div class="tblwrap"><table class="tbl"><colgroup>',
           "".join(f'<col style="width:{w}%">' for w in widths), "</colgroup><thead><tr>",
           "".join(f"<th>{h}</th>" for h in heads), "</tr></thead><tbody>"]
    for c in controls:
        kind = tag("Automated" if c["auto"] else "Manual (you answer)")
        out.append(f'<tr><td><span class="cid">{e(c["id"])}</span></td><td>{e(c["plain"])}</td>'
                   f'<td>{e(c["why"])}</td><td>{e(c["check"])}<div style="margin-top:6px">{kind}</div></td></tr>')
    out.append("</tbody></table></div>")
    return "".join(out)


def manual_guide(r):
    g = r["manual_guide"]
    rows = "".join(f'<div style="margin:4px 0">{status_pill(s)} &nbsp;{e(g[s])}</div>' for s in ("PASS", "PARTIAL", "FAIL"))
    return (f'<div><span class="cid">{e(r["id"])}</span> &nbsp;<b>{e(r["plain"])}</b>'
            f'<div style="margin:10px 0 4px;font-size:.92rem"><b>Question:</b> {e(r["manual_q"])}</div>'
            f'<div class="sub" style="margin:4px 0 10px"><b>Where to look:</b> {e(r["manual_where"])}</div>'
            f'<div style="font-size:.84rem;margin-bottom:10px">{rows}</div>'
            f'<div class="sub"><b>Example evidence:</b> {e(r["manual_example"])}</div></div>')


def assessment_table(rows):
    heads = ["Rule", "What we checked", "What we found", "Result", "Risk", "How to fix"]
    widths = [19, 19, 24, 9, 10, 19]
    out = ['<div class="tblwrap"><table class="tbl"><colgroup>',
           "".join(f'<col style="width:{w}%">' for w in widths), "</colgroup><thead><tr>",
           "".join(f"<th>{h}</th>" for h in heads), "</tr></thead><tbody>"]
    for r in rows:
        col = LEVEL_COLOR.get(r["risk_level"], MUTED) if r["status"] != "NOT ASSESSED" else MUTED
        if r["evidence"]:
            found = e(r["evidence"])
        elif r["auto"]:
            found = '<span class="muted">Not assessed yet. Run the automated checks.</span>'
        else:
            found = '<span class="muted">Needs your input. See Manual controls below.</span>'
        fix = '<span class="muted">No action needed</span>' if r["status"] == "PASS" else e(r["remediation"])
        risk = level_pill(r["risk_level"], r["risk_score"]) if r["risk_score"] is not None else '<span class="muted">–</span>'
        kind = tag("Automated" if r["auto"] else "Manual")
        out.append(
            f'<tr><td style="box-shadow:inset 3px 0 0 {col}"><span class="cid">{e(r["id"])}</span>'
            f'<div class="pn">{e(r["plain"])}</div></td>'
            f'<td>{e(r["check"])}<div style="margin-top:6px">{kind}</div></td>'
            f'<td>{found}</td><td>{status_pill(r["status"])}</td><td>{risk}</td><td>{fix}</td></tr>')
    out.append("</tbody></table></div>")
    return "".join(out)


def gap_card(r, finding=None):
    col = LEVEL_COLOR.get(r["risk_level"], MUTED)
    def kv(k, v, cls=""):
        return (f'<div style="display:grid;grid-template-columns:120px 1fr;gap:12px;padding:5px 0;font-size:.88rem;'
                f'line-height:1.5"><div style="font-size:.66rem;text-transform:uppercase;letter-spacing:.08em;'
                f'color:#667085;font-weight:600;padding-top:3px">{e(k)}</div><div>{e(v)}</div></div>')
    parts = [f'<div class="card" style="border-left:3px solid {col};margin-bottom:12px">',
             f'<div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap;padding-bottom:8px;margin-bottom:4px;'
             f'border-bottom:1px solid #eef0f3"><span class="cid">{e(r["id"])}</span>'
             f'<b>{e(r["name"])}</b>{status_pill(r["status"])}{level_pill(r["risk_level"], r["risk_score"])}</div>',
             kv("Evidence", r["evidence"] or "none recorded")]
    if finding:
        parts.append(kv("Why it matters", finding["finding"]))
    parts.append(kv("Recommendation", finding["recommendation"] if finding else r["remediation"]))
    parts.append("</div>")
    return "".join(parts)
