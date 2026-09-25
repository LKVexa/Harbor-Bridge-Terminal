"""Checked little-endian u64 operations over the four TIFF logical guest tiles.

The kernel is a deterministic local CPU implementation, not an OS kernel,
GPU backend, JIT or a new VM ISA. It is called by the active ship paint path.
A patch batch is validated on a private copy and either returns a complete
new blob or raises without modifying its input. Disk commit belongs to the
ship's locking/transaction and TIFF atomic-replacement layers.
"""
from __future__ import annotations
import hashlib
import struct
from . import fabric_tif as T
from . import fabric_guard as G

SCHEMA='UC/PIXEL_KERNEL/1'
PAYLOAD_BYTES=464
WORDS=PAYLOAD_BYTES//8
MASK=(1<<64)-1
MAX_OPS=1024

def _address(tile,word):
    if type(tile) is not int or not 0<=tile<4 or type(word) is not int or not 0<=word<WORDS:
        raise G.FabricError('pixel address requires tile 0..3 and u64 word 0..57 (464-byte VM payload)')
    return tile+2,word*8

def coordinates(tile,word,cols=2):
    _address(tile,word);T._grid(cols)
    # One u64 is exactly two adjacent RGBA8 pixels, in little-endian byte order.
    px=word*2
    return {'tile':tile,'word':word,'slot':tile+2,'byte_offset':word*8,
            'pixels':[[tile%cols*16+(px+i)%16,tile//cols*8+(px+i)//16] for i in (0,1)],'byte_order':'little'}

def read_u64(blob,tile,word):
    parts=T.parse_blob(T.normalize_blob(blob));slot,off=_address(tile,word);b=parts['slots'][slot]
    if off+8>len(b): raise G.FabricError('pixel word is outside the initialized payload')
    return struct.unpack_from('<Q',b,off)[0]

def apply(blob,operations,*,expected_sha256=None):
    normalized=T.normalize_blob(blob)
    digest=hashlib.sha256(normalized).hexdigest()
    if expected_sha256 is not None and expected_sha256!=digest: raise G.FabricError('stale logical-state digest')
    if not isinstance(operations,(list,tuple)) or not 1<=len(operations)<=MAX_OPS: raise G.FabricError('patch batch must contain 1..1024 operations')
    parts=T.parse_blob(normalized);original_slots=parts['slots'];slots=[bytearray(s) for s in original_slots];events=[]
    for item in operations:
        if not isinstance(item,dict) or not {'tile','word','op','value'}<=set(item) or set(item)-{'tile','word','op','value','overflow','expect'}:
            raise G.FabricError('invalid pixel operation fields')
        idx,off=_address(item['tile'],item['word']);value=G.uint(item['value'],name='pixel value')
        op=item['op'];mode=item.get('overflow','checked')
        if op not in ('set','add','xor') or mode not in ('checked','wrap') or (op!='add' and 'overflow' in item):
            raise G.FabricError('unsupported pixel operation or overflow mode')
        buf=slots[idx]
        if len(buf)>PAYLOAD_BYTES: raise G.FabricError('pixel payload exceeds native VM capacity')
        if len(buf)<off+8:
            if op!='set': raise G.FabricError('arithmetic requires an initialized u64 cell')
            buf.extend(bytes(off+8-len(buf)))
        before=struct.unpack_from('<Q',buf,off)[0]
        if 'expect' in item and G.uint(item['expect'],name='expected cell')!=before: raise G.FabricError('pixel compare-and-swap mismatch')
        after=value if op=='set' else before^value if op=='xor' else before+value
        if after>MASK:
            if mode!='wrap': raise G.FabricError('u64 addition overflow')
            after&=MASK
        struct.pack_into('<Q',buf,off,after)
        events.append({'tile':item['tile'],'word':item['word'],'before':before,'after':after,'op':op})
    parts['slots']=[bytes(s) for s in slots];out=T.build_blob(parts)
    dirty=[k for k in range(4) if parts['slots'][k+2]!=original_slots[k+2]]
    return {'schema':SCHEMA,'blob':out,'before_sha256':digest,'after_sha256':hashlib.sha256(out).hexdigest(),
            'dirty_tiles':dirty,'operations':events,'changed':out!=normalized,'arithmetic':'u64-little-endian'}

def summary(blob):
    normalized=T.normalize_blob(blob);p=T.parse_blob(normalized)
    return {'schema':SCHEMA,'monotonic':p['monotonic'],'clock':p['clock'],
            'blob_sha256':hashlib.sha256(normalized).hexdigest(),'byte_order':'little','word_bits':64,
            'max_guest_payload_bytes':PAYLOAD_BYTES,'max_words_per_tile':WORDS,
            'tiles':[{'tile':k,'bytes':len(p['slots'][k+2]),'complete_u64_cells':len(p['slots'][k+2])//8,
                      'sha256':hashlib.sha256(p['slots'][k+2]).hexdigest()} for k in range(4)]}

def diff(before,after):
    a=T.parse_blob(T.normalize_blob(before));b=T.parse_blob(T.normalize_blob(after));changes=[]
    for tile in range(4):
        old,new=a['slots'][tile+2],b['slots'][tile+2]
        for word in range((max(len(old),len(new))+7)//8):
            x,y=old[word*8:(word+1)*8],new[word*8:(word+1)*8]
            if x!=y: changes.append({'tile':tile,'word':word,'before_hex':x.hex(),'after_hex':y.hex()})
    return {'schema':'UC/PIXEL_DIFF/1','changed_cells':changes,
            'scalar_slots_changed':[i for i in (0,1,6,7) if a['slots'][i]!=b['slots'][i]],
            'counters_changed':any(a[k]!=b[k] for k in ('monotonic','clock'))}
