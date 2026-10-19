"""Sample assessment data so the app can be explored on any OS (or screenshotted)."""
import db

DEMO = {
    "AC-1": ("FAIL", "No documented access control policy found during document review.", "demo"),
    "AC-2": ("PARTIAL", "Guest account: disabled; Built-in Administrator: ENABLED; 4 enabled local account(s).", "demo"),
    "AC-7": ("FAIL", "Lockout threshold: Never (0) - unlimited failed logons allowed.", "demo"),
    "AU-2": ("PARTIAL", "Logon: Success and Failure; User Account Management: Success; Process Creation: No Auditing.", "demo"),
    "AU-4": ("PARTIAL", "Security log: enabled, max size 20 MB (target >= 192 MB).", "demo"),
    "CM-6": ("PASS", "UAC (EnableLUA): enabled; SMBv1: disabled.", "demo"),
    "IA-2": ("PARTIAL", "Unique accounts in use; MFA not enabled for local or remote logon.", "demo"),
    "IA-5": ("FAIL", "Minimum length 7; password complexity NOT enforced.", "demo"),
    "SC-7": ("FAIL", "Windows Firewall - Domain profile: OFF; Private profile: OFF; Public profile: OFF.", "demo"),
    "SI-3": ("PASS", "Defender antivirus: enabled; real-time protection: on; signatures 1 day(s) old.", "demo"),
}


def load_demo():
    for cid, (status, evidence, source) in DEMO.items():
        db.save_assessment(cid, status, evidence, source=source)
