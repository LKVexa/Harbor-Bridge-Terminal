"""Source/launcher/traceability regressions; no service or control mutation is started."""
import gzip,hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'ship'))
from unikernel import vws_workflow as W, Refusal

class VWSIntegration(unittest.TestCase):
    def test_complete_source_traceability(self):
        r=W.check(ROOT)
        self.assertEqual(r['task_count'],6360);self.assertEqual(r['source_requirement_hashes_verified'],6300)
        self.assertEqual(r['engineering_completion'],'NOT_COMPLETE');self.assertEqual(r['phase_gates_closed'],0)
    def test_exact_original_workpack_retained(self):
        r=W.show(ROOT,'C18-001');s=r['source_workpack']
        self.assertEqual(s['requirement'],r['current_disposition']['requirement'])
        self.assertGreater(len(s['prompt']),100);self.assertGreater(len(s['workflow']),1)
    def test_no_automatic_pass_or_lost_ids(self):
        b,m=W.load(ROOT);rows,source=W.records(b,m)
        self.assertEqual(len({r['id'] for r in rows}),6360)
        self.assertFalse(any(r['status']=='PASS' for r in rows))
        self.assertTrue(any(r['inherited_ramws_status']=='PASS' and r['status']!='PASS' for r in rows))
    def test_traversal_task_refused(self):
        for value in ['../MASTER','I001/../../','C18-001\x00','I999']:
            with self.subTest(value=value),self.assertRaises(Refusal):W.show(ROOT,value)
    def test_corrupt_archive_fails_before_read(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)/'vwsflow';base.mkdir()
            (base/'APPLICATION.json').write_bytes((ROOT/'vwsflow/APPLICATION.json').read_bytes())
            (base/'series.zip').write_bytes(b'corrupt')
            with self.assertRaisesRegex(Refusal,'archive digest mismatch'):W.check(d)
    def test_windows_launchers_ascii_crlf_and_no_elevation(self):
        for name in ['START.cmd','TERMINAL.cmd','VERIFY_VWS.cmd','CHECK_VWS.cmd','VWS_WORKFLOW.cmd']:
            b=(ROOT/name).read_bytes();b.decode('ascii');self.assertTrue(b.startswith(b'@echo off\r\n'),name)
            self.assertNotIn(b'ExecutionPolicy Bypass',b);self.assertNotIn(b'RunAs',b)

if __name__=='__main__':unittest.main()
