"""JYRM 1BNCF source-preservation and no-false-promotion tests."""
import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'ship'))
from unikernel import onebit_workflow as W, Refusal

class OneBitWorkflowTests(unittest.TestCase):
    def test_complete_ledger_retained(self):
        r=W.check(ROOT);self.assertEqual(r['tasks'],275000);self.assertEqual(r['components'],110);self.assertEqual(r['phase_gates_closed'],0);self.assertFalse(r['engineering_completion_verified'])
    def test_status_is_not_promoted(self):
        r=W.status(ROOT);self.assertEqual(r['counts'],{'BLOCKED':85000,'IN_PROGRESS':190000});self.assertEqual(r['phase_gates'],{f'P{i:02d}':'BLOCKED' for i in range(1,11)});self.assertFalse(r['full_series_complete'])
    def test_exact_source_prompt_visible(self):
        r=W.show(ROOT,'PW-001-001-01');self.assertIn('PW-001-001-01',r['source_prompt_workflow']);self.assertIn(r['disposition']['status'],('IN_PROGRESS','BLOCKED'))
    def test_invalid_ids_refused(self):
        for s in ['../../x','PW-000-001-01','PW-111-001-01','PW-001-101-01','PW-001-001-26']:
            with self.subTest(s=s),self.assertRaises(Refusal):W.show(ROOT,s)
    def test_source_archives_exact_count(self):
        app=json.loads((ROOT/'onebitflow/APPLICATION.json').read_text());self.assertEqual(len(app['source_phases']),10);self.assertEqual(sum(x['prompt_workflows'] for x in app['source_phases']),275000)
    def test_windows_launchers(self):
        for name in ['ONEBIT.cmd','ONEBIT_FLOW.cmd','VERIFY_1BIT.cmd']:
            b=(ROOT/name).read_bytes();b.decode('ascii');self.assertTrue(b.startswith(b'@echo off\r\n'));self.assertNotIn(b'RunAs',b);self.assertNotIn(b'ExecutionPolicy Bypass',b)

if __name__=='__main__':unittest.main()
