"""Automated technical checks (Windows).

Design: every check is split into
  1. a *collector*  - runs a Windows command and returns raw text, and
  2. an *analyzer*  - a pure function (raw text -> CheckResult) that is unit-tested.
This keeps the OS-specific part tiny and the compliance logic testable anywhere.
"""
from __future__ import annotations

import ctypes
import json
import os
import platform
import re
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Optional


class CheckError(Exception):
    """A check could not be performed (not admin, command missing, unexpected output)."""


@dataclass
class CheckResult:
    control_id: str
    status: str      # PASS / PARTIAL / FAIL / ERROR
    evidence: str


# --------------------------------------------------------------------------- helpers
def is_windows() -> bool:
    return platform.system() == "Windows"


def is_admin() -> bool:
    if not is_windows():
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _run(args, timeout=40) -> str:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, errors="replace")
    except FileNotFoundError:
        raise CheckError(f"Command not found: {args[0]}")
    except subprocess.TimeoutExpired:
        raise CheckError(f"Timed out running {args[0]}")
    if p.returncode != 0:
        lines = (p.stderr or p.stdout or "").strip().splitlines()
        raise CheckError(lines[0] if lines else f"{args[0]} exited with code {p.returncode}")
    return p.stdout


def _ps(command: str) -> str:
    return _run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                 "-Command", command])


def _json_list(raw: str):
    raw = (raw or "").strip()
    if not raw:
        raise CheckError("PowerShell returned no output")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise CheckError("Unexpected PowerShell output (could not parse JSON)")
    return data if isinstance(data, list) else [data]


def _to_bool(v) -> Optional[bool]:
    if v in (True, 1, "1", "true", "True"):
        return True
    if v in (False, 0, "0", "false", "False"):
        return False
    return None  # unknown / not configured


def grade(items):
    """items = [(evidence_text, True/False/None)] -> (status, evidence).
    All known OK -> PASS, none OK -> FAIL, mixed -> PARTIAL, nothing known -> ERROR."""
    known = [ok for _, ok in items if ok is not None]
    evidence = "; ".join(t for t, _ in items)
    if not known:
        return "ERROR", evidence
    if all(known):
        return "PASS", evidence
    if not any(known):
        return "FAIL", evidence
    return "PARTIAL", evidence


# --------------------------------------------------------------------------- SC-7 firewall
CMD_FIREWALL = "Get-NetFirewallProfile | Select-Object Name,Enabled | ConvertTo-Json -Compress"


def analyze_firewall(raw: str) -> CheckResult:
    items = []
    for p in _json_list(raw):
        state = _to_bool(p.get("Enabled"))
        label = "ON" if state else "OFF" if state is False else "not configured"
        items.append((f"{p.get('Name')} profile: {label}", state))
    status, ev = grade(items)
    return CheckResult("SC-7", status, f"Windows Firewall - {ev}")


# --------------------------------------------------------------------------- IA-5 / AC-7 policy
_policy_cache: dict = {}


def parse_secedit(text: str) -> dict:
    vals = dict(re.findall(r"^\s*(\w+)\s*=\s*(.+?)\s*$", text, re.M))
    def _int(key):
        v = vals.get(key)
        return int(v) if v is not None and re.fullmatch(r"-?\d+", v) else None
    return {"min_length": _int("MinimumPasswordLength"),
            "complexity": (vals["PasswordComplexity"] == "1") if "PasswordComplexity" in vals else None,
            "lockout": _int("LockoutBadCount")}


def parse_net_accounts(text: str) -> dict:
    m = re.search(r"Minimum password length:\s+(\d+)", text)
    l = re.search(r"Lockout threshold:\s+(\w+)", text)
    lockout = None
    if l:
        v = l.group(1)
        lockout = 0 if v.lower() == "never" else int(v) if v.isdigit() else None
    return {"min_length": int(m.group(1)) if m else None, "complexity": None, "lockout": lockout}


def _read_text(path: str) -> str:
    data = open(path, "rb").read()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    return data.decode("utf-8", errors="replace")


def get_security_policy() -> dict:
    """Prefer secedit (admin; gives complexity too); fall back to `net accounts`."""
    if _policy_cache:
        return _policy_cache
    pol = None
    try:
        cfg = os.path.join(tempfile.gettempdir(), "grc_secpol.inf")
        _run(["secedit", "/export", "/cfg", cfg, "/areas", "SECURITYPOLICY"])
        pol = parse_secedit(_read_text(cfg))
        pol["source"] = "secedit"
        os.remove(cfg)
        if pol["min_length"] is None or pol["lockout"] is None:
            pol = None
    except (CheckError, OSError):
        pol = None
    if pol is None:
        pol = parse_net_accounts(_run(["net", "accounts"]))
        pol["source"] = "net accounts"
    _policy_cache.update(pol)
    return pol


def analyze_password(pol: dict) -> CheckResult:
    length, cx = pol.get("min_length"), pol.get("complexity")
    if length is None:
        raise CheckError("Could not read minimum password length")
    cx_txt = ("complexity enforced" if cx else "complexity NOT enforced" if cx is False
              else "complexity not verified (run as Administrator)")
    if length >= 12 and cx is not False:
        status = "PASS"
    elif length >= 8 or cx is True:
        status = "PARTIAL"
    else:
        status = "FAIL"
    return CheckResult("IA-5", status, f"Minimum length {length}; {cx_txt}.")


def analyze_lockout(pol: dict) -> CheckResult:
    t = pol.get("lockout")
    if t is None:
        raise CheckError("Could not read lockout threshold")
    if 1 <= t <= 5:
        status = "PASS"
    elif 6 <= t <= 10:
        status = "PARTIAL"
    else:
        status = "FAIL"
    txt = "Never (0) - unlimited failed logons allowed" if t == 0 else f"{t} invalid attempts"
    return CheckResult("AC-7", status, f"Lockout threshold: {txt}.")


# --------------------------------------------------------------------------- AU-2 audit policy
REQUIRED_AUDIT = ["Logon", "User Account Management", "Process Creation"]


def parse_auditpol(text: str) -> dict:
    pat = r"^\s+(\S.*?)\s{2,}(No Auditing|Success and Failure|Success|Failure)\s*$"
    return {n.strip(): s for n, s in re.findall(pat, text, re.M)}


def analyze_audit(text: str) -> CheckResult:
    settings = parse_auditpol(text)
    if not settings:
        raise CheckError("No audit policy returned (needs Administrator and an English-language Windows)")
    items = []
    for name in REQUIRED_AUDIT:
        s = settings.get(name)
        items.append((f"{name}: {s or 'not found'}", None if s is None else "Success" in s))
    status, ev = grade(items)
    return CheckResult("AU-2", status, ev + ".")


# --------------------------------------------------------------------------- AU-4 log capacity
MIN_PASS_MB, MIN_PARTIAL_MB = 192, 20


def analyze_eventlog(text: str) -> CheckResult:
    size = re.search(r"maxSize:\s*(\d+)", text)
    enabled = re.search(r"enabled:\s*(true|false)", text)
    if not size:
        raise CheckError("Could not read Security log configuration")
    mb = int(size.group(1)) / 1048576
    if enabled and enabled.group(1) == "false":
        return CheckResult("AU-4", "FAIL", "Security event log is DISABLED.")
    status = "PASS" if mb >= MIN_PASS_MB else "PARTIAL" if mb >= MIN_PARTIAL_MB else "FAIL"
    return CheckResult("AU-4", status, f"Security log: enabled, max size {mb:.0f} MB (target >= {MIN_PASS_MB} MB).")


# --------------------------------------------------------------------------- SI-3 antivirus
CMD_DEFENDER = ("Get-MpComputerStatus | Select-Object AntivirusEnabled,RealTimeProtectionEnabled,"
                "AntivirusSignatureAge | ConvertTo-Json -Compress")


def analyze_defender(raw: str) -> CheckResult:
    d = _json_list(raw)[0]
    av, rtp = _to_bool(d.get("AntivirusEnabled")), _to_bool(d.get("RealTimeProtectionEnabled"))
    age = d.get("AntivirusSignatureAge")
    if av is None and rtp is None:
        raise CheckError("Defender status unavailable (a third-party antivirus may be in use)")
    ev = (f"Defender antivirus: {'enabled' if av else 'DISABLED'}; "
          f"real-time protection: {'on' if rtp else 'OFF'}; signatures {age} day(s) old.")
    if not av or not rtp:
        status = "FAIL"
    elif isinstance(age, int) and age > 7:
        status = "PARTIAL"
    else:
        status = "PASS"
    return CheckResult("SI-3", status, ev)


# --------------------------------------------------------------------------- CM-6 baseline
CMD_SMB1 = "Get-SmbServerConfiguration | Select-Object EnableSMB1Protocol | ConvertTo-Json -Compress"


def parse_uac(text: str) -> Optional[bool]:
    m = re.search(r"EnableLUA\s+REG_DWORD\s+0x([0-9a-fA-F]+)", text)
    return None if not m else int(m.group(1), 16) == 1


def analyze_config(uac_on: Optional[bool], smb1_enabled: Optional[bool]) -> CheckResult:
    items = [
        ("UAC (EnableLUA): " + ("enabled" if uac_on else "DISABLED" if uac_on is False else "unknown"), uac_on),
        ("SMBv1: " + ("ENABLED" if smb1_enabled else "disabled" if smb1_enabled is False
                      else "not verified (run as Administrator)"),
         None if smb1_enabled is None else not smb1_enabled),
    ]
    status, ev = grade(items)
    return CheckResult("CM-6", status, ev + ".")


def _check_config() -> CheckResult:
    out = _run(["reg", "query", r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
                "/v", "EnableLUA"])
    uac = parse_uac(out)
    try:
        smb1 = _to_bool(_json_list(_ps(CMD_SMB1))[0].get("EnableSMB1Protocol"))
    except CheckError:
        smb1 = None
    return analyze_config(uac, smb1)


# --------------------------------------------------------------------------- AC-2 accounts
CMD_USERS = ("Get-LocalUser | Select-Object Name,Enabled,@{n='SID';e={$_.SID.Value}} "
             "| ConvertTo-Json -Compress")


def analyze_accounts(raw: str) -> CheckResult:
    users = _json_list(raw)
    guest = admin = None
    enabled_names = []
    for u in users:
        sid, en = str(u.get("SID") or ""), _to_bool(u.get("Enabled"))
        if en:
            enabled_names.append(str(u.get("Name")))
        if sid.endswith("-501"):
            guest = en
        elif sid.endswith("-500"):
            admin = en
    items = [
        ("Guest account: " + ("ENABLED" if guest else "disabled" if guest is False else "not found"),
         None if guest is None else not guest),
        ("Built-in Administrator: " + ("ENABLED" if admin else "disabled" if admin is False else "not found"),
         None if admin is None else not admin),
    ]
    status, ev = grade(items)
    return CheckResult("AC-2", status, f"{ev}; {len(enabled_names)} enabled local account(s): {', '.join(enabled_names)}.")


# --------------------------------------------------------------------------- registry
AUTOMATED = [
    ("SC-7", lambda: analyze_firewall(_ps(CMD_FIREWALL))),
    ("IA-5", lambda: analyze_password(get_security_policy())),
    ("AC-7", lambda: analyze_lockout(get_security_policy())),
    ("AU-2", lambda: analyze_audit(_run(["auditpol", "/get", "/category:*"]))),
    ("AU-4", lambda: analyze_eventlog(_run(["wevtutil", "gl", "Security"]))),
    ("SI-3", lambda: analyze_defender(_ps(CMD_DEFENDER))),
    ("CM-6", _check_config),
    ("AC-2", lambda: analyze_accounts(_ps(CMD_USERS))),
]


def run_all_checks():
    if not is_windows():
        raise CheckError("Automated checks need Windows. Use 'Load demo data' to explore on other systems.")
    _policy_cache.clear()
    results = []
    for cid, fn in AUTOMATED:
        try:
            res = fn()
            if res.status == "ERROR":
                res = CheckResult(cid, "ERROR", res.evidence)
        except CheckError as e:
            res = CheckResult(cid, "ERROR", str(e))
        except Exception as e:  # never let one check crash the whole run
            res = CheckResult(cid, "ERROR", f"Unexpected error: {e}")
        results.append(res)
    return results
