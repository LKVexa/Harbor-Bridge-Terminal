"""UC/FABRIC_GIF/1: exact fabric bytes in GIF89a palette-index frames.

This is a restricted state-transport profile, not arbitrary artwork import.
Palette entry i is (i,i,i), so a pixel carries one exact byte. Each frame has
independent bounded JSON metadata, a digest, a full-screen image and no alpha.
No quantization, dithering, frame coalescing, external references or execution.
TIFF remains the live state format. GIF restore writes a separate TIFF file.
"""
from __future__ import annotations
import hashlib
import io
import os
import struct
from . import fabric_guard as G
from . import fabric_tif as T

KIND='UC/FABRIC_GIF/1'
WIDTH=64
PALETTE=bytes(v for i in range(256) for v in (i,i,i))
MAX_HEIGHT=(G.MAX_BLOB_BYTES+WIDTH-1)//WIDTH
MAX_META=2048

def _blocks(data):
    return b''.join(bytes([len(data[i:i+255])])+data[i:i+255] for i in range(0,len(data),255))+b'\0'

def _scan(data):
    """Bound framing before invoking Pillow's LZW decoder on isolated frames."""
    if not isinstance(data,bytes) or not 781 <= len(data) <= G.MAX_FILE_BYTES or data[:6]!=b'GIF89a':
        raise G.FabricError('not a bounded GIF89a fabric stream')
    width,height,packed,bg,aspect=struct.unpack_from('<HHBBB',data,6)
    if width!=WIDTH or not 1<=height<=MAX_HEIGHT or not packed&128 or (packed&7)!=7 or bg or aspect:
        raise G.FabricError('unsupported fabric GIF logical screen')
    if data[13:781]!=PALETTE: raise G.FabricError('fabric GIF requires the canonical byte palette')
    off=781; frames=[]; meta=None; gce=None; frame_start=None
    def take(n):
        nonlocal off
        if n<0 or n>len(data)-off: raise G.FabricError('truncated GIF block')
        b=data[off:off+n];off+=n;return b
    def subblocks(limit):
        chunks=[];total=0
        while True:
            size=take(1)[0]
            if not size: return b''.join(chunks)
            total+=size
            if total>limit: raise G.FabricError('GIF sub-block payload exceeds budget')
            chunks.append(take(size))
    while off<len(data):
        pos=off; kind=take(1)[0]
        if kind==0x3B:
            if off!=len(data) or meta is not None or gce is not None or not frames:
                raise G.FabricError('GIF trailing bytes, incomplete frame or empty stream')
            return {'width':width,'height':height,'frames':frames,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
        if kind==0x21:
            label=take(1)[0]
            if label==0xFE:
                if meta is not None or gce is not None: raise G.FabricError('duplicate or misplaced GIF frame metadata')
                meta=G.strict_json(subblocks(MAX_META))
                required={'kind','index','blob_len','blob_sha256','tick','cols'}
                if set(meta)!=required or meta['kind']!=KIND or type(meta['index']) is not int or meta['index']!=len(frames):
                    raise G.FabricError('invalid GIF frame metadata identity/order')
                n=meta['blob_len']; sha=meta['blob_sha256']
                if type(n) is not int or not 92<=n<=min(width*height,G.MAX_BLOB_BYTES): raise G.FabricError('GIF fabric length outside budget')
                if not isinstance(sha,str) or len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha):
                    raise G.FabricError('GIF fabric digest is invalid')
                G.uint(meta['tick'],name='GIF tick'); T._grid(meta['cols'])
            elif label==0xF9:
                if meta is None or gce is not None: raise G.FabricError('GIF frame has missing metadata or duplicate controls')
                b=take(6)
                if b[0]!=4 or b[1]!=8 or b[4]!=0 or b[5]!=0:
                    raise G.FabricError('GIF fabric forbids transparency and non-independent disposal')
                duration=struct.unpack_from('<H',b,2)[0]
                if not 1<=duration<=6000: raise G.FabricError('GIF frame timing outside profile')
                gce=b'\x21\xf9'+b;frame_start=pos
            else:
                raise G.FabricError('GIF extension is outside the state profile')
        elif kind==0x2C:
            if meta is None or gce is None: raise G.FabricError('GIF frame requires independent metadata and control')
            b=take(9);left,top,w,h,flags=struct.unpack('<HHHHB',b)
            if (left,top,w,h,flags)!=(0,0,width,height,0):
                raise G.FabricError('GIF fabric forbids cropping, interlace or local palettes')
            if take(1)!=b'\x08': raise G.FabricError('GIF fabric requires 8-bit LZW input')
            subblocks(G.MAX_BLOB_BYTES*2+1024)
            frames.append({'metadata':meta,'image_block':data[frame_start:off]})
            if len(frames)>G.MAX_PAGES: raise G.FabricError('GIF frame count exceeds history budget')
            meta=None;gce=None;frame_start=None
        else: raise G.FabricError('unexpected GIF record')
    raise G.FabricError('GIF trailer missing')

def _decode(data):
    from PIL import Image
    scan=_scan(data); records=[]
    for frame in scan['frames']:
        car=frame['metadata']; one=data[:781]+frame['image_block']+b';'
        try:
            with Image.open(io.BytesIO(one),formats=['GIF']) as img:
                img.load()
                if img.size!=(scan['width'],scan['height']) or img.mode not in ('L','P'):
                    raise G.FabricError('GIF decoder changed byte-plane layout')
                raw=img.tobytes()
        except G.FabricError: raise
        except (OSError,ValueError,EOFError,SyntaxError) as exc: raise G.FabricError('GIF raster decoder rejected input') from exc
        blob=raw[:car['blob_len']]
        if any(raw[car['blob_len']:]): raise G.FabricError('GIF state padding must be zero')
        if hashlib.sha256(blob).hexdigest()!=car['blob_sha256']: raise G.FabricError('GIF state digest mismatch')
        T.parse_blob(blob)
        records.append({'blob':blob,'tick':car['tick'],'cols':car['cols'],'blob_sha256':car['blob_sha256']})
    return records,scan

def read_gif(path):
    records,scan=_decode(G.read_bytes(path))
    return {'kind':KIND,'frames':records,'pages':len(records),'sha256':scan['sha256'],'bytes':scan['bytes']}

def write_gif(records,path,*,duration_ms=100):
    from PIL import Image
    if not isinstance(records,(list,tuple)) or not 1<=len(records)<=G.MAX_PAGES:
        raise G.FabricError('GIF export requires 1..512 frame records')
    if type(duration_ms) is not int or not 10<=duration_ms<=60000 or duration_ms%10:
        raise G.FabricError('GIF duration must be 10..60000ms in 10ms units')
    clean=[]
    for r in records:
        if not isinstance(r,dict): raise G.FabricError('GIF frame must be a record')
        T.parse_blob(r.get('blob'));G.uint(r.get('tick'),name='tick');T._grid(r.get('cols',2));clean.append(r)
    height=(max(len(r['blob']) for r in clean)+WIDTH-1)//WIDTH
    header=b'GIF89a'+struct.pack('<HHBBB',WIDTH,height,0xF7,0,0)+PALETTE
    out=bytearray(header)
    for i,r in enumerate(clean):
        blob=r['blob'];car={'kind':KIND,'index':i,'blob_len':len(blob),'blob_sha256':hashlib.sha256(blob).hexdigest(),
                           'tick':r['tick'],'cols':r.get('cols',2)}
        raw=blob+bytes(WIDTH*height-len(blob))
        with Image.frombytes('P',(WIDTH,height),raw) as img:
            img.putpalette(PALETTE)
            with io.BytesIO() as buf:
                # Encode one complete image at a time: save_all would coalesce
                # identical raster frames even when counters/tick metadata differ.
                img.save(buf,format='GIF',optimize=False,interlace=False,disposal=2,duration=duration_ms)
                single=buf.getvalue()
        if single[13:781]!=PALETTE or single[-1:]!=b';': raise G.FabricError('GIF encoder altered the byte palette')
        out.extend(b'\x21\xfe'+_blocks(G.canonical(car)));out.extend(single[781:-1])
        if len(out)>G.MAX_FILE_BYTES-1: raise G.FabricError('GIF export exceeds file budget')
    out.extend(b';');data=bytes(out)
    back,scan=_decode(data)
    if [r['blob'] for r in back]!=[r['blob'] for r in clean] or [r['tick'] for r in back]!=[r['tick'] for r in clean]:
        raise G.FabricError('GIF export failed exact state verification')
    G.atomic_bytes(path,data)
    return {'path':os.fspath(path),'kind':KIND,'frames':len(clean),'bytes':len(data),
            'sha256':scan['sha256'],'reversible':True,'authoritative':False,'order':'newest-first'}

def export_tiff(source,destination,*,limit=G.MAX_PAGES,duration_ms=100):
    if os.path.abspath(source)==os.path.abspath(destination): raise G.FabricError('export must not replace its source')
    hist=T.load_frames(source,limit=limit)
    try:
        records=[]
        for img in hist:
            car=T._car_from_tags(dict(img.encoderinfo['tiffinfo']),img.size)
            records.append({'blob':T._blob_from_image(img,car),'tick':car['tick'],'cols':car['grid']['cols']})
        return write_gif(records,destination,duration_ms=duration_ms)
    finally:
        for img in hist: img.close()

def restore_tiff(source,destination):
    """Staged conversion only. Caller must choose a new destination; no live adoption."""
    if os.path.lexists(destination): raise G.FabricError('restore requires a new TIFF destination')
    records=read_gif(source)['frames'];hist=[]
    try:
        for r in records[1:]:
            parts=T.parse_blob(r['blob']);img,geom=T._field_image(parts['slots'],r['cols'])
            img.encoderinfo={'tiffinfo':T._page_ifd(T._sidecar(parts,geom,r['tick']))};hist.append(img)
        r=records[0]
        return T.write_tif(r['blob'],destination,cols=r['cols'],tick=r['tick'],history=hist)
    finally:
        for img in hist: img.close()
