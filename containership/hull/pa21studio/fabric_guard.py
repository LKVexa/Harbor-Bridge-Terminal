"""Bounded binary admission for the UC pixel-state profile (not a general TIFF reader).

Checked before Pillow sees an immutable byte snapshot. Both TIFF directory widths
are understood; codecs/color models outside the byte-exact state profile fail
closed. Source standards and limits are recorded in docs/tiff/CONTRACT.md.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import tempfile

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_PAGES = 512
MAX_TAGS = 128
MAX_TAG_BYTES = 65536
MAX_TOTAL_TAG_BYTES = 4 * 1024 * 1024
MAX_SCALAR_BYTES = 4096
MAX_BLOB_BYTES = 28 + 8 * 8 + 4 * 512 + 4 * MAX_SCALAR_BYTES
MAX_RASTER_BYTES = 4096

class FabricError(RuntimeError):
    """An invalid or unsupported fabric input; no state should be committed."""

def uint(value, bits=64, name='integer'):
    if type(value) is not int or not 0 <= value < (1 << bits):
        raise FabricError(f'{name} must be an unsigned {bits}-bit integer')
    return value

def strict_json(raw):
    if not isinstance(raw, (str, bytes)) or len(raw) > MAX_TAG_BYTES:
        raise FabricError('metadata is missing or exceeds the byte budget')
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise FabricError(f'duplicate metadata key: {k}')
            out[k] = v
        return out
    def constant(value):
        raise FabricError(f'non-finite JSON constant: {value}')
    try:
        result = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        raise FabricError('invalid JSON metadata') from exc
    if not isinstance(result, dict):
        raise FabricError('metadata must be a JSON object')
    return result

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')

def no_links(path):
    p = Path(os.path.abspath(os.fspath(path)))
    for q in (p, *p.parents):
        if not q.exists() and not q.is_symlink():
            continue
        st = q.lstat()
        if stat.S_ISLNK(st.st_mode) or getattr(st, 'st_file_attributes', 0) & 0x400:
            raise FabricError('fabric I/O refuses symlinks and reparse points')
    return p

def read_bytes(path, limit=MAX_FILE_BYTES):
    p = no_links(path)
    if not p.is_file():
        raise FabricError('fabric input must be a regular file')
    with p.open('rb') as f:
        s = os.fstat(f.fileno())
        if not stat.S_ISREG(s.st_mode) or s.st_size > limit:
            raise FabricError('fabric input exceeds its byte budget or is not regular')
        data = f.read(limit + 1)
    if len(data) > limit:
        raise FabricError('fabric input grew beyond its byte budget')
    return data

def atomic_bytes(path, data, expected_sha256=None):
    """Same-directory replacement; caller serializes cooperating writers.

    expected_sha256 is optimistic concurrency, not a lock against hostile peers.
    A rename is the commit point; an OS power-loss durability guarantee is not
    claimed when the filesystem does not implement directory fsync.
    """
    if len(data) > MAX_FILE_BYTES:
        raise FabricError('fabric output exceeds the byte budget')
    p = no_links(path)
    if p.exists() and not p.is_file():
        raise FabricError('fabric output must be a regular file')
    if not p.parent.is_dir():
        raise FabricError('fabric output directory does not exist')
    def check():
        if expected_sha256 is not None:
            if hashlib.sha256(read_bytes(p)).hexdigest() != expected_sha256:
                raise FabricError('stale fabric digest; the image changed before commit')
    check()
    fd, name = tempfile.mkstemp(prefix='.px-', suffix='.tmp', dir=p.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        no_links(p); check()
        os.replace(name, p)
        if os.name != 'nt':
            d = os.open(p.parent, os.O_RDONLY)
            try: os.fsync(d)
            finally: os.close(d)
    finally:
        if os.path.exists(name): os.unlink(name)

TYPE_SIZES = {1:1,2:1,3:2,4:4,5:8,6:1,7:1,8:2,9:4,10:8,11:4,12:8,13:4,16:8,17:8,18:8}
INT_FORMATS = {1:'B',3:'H',4:'I',6:'b',8:'h',9:'i',13:'I',16:'Q',17:'q',18:'Q'}

def inspect_tiff(data, *, max_pages=MAX_PAGES):
    """Validate directories, all tag spans and all strip/tile spans before decoding."""
    if not isinstance(data, bytes) or len(data) > MAX_FILE_BYTES or len(data) < 8:
        raise FabricError('TIFF byte budget or truncated header')
    if data[:2] not in (b'II', b'MM'):
        raise FabricError('invalid TIFF byte-order signature')
    endian = '<' if data[:2] == b'II' else '>'
    def number(fmt, pos):
        n = struct.calcsize(fmt)
        span(pos, n, 'integer')
        return struct.unpack_from(endian + fmt, data, pos)[0]
    def span(pos, size, label):
        if type(pos) is not int or type(size) is not int or pos < 0 or size < 0 or pos > len(data) or size > len(data) - pos:
            raise FabricError(f'{label} span is outside the TIFF')
    magic = number('H', 2)
    if magic == 42:
        big, header, count_size, entry_size, ptr_size, cf, pf, first = False, 8, 2, 12, 4, 'H', 'I', number('I', 4)
    elif magic == 43:
        if len(data) < 16 or number('H', 4) != 8 or number('H', 6) != 0:
            raise FabricError('invalid BigTIFF offset width or reserved header')
        big, header, count_size, entry_size, ptr_size, cf, pf, first = True, 16, 8, 20, 8, 'Q', 'Q', number('Q', 8)
    else:
        raise FabricError('unsupported TIFF magic; expected 42 or 43')
    pages, seen, metadata, pixel_spans = [], set(), [(0, header)], []
    off = first
    total_tag_bytes = 0
    while off:
        if len(pages) >= max_pages:
            raise FabricError('fabric history page budget exceeded; checkpoint required')
        if off in seen:
            raise FabricError('cyclic TIFF IFD chain')
        if off < header or off % (8 if big else 2):
            raise FabricError('invalid or unaligned IFD offset')
        seen.add(off)
        count = number(cf, off)
        if not 1 <= count <= MAX_TAGS:
            raise FabricError('IFD tag count exceeds the profile budget')
        table_end = off + count_size + count * entry_size + ptr_size
        span(off, table_end - off, 'IFD table')
        metadata.append((off, table_end))
        tags, last = {}, -1
        for i in range(count):
            p = off + count_size + i * entry_size
            tag, typ = number('H', p), number('H', p + 2)
            if tag <= last:
                raise FabricError('duplicate or unordered TIFF tag')
            last = tag
            if typ not in TYPE_SIZES or (not big and typ in (16,17,18)):
                raise FabricError('unsupported TIFF datatype for this header')
            n = number('Q' if big else 'I', p + 4)
            size = n * TYPE_SIZES[typ]
            if size > MAX_TAG_BYTES:
                raise FabricError('TIFF tag payload exceeds its byte budget')
            total_tag_bytes += size
            if total_tag_bytes > MAX_TOTAL_TAG_BYTES:
                raise FabricError('cumulative TIFF metadata decoding budget exceeded')
            val = p + (12 if big else 8)
            if size > ptr_size:
                val = number(pf, val)
                if val < header:
                    raise FabricError('external tag value points into header')
                span(val, size, 'external tag')
                metadata.append((val, val + size))
            raw = data[val:val + size]
            if typ in INT_FORMATS:
                values = tuple(v[0] for v in struct.iter_unpack(endian + INT_FORMATS[typ], raw))
            elif typ == 2:
                if not raw or raw[-1:] != b'\0':
                    raise FabricError('TIFF ASCII tag must have a terminator')
                try: values = raw.rstrip(b'\0').decode('ascii')
                except UnicodeError as exc: raise FabricError('non-ASCII TIFF string') from exc
            else: values = raw
            tags[tag] = values
        def one(tag, default=None):
            v = tags.get(tag, (default,))
            if not isinstance(v, tuple) or len(v) != 1 or type(v[0]) is not int:
                raise FabricError(f'TIFF scalar tag {tag} is not a single integer')
            return v[0]
        w, h = one(256), one(257)
        if not 1 <= w <= 64 or not 1 <= h <= 32 or w * h * 4 > MAX_RASTER_BYTES:
            raise FabricError('TIFF raster dimensions exceed the fabric profile')
        if tags.get(258) != (8,8,8,8) or one(277) != 4 or one(262) != 2 or one(284,1) != 1:
            raise FabricError('fabric requires byte-exact chunky RGBA8, not color conversion')
        if one(274,1) != 1 or tags.get(338) != (2,) or tags.get(339,(1,)) not in ((1,),(1,1,1,1)):
            raise FabricError('unsupported orientation, alpha association or sample format')
        compression = one(259,1)
        if compression not in (1,5,8,32946,32773) or one(317,1) not in (1,2):
            raise FabricError('unsupported or lossy fabric compression/predictor')
        strip = 273 in tags or 279 in tags
        tile = 324 in tags or 325 in tags
        if strip == tile:
            raise FabricError('exactly one strip or tile storage layout is required')
        if strip:
            step = one(278,h)
            if step < 1: raise FabricError('RowsPerStrip must be positive')
            expected = (h + step - 1) // step
            offsets, sizes = tags.get(273), tags.get(279)
            storage = 'strips'
        else:
            tw, th = one(322), one(323)
            if tw < 1 or th < 1 or tw > 64 or th > 64 or tw * th * 4 > MAX_TAG_BYTES:
                raise FabricError('tile dimensions exceed the decode budget')
            expected = ((w + tw - 1) // tw) * ((h + th - 1) // th)
            offsets, sizes = tags.get(324), tags.get(325)
            storage = 'tiles'
        if not isinstance(offsets, tuple) or not isinstance(sizes, tuple) or len(offsets) != expected or len(sizes) != expected or expected > 64:
            raise FabricError('strip/tile offset and byte-count cardinality mismatch')
        if sum(sizes) > MAX_TAG_BYTES:
            raise FabricError('compressed raster exceeds its page budget')
        for start, size in zip(offsets, sizes):
            if size <= 0 or start < header: raise FabricError('invalid raster offset or byte count')
            span(start, size, 'raster')
            pixel_spans.append((start, start + size))
        pages.append({'page':len(pages), 'offset':off, 'width':w, 'height':h, 'compression':compression,
                      'storage':storage, 'tags':tags})
        off = number(pf, table_end - ptr_size)
    if not pages:
        raise FabricError('TIFF has no image directories')
    # Interval sweep: raster data may not alias any directory or metadata span.
    # O(n log n), not O(pages^2 * tags). Metadata aliases are legal.
    events = [(a,0,b) for a,b in metadata] + [(a,1,b) for a,b in pixel_spans]
    max_meta_end = max_pixel_end = -1
    for start, kind, end in sorted(events):
        if kind == 0:
            if start < max_pixel_end: raise FabricError('TIFF raster overlaps metadata')
            max_meta_end = max(max_meta_end,end)
        else:
            if start < max_meta_end: raise FabricError('TIFF raster overlaps metadata')
            if start < max_pixel_end: raise FabricError('TIFF raster spans overlap')
            max_pixel_end = max(max_pixel_end,end)
    return {'format':'BigTIFF' if big else 'TIFF', 'byte_order':'little' if endian=='<' else 'big',
            'pages':pages, 'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest()}


def raster_container(data, page):
    """Reframe one admitted RGBA8 raster as a minimal classic little-endian TIFF.

    Only decode-critical, validated tags cross into Pillow. Encoded strip/tile
    bytes are copied unchanged, never interpreted as metadata. The profile has
    only unsigned 8-bit samples, so changing directory endianness cannot change
    sample byte order, including byte-wise horizontal prediction. This also
    avoids the installed Pillow reader's big-endian BigTIFF header limitation.
    The input must be a page returned by inspect_tiff; this is an internal API.
    """
    tags=page['tags']; tile=page['storage']=='tiles'; ot,ct=(324,325) if tile else (273,279)
    blocks=[data[start:start+count] for start,count in zip(tags[ot],tags[ct])]
    # SHORTs for sample descriptors; LONGs for dimensions and local byte offsets.
    types={256:4,257:4,258:3,259:3,262:3,277:3,284:3,317:3,338:3,339:3}
    types.update({322:4,323:4,324:4,325:4} if tile else {273:4,278:4,279:4})
    values={tag:tags[tag] for tag in types if tag in tags}
    if not tile:values[278]=(min(page['height'],tags.get(278,(page['height'],))[0]),)
    values[ot]=tuple(0 for _ in blocks);values[ct]=tuple(len(b) for b in blocks)
    keys=sorted(values);base=8+2+len(keys)*12+4
    def build(offsets):
        table=bytearray(struct.pack('<H',len(keys)));extra=bytearray()
        for tag in keys:
            vals=offsets if tag==ot else values[tag];typ=types[tag];fmt='H' if typ==3 else 'I'
            raw=struct.pack('<'+fmt*len(vals),*vals)
            table.extend(struct.pack('<HHI',tag,typ,len(vals)))
            if len(raw)<=4:table.extend(raw+bytes(4-len(raw)))
            else:
                table.extend(struct.pack('<I',base+len(extra)));extra.extend(raw)
                if len(extra)%2:extra.append(0)
        table.extend(bytes(4))
        return b'II*\0'+struct.pack('<I',8)+table+extra
    preliminary=build(values[ot]);cursor=len(preliminary);offsets=[]
    for block in blocks:offsets.append(cursor);cursor+=len(block)
    return bytes(build(tuple(offsets)))+b''.join(blocks)
