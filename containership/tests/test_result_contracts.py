"""Failure-result contracts and real TIFF-codec guards (no guest sandbox claims)."""
from __future__ import annotations
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'ship'))
from unikernel import Refusal, engines as E, berth as BT, cli, ucmanifest as M, tif_fabric as TF, hullmount as HM

class Contracts(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(); self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)
        p=mock.patch.object(E,'SHIP',str(self.p));p.start();self.addCleanup(p.stop)
    def cargo(self):
        d=self.p/'berths/demo'; c=d/'DF_Small/cargo/_alias/a.mssl';c.parent.mkdir(parents=True);c.write_text('HALT\n')
        r={'path':'nested/a.mssl','stored_as':'_alias/a.mssl','node':'N_SMALL','bytes':c.stat().st_size,'sha256':M.sha256_file(str(c))}
        (d/'SORT_LEDGER.json').write_text(json.dumps({'records':[r]}));return c,r
    def run_slot(self,a,result):
        adapter=mock.Mock();adapter.run_native.return_value=result
        nodes=mock.Mock();nodes.make_adapter.return_value=adapter
        class AdapterRefusal(Exception): pass
        b={'roots':{'N_SMALL':'fake-root'},'nodes':nodes,'dfabric':types.SimpleNamespace(AdapterRefusal=AdapterRefusal)}
        with mock.patch.object(E,'bind',return_value=b),contextlib.redirect_stdout(io.StringIO()):code=cli.cmd_slot_run(a)
        return code,adapter
    def args(self,cargo='nested/a.mssl',slot='DF_Small'):
        return types.SimpleNamespace(name='demo',slot=slot,cargo=cargo,max_steps=100)
    def test_nested_alias_resolves(self):
        c,r=self.cargo();code,adapter=self.run_slot(self.args(),{'halted':True})
        self.assertEqual(code,0);self.assertEqual(adapter.run_native.call_args.args[0],str(c))
    def test_stored_alias_resolves(self):
        self.cargo();code,_=self.run_slot(self.args('_alias/a.mssl'),{'halted':True});self.assertEqual(code,0)
    def test_native_failure_nonzero(self):
        self.cargo();code,_=self.run_slot(self.args(),{'halted':False,'status':'TRAP'});self.assertEqual(code,1)
    def test_unlisted_cargo_not_executed(self):
        self.cargo()
        with mock.patch.object(E,'bind') as b,contextlib.redirect_stdout(io.StringIO()):code=cli.cmd_slot_run(self.args('unlisted.mssl'));b.assert_not_called()
        self.assertEqual(code,2)
    def test_wrong_slot_not_executed(self):
        self.cargo()
        with mock.patch.object(E,'bind') as b,contextlib.redirect_stdout(io.StringIO()):code=cli.cmd_slot_run(self.args(slot='DF_Medium'));b.assert_not_called()
        self.assertEqual(code,2)
    def test_changed_cargo_not_executed(self):
        c,_=self.cargo();c.write_text('ALTERED\n')
        with mock.patch.object(E,'bind') as b,contextlib.redirect_stdout(io.StringIO()):code=cli.cmd_slot_run(self.args());b.assert_not_called()
        self.assertEqual(code,3)
    def test_mount_registry_corruption_refused(self):
        p=self.p/'_studio/uc_mounts.json';p.parent.mkdir();p.write_text('{broken')
        with self.assertRaises(Refusal):HM.read_registry()
    def test_missing_mount_registry_empty(self):self.assertEqual(HM.read_registry()['mounts'],{})
    def test_studio_test_failure_code(self):
        from unikernel import studio_face
        with mock.patch.object(studio_face,'test_all',return_value={'ok':False}),contextlib.redirect_stdout(io.StringIO()):code=cli.cmd_studio_test(None)
        self.assertEqual(code,1)
    def test_studio_test_skip_code(self):
        from unikernel import studio_face
        with mock.patch.object(studio_face,'test_all',return_value={'skipped':'not installed'}),contextlib.redirect_stdout(io.StringIO()):code=cli.cmd_studio_test(None)
        self.assertEqual(code,3)
    def test_studio_register_failure_code(self):
        from unikernel import studio_face
        with mock.patch.object(studio_face,'register',return_value={'ok':False}),contextlib.redirect_stdout(io.StringIO()):code=cli.cmd_studio_register(types.SimpleNamespace(name='demo'))
        self.assertEqual(code,1)
    def test_inventory_rejects_fifo(self):
        if not hasattr(os,'mkfifo'): self.skipTest('OS does not expose mkfifo')
        os.mkfifo(self.p/'pipe')
        with self.assertRaises(Refusal):M.walk(str(self.p))

class RealTIFF(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('uc_test_codec',ROOT/'hull/pa21studio/fabric_tif.py')
        cls.codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.codec)
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name)/'fabric.tif'
        patch=mock.patch.object(TF,'codec',return_value=self.codec);patch.start();self.addCleanup(patch.stop)
        self.blob=self.codec.build_blob({'version':1,'monotonic':0,'clock':0,'slots':[b'']*8})
        self.codec.write_tif(self.blob,str(self.p),tick=0)
    def test_valid_image_admitted(self):TF._validate_tif(str(self.p))
    def test_atomic_append_roundtrip(self):
        r=TF._write_next(str(self.p),self.blob,1);self.assertEqual(r['pages'],2)
        self.assertEqual(self.codec.read_tif(str(self.p))['blob'],self.blob)
    def test_history_limit_before_append(self):
        with mock.patch.object(TF,'MAX_TIF_PAGES',1):
            with self.assertRaises(Refusal):TF._write_next(str(self.p),self.blob,1)
        self.assertEqual(self.codec.read_tif(str(self.p))['pages'],1)
    def test_history_limit_read(self):
        TF._write_next(str(self.p),self.blob,1)
        with mock.patch.object(TF,'MAX_TIF_PAGES',1):
            with self.assertRaises(Refusal):TF._validate_tif(str(self.p))
    def test_tiff_write_error_preserves_old(self):
        original=self.p.read_bytes()
        with mock.patch.object(self.codec,'write_tif',side_effect=OSError('injected')):
            with self.assertRaises(OSError):TF._write_next(str(self.p),self.blob,1)
        self.assertEqual(self.p.read_bytes(),original);self.assertFalse(list(self.p.parent.glob('.uc-tif-*')))

class CompletenessGate(unittest.TestCase):
    """Exercise the real CLI result policy with synthetic gate records."""
    def result(self, strict, *, verdict='PASS', skipped=False):
        from unikernel import gates
        record={'totals':{'passed':1,'failed':int(verdict != 'PASS'),'skipped':0,'wall_seconds':0},
                'verdict':verdict,'gates':[{'id':'U1','status':'PASS'}],
                'berths':{'sample':{'gates':[{'id':'B11','status':'SKIPPED' if skipped else 'PASS'}]}}}
        with tempfile.TemporaryDirectory() as td:
            args=types.SimpleNamespace(berth=None,out=str(Path(td)/'result.json'),quick=True,
                                       no_hull=True,require_complete=strict)
            with mock.patch.object(gates,'run_ship_battery',return_value=record), contextlib.redirect_stdout(io.StringIO()):
                return cli.cmd_verify(args)
    def test_complete_success(self): self.assertEqual(self.result(True),0)
    def test_nested_skip_blocks_strict(self): self.assertEqual(self.result(True,skipped=True),3)
    def test_legacy_mode_reports_but_permits_skip(self): self.assertEqual(self.result(False,skipped=True),0)
    def test_failure_takes_precedence(self): self.assertEqual(self.result(True,verdict='FAIL',skipped=True),1)

if __name__=='__main__':unittest.main()
