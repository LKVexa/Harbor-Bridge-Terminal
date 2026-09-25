from __future__ import annotations
import contextlib, hashlib, io, json, math, os, tempfile, unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT/'ship'))
from unikernel import onebit as O
from unikernel import onebit_cli as C
from unikernel import engines as E, tif_fabric as TF


class EncodingTests(unittest.TestCase):
    def test_sign_pack_lsb0(self):
        self.assertEqual(O.pack_signs([1,0,1,1,0,0,0,1]),b'\x8d')
        self.assertEqual(O.unpack_signs(b'\x8d',8),[1,0,1,1,0,0,0,1])
    def test_tail_bits_canonical(self):
        self.assertEqual(O.unpack_signs(b'\x03',2),[1,1])
        with self.assertRaises(O.OneBitError):O.unpack_signs(b'\x83',2)
    def test_onebit_roundtrip(self):
        r=O.encode_onebit([-2,-1,0,1,2],sequence=7,source=3,destination=9)
        d=O.decode_onebit(r['packet'])
        self.assertEqual((d['sequence'],d['source'],d['destination'],d['count']),(7,3,9,5))
        self.assertEqual(d['signs'],[0,0,1,1,1]);self.assertEqual(d['scale'],1.2)
    def test_onebit_corruption_crc(self):
        p=bytearray(O.encode_onebit([-1,1]*10,sequence=0)['packet']);p[-1]^=1
        with self.assertRaises(O.OneBitError):O.decode_onebit(bytes(p))
    def test_onebit_wrong_magic(self):
        p=bytearray(O.encode_onebit([-1,1],sequence=0)['packet']);p[0]=0
        with self.assertRaises(O.OneBitError):O.decode_packet(bytes(p))
    def test_fp32_roundtrip(self):
        p=O.encode_fp32([1.25,-2.5,0],sequence=4,source=1,destination=2)['packet'];d=O.decode_fp32(p)
        self.assertEqual(d['sequence'],4);self.assertEqual(d['values'],[1.25,-2.5,0.0])
    def test_fp32_crc(self):
        p=bytearray(O.encode_fp32([1.0],sequence=0)['packet']);p[-1]^=1
        with self.assertRaises(O.OneBitError):O.decode_fp32(bytes(p))
    def test_packet_deterministic(self):
        a=O.encode_onebit([-3,2,1],sequence=8)['packet'];b=O.encode_onebit([-3,2,1],sequence=8)['packet'];self.assertEqual(a,b)
    def test_nonfinite_refused(self):
        for x in (float('nan'),float('inf'),float('-inf')):
            with self.subTest(x=x),self.assertRaises(O.OneBitError):O.encode_onebit([x],sequence=0)
    def test_budget(self):
        with self.assertRaises(O.OneBitError):O.values([0.0]*(O.MAX_SCALARS+1))


class QuantizerTests(unittest.TestCase):
    def test_scale_mean_abs(self):self.assertEqual(O.estimate_scale([-2,0,4]),2.0)
    def test_zero_block(self):
        q=O.sign_quantize([0,0,0]);self.assertEqual(q['scale'],0);self.assertEqual(q['reconstructed'],[0,0,0])
    def test_zero_sign_is_positive(self):self.assertEqual(O.sign_quantize([-1,0,1])['signs'],[0,1,1])
    def test_zero_scale_nonzero_refused(self):
        with self.assertRaises(O.OneBitError):O.sign_quantize([1],scale=0)
    def test_local_values_remain_float(self):
        q=O.sign_quantize([0.25,-0.5]);self.assertTrue(all(isinstance(x,float) for x in q['residual']))
    def test_error_metric(self):
        q=O.sign_quantize([-2,-1,1,2]);self.assertGreater(q['normalized_rmse'],0);self.assertEqual(q['bit_balance'],0.5)


class WarmupTests(unittest.TestCase):
    def cfg(self):return O.ControllerConfig(warmup_blocks=4,stability_window=4,stability_cv=.001,recovery_blocks=2)
    def test_full_precision_warmup_then_onebit(self):
        c=O.CommunicationController(self.cfg());trans=[]
        for _ in range(5):trans.append(c.transmit([1,-1,1,-1])['transport'])
        self.assertEqual(trans,['fp32']*4+['one_bit']);self.assertEqual(c.state.mode,'ONE_BIT')
    def test_unstable_warmup_stays_full(self):
        c=O.CommunicationController(self.cfg())
        for k in (1,10,1,10,1,10):c.transmit([k,-k])
        self.assertEqual(c.state.mode,'WARMUP')
    def test_sequence_monotonic(self):
        c=O.CommunicationController(self.cfg());self.assertEqual([c.transmit([1,-1])['sequence'] for _ in range(3)],[0,1,2])
    def test_reference_frozen_on_transition(self):
        c=O.CommunicationController(self.cfg())
        for _ in range(4):c.transmit([2,-2])
        self.assertEqual(c.state.reference_scale,2)
    def test_sequence_exhaustion(self):
        s=O.ChannelState(sequence=2**64-1);c=O.CommunicationController(self.cfg(),s)
        with self.assertRaises(O.OneBitError):c.transmit([1,-1])


class IntegrityResidualTests(unittest.TestCase):
    def one(self,**kw):
        cfg=O.ControllerConfig(warmup_blocks=2,stability_window=2,stability_cv=.001,recovery_blocks=2,**kw)
        c=O.CommunicationController(cfg)
        c.transmit([1,-1]);c.transmit([1,-1]);return c
    def test_residual_feedback_state(self):
        c=self.one();r=c.transmit([2,-1]);self.assertEqual(r['transport'],'one_bit');self.assertEqual(len(c.state.residual),2)
    def test_shape_change_resets_residual(self):
        c=self.one();c.transmit([2,-1]);c.transmit([1,-1,1,-1]);self.assertEqual(len(c.state.residual),4)
    def test_low_error_threshold_fallback(self):
        c=self.one(max_error_ratio=.01);r=c.transmit([10,-1]);self.assertEqual(r['transport'],'fp32');self.assertTrue(r['fallback']);self.assertEqual(c.state.mode,'RECOVERY')
    def test_saturation_fallback(self):
        c=self.one();r=c.transmit([1,1]);self.assertTrue(r['fallback']);self.assertIn('bit-balance',r['fallback_reason'])
    def test_checkpoint_roundtrip(self):
        c=self.one();c.transmit([2,-1]);cp=c.checkpoint();d=O.CommunicationController.from_checkpoint(cp);self.assertEqual(d.checkpoint()['sha256'],cp['sha256'])
    def test_checkpoint_tamper(self):
        c=self.one();cp=c.checkpoint();cp['state']['sequence']+=1
        with self.assertRaises(O.OneBitError):O.CommunicationController.from_checkpoint(cp)
    def test_receive_sequence_guard(self):
        c=self.one();p=O.encode_onebit([1,-1],sequence=4)['packet']
        with self.assertRaises(O.OneBitError):c.receive(p,expected_sequence=3)


class RoutingCollectiveTests(unittest.TestCase):
    def test_route_table(self):
        r=O.RouteTable({1:[2,3]});self.assertEqual(r.recipients(1),(2,3));self.assertEqual(r.recipients(9),())
    def test_duplicate_recipient_refused(self):
        with self.assertRaises(O.OneBitError):O.RouteTable({1:[2,2]})
    def test_average_reduce(self):self.assertEqual(O.average_reduce([[1,3],[3,5]]),[2,4])
    def test_reduce_shape_refused(self):
        with self.assertRaises(O.OneBitError):O.average_reduce([[1],[1,2]])
    def test_compressed_average(self):
        r=O.compressed_average([[1,-1,1,-1],[2,-2,2,-2]]);self.assertEqual(r['normalized_error'],0);self.assertEqual(len(r['packets']),2)
    def test_collective_local_reduction_full_precision(self):
        r=O.compressed_average([[.1,-.9],[.2,-.8]]);self.assertTrue(all(isinstance(x,float) for x in r['compressed_reduce']))


class BackendAndTIFFTests(unittest.TestCase):
    def test_memory_backend(self):
        b=O.MemoryBackend();p=O.encode_onebit([-1,1],sequence=0,destination=7)['packet'];b.send(7,p);self.assertEqual(b.receive(7),p)
    def test_memory_backpressure(self):
        b=O.MemoryBackend(1024);p=O.encode_fp32([1.0]*200,sequence=0)['packet'];b.send(1,p)
        with self.assertRaises(O.OneBitError):b.send(1,p)
    def test_memory_rejects_bad_packet(self):
        with self.assertRaises(O.OneBitError):O.MemoryBackend().send(1,b'bad')
    def test_tiff_packet_capacity(self):
        p=O.encode_onebit([1,-1]*(O.MAX_TIFF_ONEBIT_SCALARS//2),sequence=0)['packet'];self.assertLessEqual(len(p),O.TIFF_PACKET_LIMIT)
    def test_tiff_capacity_boundary(self):
        self.assertEqual(O.MAX_TIFF_ONEBIT_SCALARS,3392)
        p=O.encode_onebit([1]*3392,sequence=0)['packet'];self.assertEqual(len(p),464)
        self.assertGreater(len(O.encode_onebit([1]*3393,sequence=0)['packet']),464)
    def test_real_tiff_slot_roundtrip(self):
        t=TF.codec();parts={'version':1,'monotonic':0,'clock':0,'slots':[b'']*8};packet=O.encode_onebit([-1,1]*20,sequence=5)['packet'];parts['slots'][2]=packet
        blob=t.build_blob(parts)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.tif';t.write_tif(blob,p,cols=2,tick=0);r=t.read_tif(p);got=t.parse_blob(r['blob'])['slots'][2]
        self.assertEqual(O.decode_onebit(got)['sequence'],5)


class AdaptiveControlTests(unittest.TestCase):
    def test_config_validation(self):
        with self.assertRaises(O.OneBitError):O.ControllerConfig(warmup_blocks=1).validate()
    def test_scale_step_limiter(self):
        cfg=O.ControllerConfig(warmup_blocks=2,stability_window=2,stability_cv=.001,max_scale_step_ratio=.1,max_error_ratio=10,min_bit_balance=0,max_bit_balance=1)
        c=O.CommunicationController(cfg);c.transmit([1,-1]);c.transmit([1,-1]);r=c.transmit([2,-2]);self.assertLessEqual(r['scale'],1.1+1e-12)
    def test_scale_lower_upper_bounds(self):
        cfg=O.ControllerConfig(warmup_blocks=2,stability_window=2,stability_cv=.001,max_scale_step_ratio=10,max_error_ratio=10,min_bit_balance=0,max_bit_balance=1)
        c=O.CommunicationController(cfg);c.transmit([1,-1]);c.transmit([1,-1]);r=c.transmit([6,-6]);self.assertEqual(r['scale'],4.0)
    def test_momentum_high_precision(self):
        cfg=O.ControllerConfig(warmup_blocks=2,stability_window=2,stability_cv=.001,max_error_ratio=10,min_bit_balance=0,max_bit_balance=1)
        c=O.CommunicationController(cfg);c.transmit([1,-1]);c.transmit([1,-1]);c.transmit([.3,-.7]);self.assertTrue(all(isinstance(x,float) for x in c.state.momentum))
    def test_metrics_account_state_memory(self):
        c=O.CommunicationController(O.ControllerConfig(warmup_blocks=2,stability_window=2,stability_cv=.001));c.transmit([1,-1]);c.transmit([1,-1]);m=c.metrics();self.assertEqual(m['residual_bytes_estimate'],16)


class CapabilityBoundaryTests(unittest.TestCase):
    def test_rule_explicit(self):self.assertEqual(O.capability_record()['rule'],'1-bit communication, not 1-bit cognition')
    def test_network_not_claimed(self):self.assertIn('not implemented',O.capability_record()['network'])
    def test_gpu_not_claimed(self):self.assertEqual(O.capability_record()['gpu'],'not implemented')
    def test_external_not_claimed(self):self.assertIn('JYRM',O.capability_record()['external_adapters'])
    def test_checkpoint_schema(self):self.assertEqual(O.CommunicationController().checkpoint()['schema'],'UC/1BIT_CHANNEL/1')


class TransitionQualityTests(unittest.TestCase):
    def cfg(self):return O.ControllerConfig(warmup_blocks=2,stability_window=2,stability_cv=.001,recovery_blocks=2,max_error_ratio=.01,min_bit_balance=0,max_bit_balance=1)
    def test_fallback_preserves_original_wire_values(self):
        c=O.CommunicationController(self.cfg());c.transmit([1,-1]);c.transmit([1,-1]);r=c.transmit([10,-1]);self.assertEqual(O.decode_fp32(r['packet'])['values'],[10.0,-1.0])
    def test_recovery_window_full_precision(self):
        c=O.CommunicationController(self.cfg());c.transmit([1,-1]);c.transmit([1,-1]);c.transmit([10,-1]);r=c.transmit([1,-1]);self.assertEqual(r['transport'],'fp32');self.assertEqual(r['mode_before'],'RECOVERY')
    def test_transition_log(self):
        c=O.CommunicationController(O.ControllerConfig(warmup_blocks=2,stability_window=2,stability_cv=.001));c.transmit([1,-1]);c.transmit([1,-1]);self.assertEqual(c.state.transitions[-1]['to'],'ONE_BIT')
    def test_safe_equal_magnitude_exact_reconstruction(self):
        c=O.CommunicationController(O.ControllerConfig(warmup_blocks=2,stability_window=2,stability_cv=.001,min_bit_balance=0,max_bit_balance=1));c.transmit([2,-2]);c.transmit([2,-2]);r=c.transmit([2,-2]);self.assertEqual(r['compression_error_ratio'],0)


class RecoveryReplayTests(unittest.TestCase):
    def test_replay_deterministic(self):
        cfg=O.ControllerConfig(warmup_blocks=2,stability_window=2,stability_cv=.001,min_bit_balance=0,max_bit_balance=1);r=O.replay([[1,-1]]*8,config=cfg);self.assertTrue(r['deterministic'])
    def test_checkpoint_continuation(self):
        cfg=O.ControllerConfig(warmup_blocks=2,stability_window=2,stability_cv=.001,min_bit_balance=0,max_bit_balance=1)
        a=O.CommunicationController(cfg);a.transmit([1,-1]);a.transmit([1,-1]);cp=a.checkpoint();b=O.CommunicationController.from_checkpoint(cp)
        self.assertEqual(a.transmit([1,-1])['packet'],b.transmit([1,-1])['packet'])
    def test_recovery_reentry(self):
        cfg=O.ControllerConfig(warmup_blocks=2,stability_window=2,stability_cv=.001,recovery_blocks=2,max_error_ratio=.01,min_bit_balance=0,max_bit_balance=1)
        c=O.CommunicationController(cfg);c.transmit([1,-1]);c.transmit([1,-1]);c.transmit([10,-1]);c.transmit([1,-1]);r=c.transmit([1,-1]);self.assertEqual(r['mode_after'],'ONE_BIT')
    def test_source_destination_guard(self):
        c=O.CommunicationController();p=O.encode_onebit([-1,1],sequence=0,source=2,destination=3)['packet']
        with self.assertRaises(O.OneBitError):c.receive(p,source=9)


class EquivalenceTests(unittest.TestCase):
    def test_equal_magnitude_equivalence(self):
        r=O.ab_compare([1,-1]*512);self.assertEqual(r['normalized_reconstruction_error'],0)
    def test_ab_hashes_distinct(self):
        r=O.ab_compare([1,-1]*8);self.assertNotEqual(r['fp32_sha256'],r['onebit_sha256'])
    def test_compressed_collective_reproducible(self):
        a=O.compressed_average([[1,-1]*50,[2,-2]*50]);b=O.compressed_average([[1,-1]*50,[2,-2]*50]);self.assertEqual(a['packets'],b['packets'])
    def test_quality_error_reported_not_hidden(self):
        r=O.ab_compare([.1,.2,-.9]);self.assertGreater(r['normalized_reconstruction_error'],0)


class AccountingTests(unittest.TestCase):
    def test_large_block_compresses_vs_fp32(self):
        r=O.ab_compare([1,-1]*1024);self.assertGreater(r['compression_ratio'],20)
    def test_effective_bits_near_one_for_large_block(self):
        r=O.ab_compare([1,-1]*4096);self.assertLess(r['effective_bits_per_scalar'],1.2)
    def test_small_block_header_overhead_visible(self):
        r=O.ab_compare([1,-1]);self.assertGreater(r['effective_bits_per_scalar'],8)
    def test_benchmark_counts(self):
        r=O.benchmark([1,-1]*64,rounds=10);self.assertEqual(r['rounds'],10);self.assertGreater(r['scalars_per_second'],0)
    def test_controller_byte_accounting(self):
        cfg=O.ControllerConfig(warmup_blocks=2,stability_window=2,stability_cv=.001,min_bit_balance=0,max_bit_balance=1);c=O.CommunicationController(cfg)
        rs=[c.transmit([1,-1]*32) for _ in range(4)];self.assertEqual(c.metrics()['wire_bytes'],sum(r['wire_bytes'] for r in rs))

if __name__=='__main__':unittest.main()
