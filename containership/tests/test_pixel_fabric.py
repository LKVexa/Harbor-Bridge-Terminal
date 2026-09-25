"""Regression and fault cases for the UC-2.5.0 local TIFF/GIF pixel profile."""
from __future__ import annotations
import contextlib
import hashlib
import io
import json
from pathlib import Path
import random
import struct
import sys
import tempfile
import unittest
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'hull'),str(ROOT/'ship')]
from PIL import Image
from pa21studio import fabric_tif as T, fabric_guard as G, fabric_gif as F, pixel_kernel as K
from unikernel import tif_fabric as TF, Refusal
from unikernel import pixels_cli as PC, engines as E


def blob(seed=0):
    rng=random.Random(seed)
    return T.build_blob({'version':1,'monotonic':seed,'clock':2**63+seed,
                         'slots':[b'scalar\0',b'\xff\0',*(bytes(rng.randrange(256) for _ in range(n)) for n in (64,464,256,16)),b'',b'end']})


def framed(payload,oid=0):
    b=bytearray(512);b[:4]=b'BRO1';b[4]=1;b[5]=oid;struct.pack_into('<H',b,12,len(payload));b[16:16+len(payload)]=payload
    b[480:]=hashlib.sha256(b[:480]).digest();return bytes(b)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.path=self.root/'state.tif';self.b=blob();T.write_tif(self.b,self.path)
    def broken(self,data):
        self.path.write_bytes(data)
        with self.assertRaises(G.FabricError):T.read_tif(self.path)
    def entries(self,data):
        endian='<' if data[:2]==b'II' else '>';off=struct.unpack_from(endian+'I',data,4)[0];n=struct.unpack_from(endian+'H',data,off)[0]
        return endian,off,n,{struct.unpack_from(endian+'H',data,off+2+12*i)[0]:off+2+12*i for i in range(n)}
    def tag_value(self,tag,value):
        data=bytearray(self.path.read_bytes());endian,_,_,ent=self.entries(data);p=ent[tag]
        typ=struct.unpack_from(endian+'H',data,p+2)[0];struct.pack_into(endian+('H' if typ==3 else 'I'),data,p+8,value)
        return bytes(data)

class BlobTests(Base):
    def test_exact_roundtrip(self):self.assertEqual(T.read_tif(self.path)['blob'],self.b)
    def test_trailing_bytes(self):
        with self.assertRaises(G.FabricError):T.parse_blob(self.b+b'x')
    def test_unsupported_version(self):
        bad=bytearray(self.b);struct.pack_into('<I',bad,8,2)
        with self.assertRaises(G.FabricError):T.parse_blob(bytes(bad))
    def test_slot_overflow(self):
        bad=bytearray(self.b);struct.pack_into('<Q',bad,28,2**63)
        with self.assertRaises(G.FabricError):T.parse_blob(bytes(bad))
    def test_truncated_blob(self):
        for n in (0,7,27,30,len(self.b)-1):
            with self.subTest(n=n),self.assertRaises(G.FabricError):T.parse_blob(self.b[:n])
    def test_boolean_counter(self):
        p=T.parse_blob(self.b);p['clock']=True
        with self.assertRaises(G.FabricError):T.build_blob(p)
    def test_negative_counter(self):
        p=T.parse_blob(self.b);p['monotonic']=-1
        with self.assertRaises(G.FabricError):T.build_blob(p)
    def test_u64_tick(self):
        T.write_tif(self.b,self.path,tick=2**64-1);self.assertEqual(T.read_tif(self.path)['tick'],2**64-1)
    def test_tick_overflow(self):
        old=self.path.read_bytes()
        with self.assertRaises(G.FabricError):T.write_tif(self.b,self.path,tick=2**64)
        self.assertEqual(self.path.read_bytes(),old)
    def test_short_magic_preserved(self):
        p=T.parse_blob(self.b);p['slots'][2]=b'BRO1'+bytes(30);b=T.build_blob(p)
        self.assertEqual(T.normalize_blob(b),b)
    def test_bro1_integrity(self):
        p=T.parse_blob(self.b);p['slots'][2]=framed(b'hello');b=T.build_blob(p)
        T.write_tif(b,self.path);self.assertEqual(T.parse_blob(T.read_tif(self.path)['blob'])['slots'][2],b'hello')
    def test_bro1_corruption(self):
        p=T.parse_blob(self.b);f=bytearray(framed(b'x'));f[17]^=1;p['slots'][2]=bytes(f)
        with self.assertRaises(G.FabricError):T.normalize_blob(T.build_blob(p))
    def test_bro1_object_identity(self):
        p=T.parse_blob(self.b);p['slots'][2]=framed(b'x',3)
        with self.assertRaises(G.FabricError):T.normalize_blob(T.build_blob(p))
    def test_scalar_budget(self):
        p=T.parse_blob(self.b);p['slots'][0]=bytes(G.MAX_SCALAR_BYTES+1)
        with self.assertRaises(G.FabricError):T.build_blob(p)

class AdmissionTests(Base):
    def test_png_rejected_before_decode(self):
        with Image.new('RGBA',(32,16)) as im:im.save(self.path,format='PNG')
        with mock.patch('PIL.Image.open') as decoder,self.assertRaises(G.FabricError):T.read_tif(self.path)
        decoder.assert_not_called()
    def test_short_header(self):self.broken(b'II*\0')
    def test_unknown_magic(self):self.broken(b'II'+struct.pack('<HI',40,8)+bytes(40))
    def test_huge_ifd_pointer(self):
        bad=bytearray(self.path.read_bytes());struct.pack_into('<I',bad,4,0xfffffff0);self.broken(bytes(bad))
    def test_cycle(self):
        bad=bytearray(self.path.read_bytes());e,off,n,_=self.entries(bad);struct.pack_into(e+'I',bad,off+2+n*12,off);self.broken(bytes(bad))
    def test_ifd_count_budget(self):
        bad=bytearray(self.path.read_bytes());e,off,_,_=self.entries(bad);struct.pack_into(e+'H',bad,off,129);self.broken(bytes(bad))
    def test_duplicate_tag(self):
        bad=bytearray(self.path.read_bytes());e,off,_,_=self.entries(bad);bad[off+14:off+16]=bad[off+2:off+4];self.broken(bytes(bad))
    def test_huge_tag_count(self):
        bad=bytearray(self.path.read_bytes());e,_,_,ent=self.entries(bad);struct.pack_into(e+'I',bad,ent[65002]+4,2**32-1);self.broken(bytes(bad))
    def test_metadata_cumulative_budget(self):
        with mock.patch.object(G,'MAX_TOTAL_TAG_BYTES',8),self.assertRaises(G.FabricError):T.read_tif(self.path)
    def test_bad_external_offset(self):
        bad=bytearray(self.path.read_bytes());e,_,_,ent=self.entries(bad);struct.pack_into(e+'I',bad,ent[65002]+8,len(bad)+1);self.broken(bytes(bad))
    def test_oversize_dimensions(self):self.broken(self.tag_value(256,65535))
    def test_lossy_compression(self):self.broken(self.tag_value(259,7))
    def test_planar_conversion(self):
        # Missing PlanarConfiguration is chunky by default; build an explicit incompatible frame.
        with Image.new('RGB',(32,16)) as im:im.save(self.path,format='TIFF')
        with self.assertRaises(G.FabricError):T.read_tif(self.path)
    def test_associated_alpha(self):self.broken(self.tag_value(338,1))
    def test_raster_metadata_overlap(self):
        bad=bytearray(self.path.read_bytes());e,off,_,ent=self.entries(bad);struct.pack_into(e+'I',bad,ent[273]+8,off);self.broken(bytes(bad))
    def test_raster_out_of_range(self):self.broken(self.tag_value(273,2**32-1))
    def test_metadata_mirror_disagreement(self):
        bad=self.path.read_bytes();self.assertIn(b'"tick":0',bad);self.broken(bad.replace(b'"tick":0',b'"tick":9',1))
    def test_duplicate_json(self):
        with self.assertRaises(G.FabricError):G.strict_json('{"x":1,"x":2}')
    def test_nonfinite_json(self):
        with self.assertRaises(G.FabricError):G.strict_json('{"x":NaN}')
    def test_bad_scalar_hex(self):
        car=T.read_tif(self.path)['sidecar'];car['scalar_slots']['0']='zz'
        with self.assertRaises(G.FabricError):T._validate_sidecar(car,(32,16))
    def test_unknown_sidecar_fields(self):
        car=T.read_tif(self.path)['sidecar'];car['surprise']=True
        with self.assertRaises(G.FabricError):T._validate_sidecar(car,(32,16))
    def test_bool_grid(self):
        car=T.read_tif(self.path)['sidecar'];car['grid']['cols']=True
        with self.assertRaises(G.FabricError):T._validate_sidecar(car,(32,16))
    def test_truncation_campaign(self):
        raw=self.path.read_bytes()
        for n in range(0,len(raw),max(1,len(raw)//40)):
            with self.subTest(n=n):self.broken(raw[:n])
    def test_seeded_pointer_mutations(self):
        original=self.path.read_bytes();rng=random.Random(250)
        for _ in range(64):
            bad=bytearray(original);struct.pack_into('<I',bad,4,rng.randrange(len(bad)+1,2**32))
            self.broken(bytes(bad))
    def test_symlink_rejected(self):
        q=self.root/'link.tif'
        try:q.symlink_to(self.path)
        except (OSError,NotImplementedError):self.skipTest('symlink creation unavailable')
        with self.assertRaises(G.FabricError):T.read_tif(q)
    def test_bigtiff_header_offset_width(self):self.broken(b'II'+struct.pack('<HHHQ',43,4,0,16)+bytes(80))
    def test_bigtiff_header_reserved(self):self.broken(b'II'+struct.pack('<HHHQ',43,8,1,16)+bytes(80))

class HistoryTests(Base):
    def test_compression_matrix(self):
        for comp in ('raw','tiff_deflate','tiff_lzw','packbits'):
            with self.subTest(comp=comp):T.write_tif(self.b,self.path,compression=comp);self.assertEqual(T.read_tif(self.path)['blob'],self.b)
    def test_grid_matrix(self):
        for cols in (1,2,3,4):
            with self.subTest(cols=cols):T.write_tif(self.b,self.path,cols=cols);self.assertEqual(T.read_tif(self.path)['blob'],self.b)
    def test_history_all_frames(self):
        for n in range(1,5):
            hist=T.load_frames(self.path)
            try:T.write_tif(blob(n),self.path,tick=n,history=hist)
            finally:
                for f in hist:f.close()
        self.assertEqual([T.read_tif(self.path,i)['blob'] for i in range(5)],[blob(i) for i in range(4,-1,-1)])
    def test_missing_history_metadata(self):
        with Image.new('RGBA',(32,16)) as im,self.assertRaises(G.FabricError):T.write_tif(self.b,self.path,history=[im])
    def test_history_window(self):
        h=T.load_frames(self.path,limit=0);self.assertEqual(h,[])
    def test_full_history_refused(self):
        hist=T.load_frames(self.path)
        try:
            with mock.patch.object(T,'MAX_PAGES',1),self.assertRaises(G.FabricError):T.write_tif(self.b,self.path,history=hist)
        finally:
            for f in hist:f.close()
    def test_stale_commit(self):
        old=self.path.read_bytes()
        with self.assertRaises(G.FabricError):T.write_tif(blob(2),self.path,expected_sha256='0'*64)
        self.assertEqual(old,self.path.read_bytes())
    def test_replace_failure_preserves_old(self):
        old=self.path.read_bytes()
        with mock.patch.object(G.os,'replace',side_effect=OSError('injected')),self.assertRaises(OSError):T.write_tif(blob(2),self.path)
        self.assertEqual(old,self.path.read_bytes());self.assertFalse(list(self.root.glob('.px-*')))
    def test_encoder_failure_preserves_old(self):
        old=self.path.read_bytes()
        with mock.patch('PIL.Image.Image.save',side_effect=OSError('injected')),self.assertRaises(OSError):T.write_tif(blob(1),self.path)
        self.assertEqual(old,self.path.read_bytes())
    def test_negative_page(self):
        with self.assertRaises(G.FabricError):T.read_tif(self.path,-1)
    def test_all_30_sealed_genesis(self):
        paths=list((ROOT/'berths').glob('**/GENESIS.fabric.tif'));self.assertEqual(len(paths),30)
        for p in paths:
            with self.subTest(p=p.relative_to(ROOT)):self.assertEqual(T.read_tif(p)['pages'],1)

class GifTests(Base):
    def setUp(self):
        super().setUp();self.gif=self.root/'state.gif';F.export_tiff(self.path,self.gif)
    def badgif(self,raw):
        self.gif.write_bytes(raw)
        with self.assertRaises(G.FabricError):F.read_gif(self.gif)
    def test_exact_state(self):self.assertEqual(F.read_gif(self.gif)['frames'][0]['blob'],self.b)
    def test_all_byte_values(self):
        p=T.parse_blob(self.b);p['slots'][2]=bytes(range(256));b=T.build_blob(p)
        F.write_gif([{'blob':b,'tick':99,'cols':2}],self.gif);self.assertEqual(F.read_gif(self.gif)['frames'][0]['blob'],b)
    def test_duplicate_frames_not_coalesced(self):
        F.write_gif([{'blob':self.b,'tick':i,'cols':2} for i in range(5)],self.gif)
        result=F.read_gif(self.gif);self.assertEqual(result['pages'],5);self.assertEqual([r['tick'] for r in result['frames']],list(range(5)))
    def test_restore(self):
        dst=self.root/'restore.tif';F.restore_tiff(self.gif,dst);self.assertEqual(T.read_tif(dst)['blob'],self.b)
    def test_restore_existing_refused(self):
        old=self.path.read_bytes()
        with self.assertRaises(G.FabricError):F.restore_tiff(self.gif,self.path)
        self.assertEqual(old,self.path.read_bytes())
    def test_multiframe_restore(self):
        records=[{'blob':blob(i),'tick':i,'cols':2} for i in range(4)]
        F.write_gif(records,self.gif);dst=self.root/'restored.tif';F.restore_tiff(self.gif,dst)
        self.assertEqual([T.read_tif(dst,i)['blob'] for i in range(4)],[r['blob'] for r in records])
    def test_palette_mutation(self):
        raw=bytearray(self.gif.read_bytes());raw[20]^=1;self.badgif(bytes(raw))
    def test_missing_metadata(self):
        raw=self.gif.read_bytes();end=raw.index(b'\x21\xf9',781);self.badgif(raw[:781]+raw[end:])
    def test_digest_mismatch(self):
        raw=self.gif.read_bytes();h=hashlib.sha256(self.b).hexdigest().encode();self.assertIn(h,raw);self.badgif(raw.replace(h,b'0'*64))
    def test_trailing_data(self):self.badgif(self.gif.read_bytes()+b'x')
    def test_truncated_blocks(self):
        raw=self.gif.read_bytes()
        for n in (0,6,780,790,len(raw)-1):
            with self.subTest(n=n):self.badgif(raw[:n])
    def test_disposal_rejected(self):
        raw=self.gif.read_bytes();self.badgif(raw.replace(b'\x21\xf9\x04\x08',b'\x21\xf9\x04\x04'))
    def test_empty_records(self):
        with self.assertRaises(G.FabricError):F.write_gif([],self.gif)
    def test_duration_rejected(self):
        with self.assertRaises(G.FabricError):F.write_gif([{'blob':self.b,'tick':0,'cols':2}],self.gif,duration_ms=1)
    def test_random_artwork_refused(self):
        with Image.new('P',(64,32)) as im:im.save(self.gif,format='GIF')
        with self.assertRaises(G.FabricError):F.read_gif(self.gif)

class KernelTests(Base):
    def test_set_exact(self):
        r=K.apply(self.b,[{'tile':0,'word':0,'op':'set','value':2**64-1}]);self.assertEqual(K.read_u64(r['blob'],0,0),2**64-1);self.assertEqual(r['dirty_tiles'],[0])
    def test_set_extends_to_58(self):
        r=K.apply(self.b,[{'tile':3,'word':57,'op':'set','value':42}]);self.assertEqual(len(T.parse_blob(r['blob'])['slots'][5]),464)
    def test_native_limit(self):
        for w in (58,63,64,-1,True):
            with self.subTest(word=w),self.assertRaises(G.FabricError):K.apply(self.b,[{'tile':0,'word':w,'op':'set','value':1}])
    def test_value_types(self):
        for value in (-1,2**64,True,1.0,'1'):
            with self.subTest(value=value),self.assertRaises(G.FabricError):K.apply(self.b,[{'tile':0,'word':0,'op':'set','value':value}])
    def test_overflow_rejected(self):
        with self.assertRaises(G.FabricError):K.apply(self.b,[{'tile':0,'word':0,'op':'set','value':2**64-1},{'tile':0,'word':0,'op':'add','value':1}])
    def test_explicit_wrap(self):
        r=K.apply(self.b,[{'tile':0,'word':0,'op':'set','value':2**64-1},{'tile':0,'word':0,'op':'add','value':1,'overflow':'wrap'}]);self.assertEqual(K.read_u64(r['blob'],0,0),0)
    def test_xor(self):
        before=K.read_u64(self.b,0,0);r=K.apply(self.b,[{'tile':0,'word':0,'op':'xor','value':255}]);self.assertEqual(K.read_u64(r['blob'],0,0),before^255)
    def test_batch_atomic(self):
        old=bytes(self.b)
        with self.assertRaises(G.FabricError):K.apply(self.b,[{'tile':0,'word':0,'op':'set','value':7},{'tile':8,'word':0,'op':'set','value':8}])
        self.assertEqual(self.b,old)
    def test_cas_refused(self):
        with self.assertRaises(G.FabricError):K.apply(self.b,[{'tile':0,'word':0,'op':'set','value':7,'expect':K.read_u64(self.b,0,0)^1}])
    def test_stale_blob_digest(self):
        with self.assertRaises(G.FabricError):K.apply(self.b,[{'tile':0,'word':0,'op':'set','value':7}],expected_sha256='0'*64)
    def test_coordinates(self):self.assertEqual(K.coordinates(3,57)['pixels'],[[18,15],[19,15]])
    def test_diff(self):
        r=K.apply(self.b,[{'tile':1,'word':1,'op':'set','value':7}]);d=K.diff(self.b,r['blob']);self.assertEqual(len(d['changed_cells']),1);self.assertFalse(d['counters_changed'])
    def test_arithmetic_uninitialized(self):
        with self.assertRaises(G.FabricError):K.apply(self.b,[{'tile':3,'word':57,'op':'add','value':7}])
    def test_empty_batch(self):
        with self.assertRaises(G.FabricError):K.apply(self.b,[])
    def test_operation_budget(self):
        with self.assertRaises(G.FabricError):K.apply(self.b,[{'tile':0,'word':0,'op':'set','value':0}]*1025)
    def test_ship_paint_uses_kernel(self):
        r=TF.paint(str(self.path),0,0,42);self.assertEqual(r['dirty_tiles'],[0]);self.assertEqual(K.read_u64(T.read_tif(self.path)['blob'],0,0),42);self.assertEqual(T.read_tif(self.path)['pages'],2)
    def test_ship_rejects_negative_not_masks(self):
        old=self.path.read_bytes()
        with self.assertRaises(Refusal):TF.paint(str(self.path),0,0,-1)
        self.assertEqual(old,self.path.read_bytes())
    def test_ship_stale_digest(self):
        with self.assertRaises(Refusal):TF.paint(str(self.path),0,0,42,expected_sha256='0'*64)

class IndependentInteropTests(Base):
    def test_tifffile_matrix(self):
        try:import numpy as np;import tifffile
        except ImportError:self.skipTest('optional independent tifffile/numpy encoder unavailable')
        state=T.read_tif(self.path);car=state['sidecar'];image,_=T._field_image(T.parse_blob(self.b)['slots'],2)
        try:arr=np.array(image)
        finally:image.close()
        tags=[(65000,'s',0,T.TIF_MAGIC,False),(65001,'s',0,str(car['tick']),False),(65002,'s',0,G.canonical(car).decode(),False)]
        for big in (False,True):
            for endian in ('<','>'):
                for tiled in (False,True):
                    with self.subTest(big=big,endian=endian,tiled=tiled):
                        tifffile.imwrite(self.path,arr,bigtiff=big,byteorder=endian,photometric='rgb',extrasamples='unassalpha',
                                         metadata=None,description=G.canonical(car).decode(),extratags=tags,tile=(16,16) if tiled else None)
                        r=T.read_tif(self.path);self.assertEqual(r['blob'],self.b)


class PixelCLITests(Base):
    def call(self,verb,**kw):
        import types
        args=types.SimpleNamespace(pixel_verb=verb,name='vm_small',slot='DF_Small',**kw)
        with mock.patch.object(E,'SHIP',str(self.root)),mock.patch.object(PC,'state_path',return_value=(self.path,'live')),contextlib.redirect_stdout(io.StringIO()) as out:
            code=PC.run(args)
        self.assertEqual(code,0);return json.loads(out.getvalue())
    def test_status(self):self.assertEqual(self.call('status')['u64_words_per_native_tile'],58)
    def test_inspect(self):self.assertEqual(self.call('inspect')['file_sha256'],hashlib.sha256(self.path.read_bytes()).hexdigest())
    def test_cell(self):self.assertEqual(self.call('cell',tile=0,word=0)['value'],K.read_u64(self.b,0,0))
    def test_export_keeps_source(self):
        old=self.path.read_bytes();r=self.call('export-gif',limit=1);self.assertEqual(old,self.path.read_bytes());self.assertEqual(F.read_gif(r['path'])['frames'][0]['blob'],self.b)
    def test_checkpoint_preserves_archive_and_state(self):
        hist=T.load_frames(self.path)
        try:T.write_tif(blob(2),self.path,tick=2,history=hist)
        finally:
            for f in hist:f.close()
        old=self.path.read_bytes();r=self.call('checkpoint',expect=hashlib.sha256(old).hexdigest())
        self.assertEqual(Path(r['archive']).read_bytes(),old);self.assertEqual(r['previous_pages'],2);self.assertEqual(T.read_tif(self.path)['pages'],1);self.assertEqual(T.read_tif(self.path)['blob'],blob(2))
    def test_checkpoint_stale_refused(self):
        with self.assertRaises(Refusal):self.call('checkpoint',expect='0'*64)
    def test_paint_guard(self):
        r=self.call('paint',tile=0,word=0,value=44,expect=hashlib.sha256(self.path.read_bytes()).hexdigest());self.assertEqual(r['value'],44)
    def test_restore_into_sealed_ship_refused(self):
        with self.assertRaises(Refusal):self.call('restore-gif',source=str(self.root/'a.gif'),destination=str(self.root/'hull/x.tif'))
    def test_export_limit(self):
        with self.assertRaises(Refusal):self.call('export-gif',limit=513)
    def test_paint_requires_generation_cli(self):
        from unikernel import cli
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as e:
            cli.main(['pixels','paint','vm_small','DF_Small','0','0','1','--expect','0'*64])
        self.assertEqual(e.exception.code,2)

class CapacityTests(Base):
    def test_exact_512_pages_then_refuse_append(self):
        frame=T.load_frames(self.path)[0]
        try:
            T.write_tif(self.b,self.path,history=[frame]*511)
            self.assertEqual(T.inspect(self.path)['page_count'],512)
            with self.assertRaises(Refusal):TF._preflight_next(str(self.path))
        finally:frame.close()
    def test_counter_exhaustion_before_work(self):
        p=T.parse_blob(self.b);s=bytearray(p['slots'][2]);struct.pack_into('<Q',s,0,2**64-1);p['slots'][2]=bytes(s);T.write_tif(T.build_blob(p),self.path)
        with self.assertRaises(Refusal):TF._preflight_next(str(self.path))
    def test_clock_exhaustion_before_work(self):
        p=T.parse_blob(self.b);p['clock']=2**64-1;T.write_tif(T.build_blob(p),self.path)
        with self.assertRaises(Refusal):TF._preflight_next(str(self.path),1)
    def test_512_gif_frames_preserved(self):
        g=self.root/'full.gif';F.write_gif([{'blob':self.b,'tick':i,'cols':2} for i in range(512)],g)
        r=F.read_gif(g);self.assertEqual(r['pages'],512);self.assertEqual(r['frames'][-1]['tick'],511)

if __name__=='__main__':unittest.main()
