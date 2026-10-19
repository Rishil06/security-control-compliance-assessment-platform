"""Run:  python -m unittest discover -s tests -v   (works on any OS)"""
import os
import sys
import tempfile
import unittest

os.environ["GRC_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ai, checks, db, demo, report  # noqa: E402
from risk import compliance_percent, risk_level, risk_score  # noqa: E402

FIREWALL_OFF = '[{"Name":"Domain","Enabled":0},{"Name":"Private","Enabled":0},{"Name":"Public","Enabled":0}]'
FIREWALL_MIX = '[{"Name":"Domain","Enabled":true},{"Name":"Private","Enabled":true},{"Name":"Public","Enabled":false}]'
FIREWALL_ON = '[{"Name":"Domain","Enabled":1},{"Name":"Private","Enabled":1},{"Name":"Public","Enabled":1}]'
SECEDIT = "[System Access]\r\nMinimumPasswordLength = 12\r\nPasswordComplexity = 1\r\nLockoutBadCount = 5\r\n"
NET_ACCOUNTS = ("Force user logoff how long after time expires?:       Never\n"
                "Minimum password length:                              7\n"
                "Lockout threshold:                                    Never\n")
AUDITPOL = ("System audit policy\r\nCategory/Subcategory                      Setting\r\nLogon/Logoff\r\n"
            "  Logon                                   Success and Failure\r\n"
            "  Logoff                                  Success\r\nAccount Management\r\n"
            "  User Account Management                 Success\r\nDetailed Tracking\r\n"
            "  Process Creation                        No Auditing\r\n")
WEVT = "name: Security\nenabled: true\nlogging:\n  retention: false\n  maxSize: 20971520\n"
UAC = "HKEY_LOCAL_MACHINE\\...\\System\n    EnableLUA    REG_DWORD    0x1\n"
USERS = ('[{"Name":"Administrator","Enabled":false,"SID":"S-1-5-21-1-2-3-500"},'
         '{"Name":"Guest","Enabled":false,"SID":"S-1-5-21-1-2-3-501"},'
         '{"Name":"rishil","Enabled":true,"SID":"S-1-5-21-1-2-3-1001"}]')


class RiskTests(unittest.TestCase):
    def test_scores(self):
        self.assertEqual(risk_score("FAIL", 4, 5), 20)
        self.assertEqual(risk_score("PARTIAL", 4, 5), 10)
        self.assertEqual(risk_score("PASS", 4, 5), 0)
        self.assertIsNone(risk_score("NOT ASSESSED", 4, 5))

    def test_levels(self):
        self.assertEqual([risk_level(x) for x in (None, 0, 6, 12, 19, 20)],
                         ["N/A", "None", "Low", "Medium", "High", "Critical"])

    def test_compliance_ignores_unassessed(self):
        rows = [{"status": "PASS"}, {"status": "FAIL"}, {"status": "NOT ASSESSED"}]
        self.assertEqual(compliance_percent(rows), 50.0)


class CheckTests(unittest.TestCase):
    def test_firewall(self):
        self.assertEqual(checks.analyze_firewall(FIREWALL_OFF).status, "FAIL")
        self.assertEqual(checks.analyze_firewall(FIREWALL_MIX).status, "PARTIAL")
        self.assertEqual(checks.analyze_firewall(FIREWALL_ON).status, "PASS")

    def test_firewall_single_object_json(self):
        self.assertEqual(checks.analyze_firewall('{"Name":"Public","Enabled":true}').status, "PASS")

    def test_policy_secedit(self):
        pol = checks.parse_secedit(SECEDIT)
        self.assertEqual(checks.analyze_password(pol).status, "PASS")
        self.assertEqual(checks.analyze_lockout(pol).status, "PASS")

    def test_policy_net_accounts(self):
        pol = checks.parse_net_accounts(NET_ACCOUNTS)
        self.assertEqual(pol["lockout"], 0)
        self.assertEqual(checks.analyze_password(pol).status, "FAIL")
        self.assertEqual(checks.analyze_lockout(pol).status, "FAIL")

    def test_lockout_bands(self):
        for t, s in ((3, "PASS"), (8, "PARTIAL"), (0, "FAIL"), (50, "FAIL")):
            self.assertEqual(checks.analyze_lockout({"lockout": t}).status, s)

    def test_audit(self):
        r = checks.analyze_audit(AUDITPOL)
        self.assertEqual(r.status, "PARTIAL")
        self.assertIn("Process Creation: No Auditing", r.evidence)

    def test_audit_no_output_is_error(self):
        with self.assertRaises(checks.CheckError):
            checks.analyze_audit("Error 0x00000522 occurred")

    def test_eventlog(self):
        self.assertEqual(checks.analyze_eventlog(WEVT).status, "PARTIAL")
        self.assertEqual(checks.analyze_eventlog(WEVT.replace("20971520", "268435456")).status, "PASS")
        self.assertEqual(checks.analyze_eventlog(WEVT.replace("20971520", "1048576")).status, "FAIL")

    def test_defender(self):
        ok = '{"AntivirusEnabled":true,"RealTimeProtectionEnabled":true,"AntivirusSignatureAge":1}'
        self.assertEqual(checks.analyze_defender(ok).status, "PASS")
        self.assertEqual(checks.analyze_defender(ok.replace(':1}', ':30}')).status, "PARTIAL")
        self.assertEqual(checks.analyze_defender(ok.replace('"RealTimeProtectionEnabled":true', '"RealTimeProtectionEnabled":false')).status, "FAIL")

    def test_config(self):
        self.assertTrue(checks.parse_uac(UAC))
        self.assertEqual(checks.analyze_config(True, False).status, "PASS")
        self.assertEqual(checks.analyze_config(True, True).status, "PARTIAL")
        self.assertEqual(checks.analyze_config(False, True).status, "FAIL")
        self.assertEqual(checks.analyze_config(True, None).status, "PASS")

    def test_accounts(self):
        r = checks.analyze_accounts(USERS)
        self.assertEqual(r.status, "PASS")
        self.assertIn("rishil", r.evidence)
        self.assertEqual(checks.analyze_accounts(USERS.replace('"Guest","Enabled":false', '"Guest","Enabled":true')).status, "PARTIAL")

    def test_run_all_checks_off_windows(self):
        if not checks.is_windows():
            with self.assertRaises(checks.CheckError):
                checks.run_all_checks()


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        db.init_db()
        db.reset_all()

    def test_demo_report_and_ai_offline(self):
        demo.load_demo()
        rows = db.get_assessments()
        self.assertEqual(compliance_percent(rows), 40.0)
        analysis, note = ai.analyze(rows, api_key=None)
        self.assertIn("offline", note)
        self.assertEqual(set(analysis["findings"]), {r["id"] for r in ai.get_gaps(rows)})
        db.save_ai_analysis(analysis)
        pdf = report.build_report(rows, ai=db.get_ai_analysis(), host={"hostname": "TEST"})
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 3000)

    def test_report_with_nothing_assessed_and_special_chars(self):
        db.save_assessment("AC-1", "FAIL", "Evidence with <tags> & ampersands")
        pdf = report.build_report(db.get_assessments())
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_history_logged(self):
        db.save_assessment("SC-7", "FAIL", "off", source="automated")
        db.save_assessment("SC-7", "PASS", "on", source="automated")
        h = db.get_history()
        self.assertEqual([x["status"] for x in h[:2]], ["PASS", "FAIL"])

    def test_au11_results_migrate_to_au4(self):
        import sqlite3
        con = sqlite3.connect(db.DB_PATH)
        con.execute("DELETE FROM assessments WHERE control_id='AU-4'")
        con.execute("INSERT OR REPLACE INTO assessments (control_id,status,evidence,source) VALUES ('AU-11','FAIL','old','automated')")
        con.commit(); con.close()
        db.init_db()
        row = [r for r in db.get_assessments() if r["id"] == "AU-4"][0]
        self.assertEqual((row["status"], row["evidence"]), ("FAIL", "old"))

    def test_every_control_has_mapping_fields(self):
        from controls import CONTROLS
        for c in CONTROLS:
            for k in ("plain", "check", "requirement", "why", "remediation"):
                self.assertTrue(c[k], (c["id"], k))

    def test_manual_controls_have_guidance(self):
        from controls import CONTROLS
        manual = [c for c in CONTROLS if not c["auto"]]
        self.assertEqual({c["id"] for c in manual}, {"AC-1", "IA-2"})
        for c in manual:
            for k in ("manual_q", "manual_where", "manual_example"):
                self.assertTrue(c[k], (c["id"], k))
            self.assertEqual(set(c["manual_guide"]), {"PASS", "PARTIAL", "FAIL"})

    def test_ai_falls_back_on_bad_key(self):
        demo.load_demo()
        analysis, note = ai.analyze(db.get_assessments(), api_key="invalid")
        self.assertEqual(analysis["model"], "offline-template")
        self.assertIn("used the offline template", note)


if __name__ == "__main__":
    unittest.main()
