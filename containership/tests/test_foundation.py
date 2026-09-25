"""UC-2.3.0 executable foundation checks, including real process-crash recovery.
No test in this file claims guest boot, hardware isolation or remote trust.
"""
from __future__ import annotations
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import random
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'ship'))
from unikernel import Refusal, strictjson as J, contracts as C, artifacts as A
from unikernel import transactions as T, control_store as CS, supervisor as P, engines as E, cli

class Temp(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
    def file(self,rel,data=b'old'):
        p=self.root/rel;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(data.encode() if isinstance(data,str) else data);return p
    def request(self,**updates):
        return {'schema':C.SCHEMA,'operation':'invoke','workload':'demo','generation':1,
                'isolation':'host-process','capabilities':['native-interpretation']}|updates

class StrictJSON(Temp):
    def test_valid_roundtrip(self):
        value={'text':'café [test]','nested':[1,True,None,2.5]}
        self.assertEqual(J.loads(J.dumps(value)),value)
    def test_canonical_order(self):self.assertEqual(J.canonical_bytes({'b':2,'a':1}),b'{"a":1,"b":2}')
    def test_canonical_order_property(self):
        r=random.Random(230)
        for _ in range(100):
            pairs=[(str(n),r.randrange(100000)) for n in range(30)]
            a=dict(pairs);r.shuffle(pairs)
            self.assertEqual(J.canonical_bytes(a),J.canonical_bytes(dict(pairs)))
    def test_canonical_not_lossy_unicode_normalization(self):
        self.assertNotEqual(J.canonical_bytes({'v':'e\u0301'}),J.canonical_bytes({'v':'é'}))
    def test_canonical_rejects_float(self):
        with self.assertRaises(Refusal):J.canonical_bytes({'a':1.0})
    def test_canonical_rejects_nonstring_key(self):
        with self.assertRaises(Refusal):J.canonical_bytes({1:'a'})
    def test_byte_bound(self):
        with self.assertRaises(Refusal):J.loads('"123456"',max_bytes=4)
    def test_read_limit(self):
        h=io.StringIO('"'+('x'*100)+'"')
        with self.assertRaises(Refusal):J.load(h,max_bytes=10)
        self.assertEqual(h.tell(),11)
    def test_depth_inside_strings_not_counted(self):self.assertEqual(J.loads('"'+('['*100)+'"'),'['*100)
    def test_decode_override_rejected(self):
        with self.assertRaises(Refusal):J.loads('{}',object_pairs_hook=dict)
    def test_unknown_python_object_not_stringified_canonical(self):
        with self.assertRaises(Refusal):J.canonical_bytes(object())

INVALID_JSON={
 'duplicate_top':'{"x":1,"x":2}', 'duplicate_nested':'{"a":{"x":1,"x":2}}',
 'escaped_duplicate':'{"x":1,"\\u0078":2}', 'nan':'{"x":NaN}',
 'inf':'{"x":Infinity}', 'negative_inf':'{"x":-Infinity}',
 'exponent_overflow':'{"x":1e9999}', 'too_deep':'['*65+'0'+']'*65,
 'huge_integer':'1'*1025, 'trailing_content':'{}{}', 'truncated':'{"a":',
 'bad_utf8':b'"\xff"', 'surrogate':'"\\ud800"', 'bad_syntax':'{a:1}',
 'utf8_bom':b'\xef\xbb\xbf{}', 'leading_zero':'01', 'trailing_comma':'[1,]',
}
for key,text in INVALID_JSON.items():
    def test(self,text=text):
        with self.assertRaises(Refusal):J.loads(text)
    setattr(StrictJSON,'test_refuse_'+key,test)

class ContractTests(Temp):
    def test_valid(self):self.assertEqual(C.validate_request(self.request())['operation'],'invoke')
    def test_bool_generation(self):
        with self.assertRaises(Refusal):C.validate_request(self.request(generation=True))
    def test_unknown_field(self):
        with self.assertRaises(Refusal):C.validate_request(self.request(authority='operator'))
    def test_version(self):
        with self.assertRaises(Refusal):C.validate_request(self.request(schema='UC/CONTROL_REQUEST/99'))
    def test_duplicate_cap(self):
        with self.assertRaises(Refusal):C.validate_request(self.request(capabilities=['inspect','inspect']))
    def test_unsupported_cap(self):
        with self.assertRaises(Refusal):C.validate_request(self.request(capabilities=['host-root']))
    def test_stronger_backend_refused(self):
        with self.assertRaises(Refusal):C.require_backend('hypervisor')
    def test_no_false_network_guarantee(self):self.assertFalse(C.capabilities()['network_policy_enforced'])
    def test_different_assurance_fields(self):self.assertEqual(len(set(C.ASSURANCES)),5)
    def test_unknown_operation(self):
        with self.assertRaises(Refusal):C.validate_request(self.request(operation='exec-shell'))
    def test_large_generation(self):
        with self.assertRaises(Refusal):C.validate_request(self.request(generation=2**63))

class GraphTests(Temp):
    def graph(self):
        return {'schema':'UC/ARTIFACT_GRAPH/1','nodes':[
            {'id':'source','kind':'source','sha256':'a'*64,'dependencies':[]},
            {'id':'image','kind':'image','sha256':'b'*64,'dependencies':['source']},
            {'id':'evidence','kind':'evidence','sha256':'c'*64,'dependencies':['image']},
            {'id':'other','kind':'source','sha256':'d'*64,'dependencies':[]}]}
    def test_dependency_order(self):
        r=A.validate_graph(self.graph());self.assertLess(r['order'].index('source'),r['order'].index('image'))
    def test_exact_invalidation(self):self.assertEqual(A.affected(self.graph(),['image']),['image','evidence'])
    def test_unaffected(self):self.assertEqual(A.affected(self.graph(),['other']),['other'])
    def test_cycle(self):
        g=self.graph();g['nodes'][0]['dependencies']=['evidence']
        with self.assertRaises(Refusal):A.validate_graph(g)
    def test_missing(self):
        g=self.graph();g['nodes'][0]['dependencies']=['missing']
        with self.assertRaises(Refusal):A.validate_graph(g)
    def test_duplicate_node(self):
        g=self.graph();g['nodes'].append(dict(g['nodes'][0]))
        with self.assertRaises(Refusal):A.validate_graph(g)
    def test_duplicate_edge(self):
        g=self.graph();g['nodes'][1]['dependencies']=['source','source']
        with self.assertRaises(Refusal):A.validate_graph(g)
    def test_unknown_changed(self):
        with self.assertRaises(Refusal):A.affected(self.graph(),['missing'])
    def test_bad_digest(self):
        g=self.graph();g['nodes'][0]['sha256']='../a'
        with self.assertRaises(Refusal):A.validate_graph(g)
    def test_unknown_kind(self):
        g=self.graph();g['nodes'][0]['kind']='code-to-run'
        with self.assertRaises(Refusal):A.validate_graph(g)
    def test_unknown_fields(self):
        g=self.graph();g['nodes'][0]['command']='sh'
        with self.assertRaises(Refusal):A.validate_graph(g)
    def test_long_acyclic_graph_no_recursion(self):
        nodes=[{'id':f'n{i}','kind':'source','sha256':'a'*64,'dependencies':[f'n{i-1}'] if i else []} for i in range(1000)]
        self.assertEqual(len(A.validate_graph({'schema':'UC/ARTIFACT_GRAPH/1','nodes':nodes})['order']),1000)

class Objects(Temp):
    def store(self):return A.ObjectStore(self.root)
    def test_publish_and_verify(self):
        rec=self.store().put(b'hello');self.assertEqual(self.store().read(rec['sha256']),b'hello')
    def test_dedupe_no_overwrite(self):
        a=self.store().put(b'hello');b=self.store().put(b'hello');self.assertTrue(a['created']);self.assertFalse(b['created'])
    def test_tamper_refused(self):
        s=self.store();r=s.put(b'hello');s.path(r['sha256']).write_bytes(b'evil!')
        with self.assertRaises(Refusal):s.read(r['sha256'])
    def test_tampered_existing_not_overwritten(self):
        s=self.store();r=s.put(b'hello');s.path(r['sha256']).write_bytes(b'evil!')
        with self.assertRaises(Refusal):s.put(b'hello')
        self.assertEqual(s.path(r['sha256']).read_bytes(),b'evil!')
    def test_invalid_id(self):
        with self.assertRaises(Refusal):self.store().read('../outside')
    def test_capacity_before_write(self):
        with mock.patch.object(shutil,'disk_usage',return_value=types.SimpleNamespace(free=0)):
            with self.assertRaises(Refusal):self.store().put(b'hello')
        self.assertFalse(self.store().path(hashlib.sha256(b'hello').hexdigest()).exists())
    def test_atomic_publish_failure_not_partial(self):
        with mock.patch('unikernel.safety.os.replace',side_effect=OSError('injected')):
            with self.assertRaises(OSError):self.store().put(b'hello')
        self.assertFalse(self.store().path(hashlib.sha256(b'hello').hexdigest()).exists())
    @unittest.skipUnless(hasattr(os,'symlink'),'requires symlink support')
    def test_link_refused(self):
        target=self.file('elsewhere');p=self.store().path('a'*64);p.parent.mkdir(parents=True);p.symlink_to(target)
        with self.assertRaises(Refusal):self.store().read('a'*64)

class Lifecycle(Temp):
    def store(self):return CS.ControlStore(self.root)
    def test_identity_survives_reopen(self):
        s=self.store();t=s.begin('demo','load');s.finish(t,True,observed='staged')
        r=self.store().inspect('demo')['workloads'][0];self.assertEqual(t['workload_id'],r['workload_id'])
    def test_generation_monotonic(self):
        s=self.store();t=s.begin('demo','load');s.finish(t,True,observed='staged')
        u=s.begin('demo','load',expected=t['generation'],invalidate=True)
        self.assertGreater(u['generation'],t['generation']);self.assertEqual(u['workload_id'],t['workload_id'])
    def test_stale_begin_refused(self):
        s=self.store();t=s.begin('demo','load');s.finish(t,True,observed='staged')
        with self.assertRaises(Refusal):s.begin('demo','run',expected=99)
    def test_stale_result_refused(self):
        s=self.store();t=s.begin('demo','run');s.recover('demo','test')
        with self.assertRaises(Refusal):s.finish(t,True)
    def test_overlapping_operation_refused(self):
        s=self.store();s.begin('demo','run')
        with self.assertRaises(Refusal):s.begin('demo','run')
    def test_completed_result_cannot_replay(self):
        s=self.store();t=s.begin('demo','run');s.finish(t,True)
        with self.assertRaises(Refusal):s.finish(t,True)
    def test_ready_not_assumed_from_completion(self):
        s=self.store();t=s.begin('demo','run')
        with self.assertRaises(Refusal):s.finish(t,True,observed='ready')
    def test_failure_records_no_running(self):
        s=self.store();t=s.begin('demo','run');s.finish(t,False)
        self.assertEqual(s.inspect('demo')['workloads'][0]['observed'],'failed')
    def test_transition_requires_reason(self):
        with self.assertRaises(Refusal):self.store().transition('demo',1,'staged',reason='',evidence='e')
    def test_illegal_transition_rejected(self):
        with self.assertRaises(Refusal):self.store().transition('demo',1,'running',reason='r',evidence='e')
    def test_unknown_database_version(self):
        s=self.store();s.path.parent.mkdir(parents=True)
        with sqlite3.connect(s.path) as db:db.execute('PRAGMA user_version=99')
        with self.assertRaises(Refusal):s.inspect()
    def test_event_budget_rolls_back_state(self):
        s=self.store()
        with mock.patch.object(CS,'MAX_EVENTS',0):
            with self.assertRaises(Refusal):s.begin('demo','run')
        self.assertEqual(s.inspect()['workloads'],[])
    def test_read_empty_does_not_create_database(self):
        s=self.store();self.assertEqual(s.inspect()['events'],[]);self.assertFalse(s.path.exists())
    def test_generated_legal_and_illegal_sequences(self):
        rng=random.Random(230)
        s=self.store();token=s.begin('demo','load');s.finish(token,True,observed='staged')
        current='staged'
        for index in range(250):
            target=rng.choice(sorted(CS.STATES))
            if target in CS.TRANSITIONS[current]:
                s.transition('demo',1,target,reason=f'fixture-{index}',evidence='unit-generated-model-only');current=target
            else:
                with self.assertRaises(Refusal):s.transition('demo',1,target,reason='invalid',evidence='unit-generated-model-only')
            self.assertEqual(s.inspect('demo',1)['workloads'][0]['observed'],current)

class Transactions(Temp):
    def snapshot(self,paths=None,name=None):
        s=T.Snapshot(self.root);s.prepare(paths or ['registry','MANIFEST.json'],command='test',name=name)
        s.record['status']='EXECUTING';s.save();return s
    def test_restore_file_directory_empty_directory(self):
        self.file('registry/a','A');(self.root/'registry/empty').mkdir();self.file('MANIFEST.json','M')
        s=self.snapshot();self.file('registry/a','bad');self.file('registry/b','new');(self.root/'MANIFEST.json').unlink()
        s.rollback();self.assertEqual((self.root/'registry/a').read_text(),'A');self.assertFalse((self.root/'registry/b').exists());self.assertTrue((self.root/'registry/empty').is_dir());self.assertEqual((self.root/'MANIFEST.json').read_text(),'M')
    def test_absent_original_new_files_retained(self):
        s=self.snapshot();self.file('registry/new','new');s.rollback()
        self.assertFalse((self.root/'registry').exists());self.assertTrue(any(p.name=='new' for p in (s.home/'displaced').rglob('*')))
    def test_corrupt_backup_refused_before_mutation(self):
        self.file('MANIFEST.json','old');s=self.snapshot(['MANIFEST.json']);self.file('MANIFEST.json','new');(s.home/'backup/0').write_text('bad')
        with self.assertRaises(Refusal):s.rollback()
        self.assertEqual((self.root/'MANIFEST.json').read_text(),'new')
    def test_pending_blocks_other_mutation(self):
        s=self.snapshot()
        with self.assertRaises(Refusal):T.ensure_clean(self.root)
    def test_finished_does_not_block(self):
        s=self.snapshot();s.commit();T.ensure_clean(self.root)
    def test_committed_rollback_is_not_silently_allowed(self):
        s=self.snapshot();s.commit()
        with self.assertRaises(Refusal):s.rollback()
    def test_recovery_idempotent(self):
        self.file('MANIFEST.json','old');s=self.snapshot(['MANIFEST.json']);self.file('MANIFEST.json','new');s.rollback();s.rollback();self.assertEqual((self.root/'MANIFEST.json').read_text(),'old')
    def test_paths_escape_refused(self):
        with self.assertRaises(Refusal):self.snapshot(['../outside'])
    def test_overlapping_paths_refused(self):
        with self.assertRaises(Refusal):self.snapshot(['berths','berths/demo'])
    def test_journal_plan_tamper_refused(self):
        s=self.snapshot();s.record['resources'][0]['resource']='../outside';s.save()
        with self.assertRaises(Refusal):s.rollback()
    def test_journal_id_tamper_refused(self):
        s=self.snapshot();s.record['id']='0'*32;s.save()
        with self.assertRaises(Refusal):s.read()
    def test_bad_transaction_identifier(self):
        with self.assertRaises(Refusal):T.Snapshot(self.root,'../outside')
    def test_low_space_refused_before_mutation(self):
        self.file('MANIFEST.json','old')
        with mock.patch.object(shutil,'disk_usage',return_value=types.SimpleNamespace(free=1)):
            with self.assertRaises(Refusal):self.snapshot()
        self.assertEqual((self.root/'MANIFEST.json').read_text(),'old');self.assertEqual(T.list_transactions(self.root),[])
    def test_recovery_low_space_preserves_both(self):
        self.file('MANIFEST.json','old');s=self.snapshot(['MANIFEST.json']);self.file('MANIFEST.json','new')
        with mock.patch.object(shutil,'disk_usage',return_value=types.SimpleNamespace(free=1)):
            with self.assertRaises(Refusal):s.rollback()
        self.assertEqual((self.root/'MANIFEST.json').read_text(),'new');self.assertEqual((s.home/'backup/0').read_text(),'old')
    def test_copy_enospc_leaves_preparation_recoverable(self):
        self.file('MANIFEST.json','old');s=T.Snapshot(self.root)
        with mock.patch.object(T,'_copy',side_effect=OSError(28,'No space left')):
            with self.assertRaises(OSError):s.prepare(['MANIFEST.json'],command='test')
        self.assertEqual(s.read()['status'],'PREPARING');s.rollback();self.assertEqual((self.root/'MANIFEST.json').read_text(),'old')
    def test_interrupted_recovery_repeats(self):
        self.file('MANIFEST.json','old');s=self.snapshot(['MANIFEST.json']);self.file('MANIFEST.json','new')
        original=os.replace;count=[0]
        def replace(src,dst):
            if str(dst).endswith('MANIFEST.json'):
                count[0]+=1
                if count[0]==1:raise OSError('injected restore interruption')
            return original(src,dst)
        with mock.patch.object(os,'replace',side_effect=replace):
            with self.assertRaises(OSError):s.rollback()
        s.rollback();self.assertEqual((self.root/'MANIFEST.json').read_text(),'old')
    def test_generation_changes_on_recovery(self):
        self.file('berths/demo/BERTH.json','{}');s=self.snapshot(['berths/demo'],name='demo')
        token=CS.ControlStore(self.root).begin('demo','run');s.record['token']=token;s.save()
        s.rollback();state=CS.ControlStore(self.root).inspect('demo')['workloads'][0]
        self.assertGreater(state['generation'],token['generation']);self.assertIsNone(state['active_operation'])
    def test_no_generation_created_for_preparation_failure(self):
        s=T.Snapshot(self.root);s.prepare(['MANIFEST.json'],command='test',name='demo');s.rollback()
        self.assertFalse(CS.ControlStore(self.root).path.exists())
    @unittest.skipUnless(hasattr(os,'symlink'),'requires symlink support')
    def test_symlink_resource_rejected(self):
        self.file('real/a');(self.root/'registry').symlink_to(self.root/'real',target_is_directory=True)
        with self.assertRaises(Refusal):self.snapshot()
    def test_wrapper_nonzero_restores(self):
        self.file('MANIFEST.json','old')
        args=types.SimpleNamespace(cmd='seal',name=None)
        def fail(a):self.file('MANIFEST.json','new');print('FAILED');return 1
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):code=T.execute(self.root,args,fail)
        self.assertEqual(code,1);self.assertEqual((self.root/'MANIFEST.json').read_text(),'old')
    def test_wrapper_exception_restores(self):
        self.file('MANIFEST.json','old');args=types.SimpleNamespace(cmd='seal',name=None)
        def fail(a):self.file('MANIFEST.json','new');raise OSError('injected')
        with self.assertRaises(OSError):T.execute(self.root,args,fail)
        self.assertEqual((self.root/'MANIFEST.json').read_text(),'old')

# Each case terminates a real independent process at a different mutation point.
for boundary in range(5):
    def test_crash(self,boundary=boundary):
        self.file('registry/a','OLD-A');self.file('MANIFEST.json','OLD-M');self.file('SHA256SUMS.txt','OLD-S')
        code='''import os,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from unikernel.transactions import Snapshot
root=Path(sys.argv[2]); stop=int(sys.argv[3])
s=Snapshot(root);s.prepare(['registry','MANIFEST.json','SHA256SUMS.txt'],command='fault')
if stop==0:os._exit(73)
s.record['status']='EXECUTING';s.save()
for i,(name,data) in enumerate([('registry/a','NEW-A'),('MANIFEST.json','NEW-M'),('SHA256SUMS.txt','NEW-S')],1):
 (root/name).write_text(data)
 if stop==i:os._exit(73)
os._exit(73)
'''
        p=subprocess.run([sys.executable,'-B','-c',code,str(ROOT/'ship'),str(self.root),str(boundary)],capture_output=True,timeout=15)
        self.assertEqual(p.returncode,73,p.stderr.decode());records=T.list_transactions(self.root);self.assertEqual(len(records),1)
        with self.assertRaises(Refusal):T.ensure_clean(self.root)
        T.Snapshot(self.root,records[0]['id']).rollback()
        self.assertEqual((self.root/'registry/a').read_text(),'OLD-A');self.assertEqual((self.root/'MANIFEST.json').read_text(),'OLD-M');self.assertEqual((self.root/'SHA256SUMS.txt').read_text(),'OLD-S')
    setattr(Transactions,f'test_actual_process_crash_boundary_{boundary}',test_crash)

class Supervisor(Temp):
    def test_normal_result(self):
        r=P.run([sys.executable,'-c','print(123)'],cwd=self.root,timeout=5)
        self.assertEqual(r['returncode'],0);self.assertEqual(r['stdout'].strip(),'123')
    def test_failure_result(self):
        r=P.run([sys.executable,'-c','raise SystemExit(7)'],cwd=self.root,timeout=5);self.assertEqual(r['returncode'],7)
    def test_timeout(self):
        r=P.run([sys.executable,'-c','import time;time.sleep(10)'],cwd=self.root,timeout=.1);self.assertTrue(r['timed_out']);self.assertEqual(r['returncode'],124)
    def test_output_flood_bound(self):
        r=P.run([sys.executable,'-c','import sys;sys.stdout.write("x"*2000000)'],cwd=self.root,timeout=5,max_output=1024)
        self.assertTrue(r['output_limited']);self.assertEqual(r['returncode'],125);self.assertLessEqual(len(r['stdout']),1024)
    def test_invalid_vector(self):
        with self.assertRaises(Refusal):P.run('echo hello',cwd=self.root)
    def test_invalid_deadline(self):
        with self.assertRaises(Refusal):P.run(['echo'],cwd=self.root,timeout=float('nan'))
    @unittest.skipUnless(os.name=='posix','POSIX process-group test')
    def test_descendant_cannot_write_after_timeout(self):
        marker=self.root/'orphan'
        child='import time,pathlib;time.sleep(1);pathlib.Path('+repr(str(marker))+').write_text("bad")'
        parent='import subprocess,sys,time;subprocess.Popen([sys.executable,"-c",'+repr(child)+']);time.sleep(10)'
        r=P.run([sys.executable,'-c',parent],cwd=self.root,timeout=.15)
        import time;time.sleep(1.1)
        self.assertFalse(marker.exists());self.assertTrue(r['timed_out'])

class NewCLI(Temp):
    def call(self,args):
        with mock.patch.object(E,'SHIP',str(self.root)),contextlib.redirect_stdout(io.StringIO()) as out,contextlib.redirect_stderr(io.StringIO()):
            rc=cli.main(args)
        return rc,out.getvalue()
    def test_hypervisor_required_blocks_before_run(self):
        with mock.patch.object(E,'bind') as b:
            rc,_=self.call(['run','demo','--require-isolation','hypervisor']);b.assert_not_called()
        self.assertEqual(rc,3);self.assertFalse((self.root/'_runs/managed_tx').exists())
    def test_stale_generation_blocks_before_run(self):
        rc,_=self.call(['run','demo','--generation','99']);self.assertEqual(rc,3);self.assertFalse((self.root/'_runs/managed_tx').exists())
    def test_capabilities_machine_output(self):
        rc,text=self.call(['capabilities']);self.assertEqual(rc,0);self.assertEqual(json.loads(text)['isolation_class'],'host-process')
    def test_contract_duplicate_input(self):
        f=self.file('request.json','{"schema":1,"schema":2}')
        rc,_=self.call(['contract-check',str(f)]);self.assertEqual(rc,3)
    def test_contract_boot_not_executed(self):
        f=self.file('request.json',json.dumps(self.request(operation='boot')))
        rc,text=self.call(['contract-check',str(f)]);self.assertEqual(rc,3);self.assertFalse(json.loads(text)['executed'])
    def test_recover_unknown_id(self):
        rc,_=self.call(['recover','inspect','../outside']);self.assertEqual(rc,3)
    def test_empty_lifecycle(self):
        rc,text=self.call(['lifecycle','demo']);self.assertEqual(rc,0);self.assertEqual(json.loads(text)['workloads'],[])
    def test_nonfinite_refusal_is_valid_json(self):
        rc,text=self.call(['run','demo','--interval','nan']);self.assertEqual(rc,3);self.assertEqual(json.loads(text)['detail']['interval'],'nan')

if __name__=='__main__':unittest.main()

class ExtraInputGuards(Temp):
    def test_operation_wrong_type(self):
        with self.assertRaises(Refusal):C.validate_request(self.request(operation=[]))
    def test_isolation_wrong_type(self):
        with self.assertRaises(Refusal):C.validate_request(self.request(isolation={}))
    def test_copy_enforces_byte_limit_during_read(self):
        src=self.file('src',b'123456789')
        with mock.patch.object(T,'MAX_SNAPSHOT',4),self.assertRaises(Refusal):T._copy(src,self.root/'dst')
    def test_resource_wrong_type(self):
        with self.assertRaises(Refusal):T._resource([])
    def test_read_refuses_nonobject_journal(self):
        tx=T.Snapshot(self.root);tx.home.mkdir(parents=True);tx.journal.write_text('[]')
        with self.assertRaises(Refusal):tx.read()
    def test_subprocess_env_is_explicit(self):
        r=P.run([sys.executable,'-c','import os;print(os.environ.get("UC_PROBE"))'],env=dict(os.environ,UC_PROBE='controlled'),cwd=self.root)
        self.assertEqual(r['returncode'],0);self.assertEqual(r['stdout'].strip(),'controlled')

class WorkflowTrace(Temp):
    def setUp(self):
        super().setUp()
        from unikernel import workflow as W
        self.W=W;self.base=self.root/'workflow';self.base.mkdir()
        # Hard links are only in the disposable test fixture. Mutations replace
        # fixture files, never write through to the source package.
        for name in ('series.zip','APPLICATION.json','ledger.jsonl.gz'):
            try:os.link(ROOT/'workflow'/name,self.base/name)
            except OSError:shutil.copyfile(ROOT/'workflow'/name,self.base/name)
    def replace(self,name,data):
        p=self.base/name;p.unlink();p.write_bytes(data)
    def meta(self,**changes):
        r=json.loads((self.base/'APPLICATION.json').read_text());r.update(changes)
        self.replace('APPLICATION.json',json.dumps(r).encode())
    def test_complete_source_and_ledger_accounting(self):
        r=self.W.check(self.root)
        self.assertEqual(r['tasks'],96000);self.assertFalse(r['engineering_completion_verified'])
    def test_show_preserves_original_statement(self):
        r=self.W.show(self.root,'UC-M01.04-C002-T03')
        self.assertIn('duplicate',r['source']['text'].lower());self.assertEqual(r['application_pass']['status'],'IN_PROGRESS')
    def test_refuse_source_replacement(self):
        self.replace('series.zip',b'invalid series')
        with self.assertRaisesRegex(Refusal,'series bytes'):self.W.check(self.root)
    def test_refuse_ledger_replacement(self):
        self.replace('ledger.jsonl.gz',b'not a ledger')
        with self.assertRaisesRegex(Refusal,'ledger digest'):self.W.check(self.root)
    def test_refuse_incompatible_version(self):
        self.meta(schema='UC/WORKFLOW_APPLICATION/99')
        with self.assertRaises(Refusal):self.W.status(self.root)
    def test_refuse_claimed_count_change(self):
        self.meta(task_status_counts={'DONE':96000})
        with self.assertRaisesRegex(Refusal,'status summary'):self.W.check(self.root)
    def test_bad_task_id(self):
        with self.assertRaises(Refusal):self.W.show(self.root,'../../outside')
    def test_truncated_line(self):
        with self.assertRaises(Refusal):list(self.W._rows(io.BytesIO(b'{}')))
    def test_line_bound(self):
        with self.assertRaises(Refusal):list(self.W._rows(io.BytesIO(b' '*65537+b'\n')))
    def test_duplicate_field(self):
        with self.assertRaises(Refusal):list(self.W._rows(io.BytesIO(b'{"id":"a","id":"b"}\n')))
    def test_done_is_not_promoted_by_hash_recalculation(self):
        import gzip
        data=gzip.decompress((self.base/'ledger.jsonl.gz').read_bytes());first,rest=data.split(b'\n',1)
        rec=json.loads(first);rec['status']='DONE'
        new=gzip.compress(json.dumps(rec).encode()+b'\n'+rest,mtime=0)
        self.replace('ledger.jsonl.gz',new);self.meta(ledger_sha256=hashlib.sha256(new).hexdigest())
        with self.assertRaisesRegex(Refusal,'no individually promoted'):self.W.check(self.root)

class CommitReportBarrier(Temp):
    def args(self):return types.SimpleNamespace(cmd='seal',out=str(self.root/'_runs'/'export.json'))
    def mutate(self,a):
        self.file('registry/x','new');Path(a.out).write_text('{"verdict":"PASS"}')
        return 0
    def test_report_published_after_commit(self):
        self.file('registry/x');a=self.args()
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):self.assertEqual(T.execute(self.root,a,self.mutate),0)
        r=json.loads(Path(a.out).read_text());self.assertEqual(r['managed_transaction']['status'],'COMMITTED')
    def test_commit_failure_does_not_publish_success(self):
        self.file('registry/x');a=self.args();self.file('_runs/export.json','previous')
        with mock.patch.object(T.Snapshot,'commit',side_effect=OSError('commit failure')),self.assertRaises(OSError):T.execute(self.root,a,self.mutate)
        self.assertEqual(Path(a.out).read_text(),'previous');self.assertEqual((self.root/'registry/x').read_bytes(),b'old')
    def test_failure_report_is_explicitly_rolled_back(self):
        self.file('registry/x');a=self.args()
        def bad(args):self.mutate(args);return 1
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):self.assertEqual(T.execute(self.root,a,bad),1)
        self.assertEqual(json.loads(Path(a.out).read_text())['managed_transaction']['status'],'ROLLED_BACK')
        self.assertEqual((self.root/'registry/x').read_bytes(),b'old')
    def test_output_cannot_overwrite_source(self):
        a=self.args();a.out=str(self.root/'MANIFEST.json')
        with self.assertRaises(Refusal):T.execute(self.root,a,lambda _:0)
        self.assertFalse((self.root/'_runs/managed_tx').exists())
    def test_output_cannot_overwrite_control(self):
        a=self.args();a.out=str(self.root/'_runs/control/state.sqlite')
        with self.assertRaises(Refusal):T.execute(self.root,a,lambda _:0)
    def test_failed_report_publish_cannot_undo_commit(self):
        self.file('registry/x');a=self.args()
        original=T.atomic_json
        def fail(path,value):
            if Path(path)==Path(a.out):raise OSError('report disk failure')
            return original(path,value)
        with mock.patch.object(T,'atomic_json',side_effect=fail),contextlib.redirect_stderr(io.StringIO()) as err,self.assertRaises(OSError):T.execute(self.root,a,self.mutate)
        self.assertIn('COMMITTED',err.getvalue());self.assertEqual((self.root/'registry/x').read_bytes(),b'new')
        self.assertEqual(T.list_transactions(self.root)[0]['status'],'COMMITTED')
    def test_finish_checks_legal_predecessor(self):
        s=CS.ControlStore(self.root);t=s.begin('demo','fake')
        with self.assertRaises(Refusal):s.finish(t,True,observed='built')
