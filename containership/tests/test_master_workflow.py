from __future__ import annotations
import tempfile, unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'ship'))
from unikernel import Refusal
from unikernel import kernel_contracts as K
from unikernel import master_workflow as M

class KernelContractTests(unittest.TestCase):
    def test_descriptor(self):
        d=K.descriptor();self.assertEqual(d['abi'],K.ABI);self.assertEqual(d['tile_payload_max_bytes'],464);self.assertTrue(d['deterministic_integer_semantics'])
    def test_validate(self):
        r={'abi':K.ABI,'op':'add','x':1,'y':2,'value':3};self.assertEqual(K.validate_request(r),r)
    def test_reject(self):
        for r in [
            {'abi':'bad','op':'add','x':1,'y':2,'value':3},
            {'abi':K.ABI,'op':'mul','x':1,'y':2,'value':3},
            {'abi':K.ABI,'op':'add','x':-1,'y':2,'value':3},
        ]:
            with self.assertRaises(Refusal):K.validate_request(r)

class MasterWorkflowTests(unittest.TestCase):
    def test_status(self):
        r=M.status(ROOT);self.assertEqual(r['tasks'],375000);self.assertEqual(r['components'],150);self.assertEqual(r['source_tasks_promoted_pass'],0)
    def test_check(self):
        r=M.check(ROOT,deep=False);self.assertEqual(r['integrity'],'PASS');self.assertEqual(r['unique_ids'],375000)
    def test_show(self):
        r=M.show(ROOT,'C001.001.T01');self.assertEqual(r['source']['id'],'C001.001.T01');self.assertIn(r['disposition']['status'],{'OPEN','BLOCKED'})
