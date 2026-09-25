from __future__ import annotations
import json, os, tempfile, unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
import sys; sys.path.insert(0,str(ROOT/'ship'))
from unikernel import Refusal
from unikernel import platform_services as P

class EventAndAuditTests(unittest.TestCase):
    def test_event_order_and_subscriber_isolation(self):
        bus=P.EventBus(max_history=2);seen=[]
        bus.subscribe('ship.test',lambda e:seen.append(e['seq']))
        def bad(_): raise RuntimeError('nope')
        bus.subscribe('ship.test',bad)
        a=bus.publish('ship.test',{'x':1});b=bus.publish('ship.test',{'x':2});bus.publish('ship.test',{'x':3})
        self.assertEqual(seen,[1,2,3]);self.assertEqual(len(a['subscriber_errors']),1);self.assertEqual([r['seq'] for r in bus.history()],[2,3])
    def test_event_limits(self):
        with self.assertRaises(Refusal):P.EventBus().publish('bad topic',{})
        with self.assertRaises(Refusal):P.EventBus().publish('ok',{'x':'x'*(P.MAX_EVENT_BYTES+1)})
    def test_audit_chain_and_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            a=P.AuditLedger(d);r1=a.append('ship.start',{'version':'2.7.0'});r2=a.append('ship.test',{'ok':True})
            self.assertEqual(r2['prev_sha256'],r1['sha256']);self.assertEqual(a.verify()['records'],2)
            p=Path(d)/'_runs/audit/events.jsonl';raw=p.read_text();p.write_text(raw.replace('ship.start','ship.stop',1))
            with self.assertRaises(Refusal):a.verify()

class MetricTests(unittest.TestCase):
    def test_counter_gauge(self):
        m=P.Metrics();self.assertEqual(m.inc('ticks'),1);self.assertEqual(m.inc('ticks',2),3);m.set('depth',4,{'berth':'vm_small'})
        self.assertEqual(m.snapshot()['count'],2)
    def test_invalid(self):
        m=P.Metrics()
        with self.assertRaises(Refusal):m.inc('bad metric')
        with self.assertRaises(Refusal):m.inc('x',-1)

class QueueTests(unittest.TestCase):
    def test_priority_and_duplicate(self):
        q=P.WorkQueue(2);q.submit('a',{'n':1},10);self.assertFalse(q.submit('a',{'n':2})['accepted']);q.submit('b',{'n':2},1)
        self.assertEqual(q.take()['key'],'b');self.assertEqual(q.take()['key'],'a');self.assertIsNone(q.take())
    def test_backpressure(self):
        q=P.WorkQueue(1);q.submit('a',{})
        with self.assertRaises(Refusal):q.submit('b',{})

class ConfigTests(unittest.TestCase):
    def test_flags(self):self.assertEqual(P.validate_feature_flags({'b':False,'a':True}),{'a':True,'b':False})
    def test_flags_reject_nonbool(self):
        with self.assertRaises(Refusal):P.validate_feature_flags({'x':1})
    def test_quotas(self):self.assertEqual(P.validate_quotas({'memory_bytes':1024}),{'memory_bytes':1024})
    def test_unknown_quota(self):
        with self.assertRaises(Refusal):P.validate_quotas({'magic':1})

class HardwareTests(unittest.TestCase):
    def test_shape(self):
        r=P.hardware_capabilities();self.assertEqual(r['schema'],'UC/HARDWARE_CAPABILITIES/1');self.assertGreaterEqual(r['logical_cpu_count'],1)
        self.assertFalse(r['gpu_qualified'])
    def test_compatibility_is_conservative(self):
        r=P.compatibility_matrix();self.assertEqual(r['candidate'],'UC-2.8.0');self.assertTrue(r['unqualified'])

class HealthTests(unittest.TestCase):
    def test_ready(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'ship/unikernel').mkdir(parents=True);(p/'MANIFEST.json').write_text('{}');(p/'VERSION').write_text('2.7.0');(p/'ship/unikernel/__init__.py').write_text('')
            self.assertTrue(P.health_snapshot(d)['ready'])

class TraceAndCapacityTests(unittest.TestCase):
    def test_trace(self):
        tr=P.TraceRecorder(4);a=tr.start('ship.request');b=tr.start('ship.child',a);tr.finish(b);tr.finish(a,'ok')
        s=tr.snapshot();self.assertEqual(s['open'],0);self.assertEqual(len(s['completed']),2)
    def test_trace_bad_parent(self):
        with self.assertRaises(Refusal):P.TraceRecorder().start('x','missing')
    def test_structured_log(self):
        r=P.structured_log('ship.ready','info',{'version':'2.7.0'});self.assertEqual(r['schema'],'UC/LOG_EVENT/1')
        with self.assertRaises(Refusal):P.structured_log('x','notice',{})
    def test_capacity(self):
        ok=P.capacity_plan({'memory_bytes':10},{'memory_bytes':20});self.assertTrue(ok['admitted'])
        bad=P.capacity_plan({'memory_bytes':30},{'memory_bytes':20});self.assertFalse(bad['admitted'])
    def test_retention(self):
        self.assertEqual(P.validate_retention_policy({'max_items':5}),{'max_items':5})
        with self.assertRaises(Refusal):P.validate_retention_policy({'max_items':0})
