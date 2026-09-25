"""Byte-exact logical pixel state, as bounded, atomically replaced TIFF pages.

UC-2.5.0 patches the PA21FABTIF/1 codec. The four logical 512-byte tiles
remain RGBA8. TIFF strips/tiles are a storage choice, not the logical grid.
BRO1 VM wrappers are verified then normalized to guest-visible payloads;
wrapper bytes themselves are not represented as editable pixels.
"""
from __future__ import annotations
import hashlib
import io
import json
import os
import struct
from typing import Dict, List, Optional, Tuple
try:
    from . import fabric_guard as G
except ImportError:  # Preserve the original standalone module-loading test/API.
    import importlib.util
    spec = importlib.util.spec_from_file_location('uc_fabric_guard', os.path.join(os.path.dirname(__file__), 'fabric_guard.py'))
    G = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(G)
FabricError = G.FabricError
MAGIC, TIF_MAGIC = b'PA21FAB1', 'PA21FABTIF/1'
CODEC_VERSION = '2.5.0'
HEADER, SLOTS, GUEST_FIRST, GUEST_COUNT, SHARD_BYTES = 28, 8, 2, 4, 512
T_KIND, T_TICK, T_STATE = 65000, 65001, 65002
FRAME, FRAME_HEADER = b'BRO1', 16
MAX_PAGES = G.MAX_PAGES

def parse_blob(blob: bytes) -> Dict[str, object]:
    if not isinstance(blob, bytes) or not HEADER <= len(blob) <= G.MAX_BLOB_BYTES or blob[:8] != MAGIC:
        raise FabricError('invalid or oversized PA21FAB1 fabric blob')
    version, monotonic, clock = struct.unpack_from('<IQQ', blob, 8)
    if version != 1: raise FabricError('unsupported fabric blob version')
    off, slots = HEADER, []
    for i in range(SLOTS):
        if off + 8 > len(blob): raise FabricError('fabric blob truncated in slot table')
        n = struct.unpack_from('<Q', blob, off)[0]; off += 8
        limit = SHARD_BYTES if GUEST_FIRST <= i < GUEST_FIRST + GUEST_COUNT else G.MAX_SCALAR_BYTES
        if n > limit or n > len(blob) - off: raise FabricError('fabric slot truncated or exceeds budget')
        slots.append(blob[off:off+n]); off += n
    if off != len(blob): raise FabricError('trailing bytes after fabric slots')
    return {'version':version,'monotonic':monotonic,'clock':clock,'slots':slots}

def build_blob(parts: Dict[str, object]) -> bytes:
    if not isinstance(parts, dict) or parts.get('version') != 1 or type(parts.get('version')) is not int:
        raise FabricError('unsupported fabric blob version')
    monotonic = G.uint(parts.get('monotonic'), name='monotonic')
    clock = G.uint(parts.get('clock'), name='clock')
    slots = parts.get('slots')
    if not isinstance(slots,(list,tuple)) or len(slots) != SLOTS: raise FabricError('a fabric must contain eight slots')
    out = bytearray(MAGIC + struct.pack('<IQQ',1,monotonic,clock))
    for i, slot in enumerate(slots):
        if not isinstance(slot,(bytes,bytearray,memoryview)): raise FabricError('fabric slot must be bytes')
        limit = SHARD_BYTES if 2 <= i < 6 else G.MAX_SCALAR_BYTES
        if len(slot) > limit: raise FabricError('fabric slot exceeds its byte budget')
        out.extend(struct.pack('<Q',len(slot))); out.extend(slot)
    return bytes(out)

def _unframe(slot: bytes, object_id=None) -> bytes:
    # Only a full-size BRO1 record is a VM frame. A short payload may legitimately
    # begin with the same four letters and must not be silently truncated.
    if len(slot) == SHARD_BYTES and slot[:4] == FRAME:
        plen = struct.unpack_from('<H',slot,12)[0]
        if slot[4] != 1 or slot[5] > 3 or (object_id is not None and slot[5] != object_id) or plen > 464:
            raise FabricError('invalid BRO1 version, object identity or payload length')
        if hashlib.sha256(slot[:480]).digest() != slot[480:512]:
            raise FabricError('BRO1 content hash mismatch')
        return slot[16:16+plen]
    return slot

def normalize_blob(blob):
    parts = parse_blob(blob); slots = list(parts['slots'])
    for k in range(4): slots[2+k] = _unframe(slots[2+k],k)
    parts['slots'] = slots
    return build_blob(parts)

def _grid(cols):
    if type(cols) is not int or not 1 <= cols <= 4: raise FabricError('grid columns must be 1..4')
    return (GUEST_COUNT + cols - 1)//cols, cols

def _tile_shape(): return 16,8

def _field_image(slots, cols):
    from PIL import Image
    rows,cols = _grid(cols); tw,th = _tile_shape()
    canvas = Image.new('RGBA',(cols*tw,rows*th),(0,0,0,0))
    for k in range(GUEST_COUNT):
        b = bytes(slots[2+k])
        if len(b)>SHARD_BYTES: raise FabricError('guest payload exceeds a logical tile')
        tile = Image.frombytes('RGBA',(tw,th),b+bytes(SHARD_BYTES-len(b)))
        try: canvas.paste(tile,((k%cols)*tw,(k//cols)*th))
        finally: tile.close()
    return canvas,(tw,th,rows,cols)

def _sidecar(parts,geom,tick):
    tw,th,rows,cols=geom; G.uint(tick,name='tick'); slots=parts['slots']
    return {'kind':TIF_MAGIC,'version':parts['version'],'monotonic':parts['monotonic'],
            'clock':parts['clock'],'tick':tick,'grid':{'rows':rows,'cols':cols,'tile_w':tw,'tile_h':th,'shard_bytes':512},
            'shard_len':[len(slots[2+k]) for k in range(4)],
            'scalar_slots':{str(i):slots[i].hex() for i in (0,1,6,7)}}

def _validate_sidecar(car, size=None):
    if not isinstance(car,dict) or set(car) != {'kind','version','monotonic','clock','tick','grid','shard_len','scalar_slots'}:
        raise FabricError('unknown or missing fabric metadata fields')
    if car['kind'] != TIF_MAGIC or type(car['version']) is not int or car['version'] != 1:
        raise FabricError('unsupported fabric sidecar kind/version')
    for name in ('monotonic','clock','tick'): G.uint(car[name],name=name)
    grid=car['grid']
    if not isinstance(grid,dict) or set(grid)!={'rows','cols','tile_w','tile_h','shard_bytes'}:
        raise FabricError('invalid logical tile grid')
    rows,cols=_grid(grid['cols'])
    expected={'rows':rows,'cols':cols,'tile_w':16,'tile_h':8,'shard_bytes':512}
    if grid!=expected or any(type(x) is not int for x in grid.values()): raise FabricError('unsupported logical tile geometry')
    if size is not None and tuple(size)!=(16*cols,8*rows): raise FabricError('raster/metadata geometry mismatch')
    lens=car['shard_len']
    if not isinstance(lens,list) or len(lens)!=4 or any(type(n) is not int or not 0<=n<=512 for n in lens):
        raise FabricError('invalid fabric shard lengths')
    scalars=car['scalar_slots']
    if not isinstance(scalars,dict) or set(scalars)!={'0','1','6','7'}: raise FabricError('invalid scalar slot namespace')
    for text in scalars.values():
        if not isinstance(text,str) or len(text)>G.MAX_SCALAR_BYTES*2 or len(text)%2 or any(c not in '0123456789abcdef' for c in text):
            raise FabricError('scalar slot must be bounded canonical hexadecimal')
    return car

def _page_ifd(car):
    from PIL.TiffImagePlugin import ImageFileDirectory_v2
    _validate_sidecar(car)
    js=G.canonical(car).decode('ascii'); ifd=ImageFileDirectory_v2()
    ifd[T_KIND]=TIF_MAGIC
    # ASCII avoids narrowing a u64 tick into a TIFF LONG's 32 bits.
    ifd.tagtype[T_TICK]=2; ifd[T_TICK]=str(car['tick'])
    ifd[T_STATE]=js; ifd[270]=js
    return ifd

def _car_from_tags(tags,size):
    raw=tags.get(T_STATE) or tags.get(270)
    car=_validate_sidecar(G.strict_json(raw),size)
    if tags.get(T_STATE) is not None and tags.get(270) is not None:
        if G.strict_json(tags[T_STATE]) != G.strict_json(tags[270]): raise FabricError('conflicting fabric metadata mirrors')
    if tags.get(T_KIND,TIF_MAGIC)!=TIF_MAGIC: raise FabricError('conflicting TIFF fabric kind')
    tick=tags.get(T_TICK,str(car['tick']))
    if isinstance(tick,tuple) and len(tick)==1: tick=tick[0]
    if str(tick)!=str(car['tick']): raise FabricError('conflicting TIFF tick mirror')
    return car

def _load_sidecar(img):
    if not hasattr(img,'tag_v2'): raise FabricError('image has no TIFF tags')
    return _car_from_tags(dict(img.tag_v2),img.size)

def _read_field(img,geom):
    if img.mode!='RGBA': raise FabricError('fabric raster is not byte-exact RGBA8')
    out=[]; cols=geom['cols']; tw,th=geom['tw'],geom['th']
    for k in range(4):
        c,r=k%cols,k//cols
        with img.crop((c*tw,r*th,(c+1)*tw,(r+1)*th)) as tile: out.append(tile.tobytes())
    return out

def _blob_from_image(img,car):
    car=_validate_sidecar(car,img.size)
    if img.mode!='RGBA': raise FabricError('refusing implicit raster color conversion')
    grid=car['grid']; shards=_read_field(img,{'tw':16,'th':8,'cols':grid['cols']})
    slots=[b'']*8
    for i,v in car['scalar_slots'].items(): slots[int(i)]=bytes.fromhex(v)
    for k in range(4): slots[2+k]=shards[k][:car['shard_len'][k]]
    return build_blob({'version':1,'monotonic':car['monotonic'],'clock':car['clock'],'slots':slots})

def _admit(data, max_pages=MAX_PAGES):
    record=G.inspect_tiff(data,max_pages=max_pages)
    for p in record['pages']:
        p['sidecar']=_car_from_tags(p['tags'],(p['width'],p['height']))
    return record

def inspect(path, *, max_pages=MAX_PAGES):
    record=_admit(G.read_bytes(path),max_pages)
    return {**{k:v for k,v in record.items() if k!='pages'},'page_count':len(record['pages']),
            'pages':[{k:v for k,v in p.items() if k not in ('tags','sidecar')}|{'tick':p['sidecar']['tick']} for p in record['pages']]}

def _decode_frame(data, page_record):
    from PIL import Image
    try:
        raster=G.raster_container(data,page_record)
        with Image.open(io.BytesIO(raster),formats=['TIFF']) as image:
            image.load()
            if image.mode != 'RGBA' or image.size != (page_record['width'],page_record['height']):
                raise FabricError('TIFF decoder changed the admitted raster layout')
            return image.copy()
    except FabricError: raise
    except (OSError,ValueError,EOFError,SyntaxError) as exc:
        raise FabricError('TIFF raster decoder rejected input') from exc


def _read_data(data, page=0):
    record=_admit(data)
    if type(page) is not int or not 0<=page<len(record['pages']): raise FabricError('TIFF page is outside history')
    car=record['pages'][page]['sidecar']
    with _decode_frame(data,record['pages'][page]) as img:
        blob=_blob_from_image(img,car)
    return {'blob':blob,'tick':car['tick'],'pages':len(record['pages']),'sidecar':car,
            'file_sha256':record['sha256'],'blob_sha256':hashlib.sha256(blob).hexdigest(),'page':page}

def read_tif(path: str, page=0): return _read_data(G.read_bytes(path),page)

def write_tif(blob: bytes, path: str, cols=2, tick=0, history=None, *, compression='tiff_deflate', expected_sha256=None):
    from PIL import Image
    if compression not in ('raw','tiff_deflate','tiff_lzw','packbits'): raise FabricError('unsupported or lossy output compression')
    hist=list(history or [])
    if len(hist)>=MAX_PAGES: raise FabricError('fabric history full; checkpoint required')
    normalized=normalize_blob(blob); parts=parse_blob(normalized)
    field,geom=_field_image(parts['slots'],cols); car=_sidecar(parts,geom,tick); ifd=_page_ifd(car)
    # A metadata-less history frame is corruption, not a reason to invent state.
    expected=[]
    try:
        for h in hist:
            meta=(getattr(h,'encoderinfo',None) or {}).get('tiffinfo')
            if meta is None: raise FabricError('history frame has no fabric metadata')
            hcar=_car_from_tags(dict(meta),h.size)
            expected.append(_blob_from_image(h,hcar))
        field.encoderinfo={'tiffinfo':ifd}
        with io.BytesIO() as out:
            field.save(out,format='TIFF',save_all=True,append_images=hist,tiffinfo=ifd,compression=compression)
            data=out.getvalue()
        # Preflight every page; decode every emitted frame before committing.
        record=_admit(data)
        if len(record['pages'])!=1+len(hist): raise FabricError('TIFF encoder lost history frames')
        for i,want in enumerate([normalized,*expected]):
            with _decode_frame(data,record['pages'][i]) as check:
                got=_blob_from_image(check,record['pages'][i]['sidecar'])
                if got!=want: raise FabricError('TIFF encoder changed logical state/history')
        G.atomic_bytes(path,data,expected_sha256=expected_sha256)
    finally: field.close()
    return {'path':os.fspath(path),'tick':tick,'pages':1+len(hist),'grid':car['grid'],'bytes':len(data),
            'blob_sha256':hashlib.sha256(normalized).hexdigest(),'sha256':hashlib.sha256(data).hexdigest(),
            'wrapper_normalized':normalized!=blob,'codec_version':CODEC_VERSION}

def frames(path):
    record=_admit(G.read_bytes(path))
    return [{'page':i,'tick':p['sidecar']['tick'],'monotonic':p['sidecar']['monotonic'],'clock':p['sidecar']['clock']}
            for i,p in enumerate(record['pages'])]

def load_frames(path, limit=None):
    from PIL import Image
    data=G.read_bytes(path); record=_admit(data)
    if limit is None: limit=len(record['pages'])
    if type(limit) is not int or not 0<=limit<=MAX_PAGES: raise FabricError('invalid history window limit')
    out=[]
    try:
        for p in record['pages'][:limit]:
            with _decode_frame(data,p) as img:
                _blob_from_image(img,p['sidecar'])
                f=img.copy(); f.encoderinfo={'tiffinfo':_page_ifd(p['sidecar'])}; out.append(f)
        return out
    except Exception:
        for f in out: f.close()
        raise

def render_view(path,out,scale=16):
    from PIL import Image
    if type(scale) is not int or not 1<=scale<=64: raise FabricError('view scale must be 1..64')
    data=G.read_bytes(path); rec=_admit(data)
    with _decode_frame(data,rec['pages'][0]) as img:
        _blob_from_image(img,rec['pages'][0]['sidecar'])
        cells=img.size
        with img.resize((img.width*scale,img.height*scale),Image.Resampling.NEAREST) as big:
            pixels=big.size
            with io.BytesIO() as buf:
                big.save(buf,format='PNG'); G.atomic_bytes(out,buf.getvalue())
    return {'view':os.fspath(out),'cells':cells,'pixels':pixels,'authoritative':False}

def validate_roundtrip(blob,path):
    normalized=normalize_blob(blob); write_tif(blob,path); back=read_tif(path)['blob']
    ok=back==normalized
    return {'reversible':ok,'byte_exact_input':back==blob,'wrapper_normalized':normalized!=blob,
            'in_sha256':hashlib.sha256(blob).hexdigest(),'normalized_sha256':hashlib.sha256(normalized).hexdigest(),
            'out_sha256':hashlib.sha256(back).hexdigest(),'bytes_in':len(blob),'bytes_out':len(back),
            'reason':'' if ok else 'logical fabric state changed during round trip'}
