"""Source-preservation and no-false-promotion checks for the TIFF application."""
import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'ship'))
from unikernel import tiff_workflow as W, Refusal

class TIFFWorkflow(unittest.TestCase):
    def test_all_canonical_tasks_retained(self):
        r=W.check(ROOT);self.assertEqual(r['canonical_tasks_checked'],325000);self.assertEqual(r['phase_gates_closed'],0);self.assertFalse(r['full_series_complete'])
    def test_exact_prompt_and_workflow(self):
        r=W.show(ROOT,'C313-T001.05');self.assertIn('Workflow C313-T001.05',r['source_prompt_workflow']);self.assertEqual(r['disposition']['reviewer'],'UNASSIGNED');self.assertEqual(r['disposition']['status'],'BLOCKED')
    def test_invalid_task(self):
        for s in ['../../x','C000-T001.01','C326-T001.01','C001-T101.01','C001-T001.11']:
            with self.subTest(s=s),self.assertRaises(Refusal):W.show(ROOT,s)
    def test_archive_corruption_refused(self):
        with tempfile.TemporaryDirectory() as d:
            b=Path(d)/'tifflow';b.mkdir();(b/'APPLICATION.json').write_bytes((ROOT/'tifflow/APPLICATION.json').read_bytes());(b/'series.zip').write_bytes(b'x')
            with self.assertRaises(Refusal):W.check(d)
    def test_nine_unpromoted_phases(self):
        r=W.status(ROOT);self.assertEqual(r['phase_gates'],{f'P{i:02d}':'BLOCKED' for i in range(1,10)});self.assertEqual(r['components'],325)
    def test_windows_launchers(self):
        for name in ['PIXELS.cmd','TIFF_FLOW.cmd','VERIFY_TIFF.cmd']:
            b=(ROOT/name).read_bytes();b.decode('ascii');self.assertTrue(b.startswith(b'@echo off\r\n'));self.assertNotIn(b'RunAs',b);self.assertNotIn(b'ExecutionPolicy Bypass',b)

if __name__=='__main__':unittest.main()
