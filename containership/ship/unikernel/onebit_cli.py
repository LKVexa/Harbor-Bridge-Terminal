"""Local operator surface for the bounded UC 1-bit communication adaptation."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from . import Refusal, UC_RELEASE, SLOTS
from . import engines as E, safety as SAFE, tif_fabric as TF
from . import onebit as O


def configure(sp):
    p=sp.add_parser('onebit',help='bounded 1-bit communication tools; local compute remains full precision')
    sub=p.add_subparsers(dest='onebit_verb',required=True)
    q=sub.add_parser('status');q.set_defaults(fn=run)
    q=sub.add_parser('demo');q.add_argument('--count',type=int,default=512);q.add_argument('--rounds',type=int,default=12);q.set_defaults(fn=run)
    q=sub.add_parser('benchmark');q.add_argument('--count',type=int,default=2048);q.add_argument('--rounds',type=int,default=100);q.set_defaults(fn=run)
    q=sub.add_parser('inspect-packet');q.add_argument('source');q.set_defaults(fn=run)
    q=sub.add_parser('pack');q.add_argument('source',help='JSON array of finite numbers');q.add_argument('destination');q.add_argument('--sequence',type=int,default=0);q.add_argument('--source-id',type=int,default=0);q.add_argument('--destination-id',type=int,default=0);q.set_defaults(fn=run)
    q=sub.add_parser('tiff-read');q.add_argument('name');q.add_argument('slot',choices=SLOTS);q.add_argument('tile',type=int);q.set_defaults(fn=run)
    q=sub.add_parser('tiff-put');q.add_argument('name');q.add_argument('slot',choices=SLOTS);q.add_argument('tile',type=int);q.add_argument('source',help='1-bit packet file, max 464 bytes');q.add_argument('--generation',type=int,required=True);q.add_argument('--expect',required=True);q.set_defaults(fn=run)


def _emit(value):
    print(json.dumps(value,sort_keys=True,indent=2,default=str));return 0


def _read_values(path):
    p=Path(path)
    if p.is_symlink() or not p.is_file():raise Refusal('onebit input must be a regular file')
    if p.stat().st_size>4*1024*1024:raise Refusal('onebit JSON input exceeds 4 MiB')
    try:v=json.loads(p.read_text(encoding='utf-8'))
    except (OSError,UnicodeError,json.JSONDecodeError) as exc:raise Refusal('invalid onebit JSON input') from exc
    try:return O.values(v)
    except O.OneBitError as exc:raise Refusal(str(exc)) from exc


def _state_path(name,slot,live_only=False):
    from . import pixels_cli
    return pixels_cli.state_path(name,slot,live_only=live_only)


def _tiff_packet(name,slot,tile,live_only=False):
    if type(tile) is not int or not 0<=tile<4:raise Refusal('tile must be 0..3')
    path,kind=_state_path(name,slot,live_only=live_only);TF._validate_tif(str(path))
    t=TF.codec();state=t.read_tif(path);parts=t.parse_blob(state['blob']);packet=bytes(parts['slots'][2+tile])
    return t,path,kind,state,parts,packet


def run(a):
    try:
        if a.onebit_verb=='status':
            return _emit({**O.capability_record(),'uc_release':UC_RELEASE,'workflow':'use `uc onebit-workflow status` for JYRM 1BNCF v3.1.0 traceability'})
        if a.onebit_verb in ('demo','benchmark'):
            if type(a.count) is not int or not 1<=a.count<=O.MAX_SCALARS:raise Refusal('count must be 1..65536')
            block=[((i%17)-8)/8.0 for i in range(a.count)]
            if a.onebit_verb=='benchmark':
                return _emit({'schema':'UC/1BIT_BENCHMARK/1',**O.ab_compare(block),**O.benchmark(block,rounds=a.rounds)})
            cfg=O.ControllerConfig(warmup_blocks=4,stability_window=4,stability_cv=0.001,recovery_blocks=2)
            ctl=O.CommunicationController(cfg);steps=[]
            for _ in range(a.rounds):
                r=ctl.transmit(block,source=1,destination=2)
                steps.append({k:r.get(k) for k in ('sequence','transport','wire_bytes','mode_before','mode_after','fallback')})
            return _emit({'schema':'UC/1BIT_DEMO/1','steps':steps,'metrics':ctl.metrics(),'ab':O.ab_compare(block),'replay':O.replay([block]*min(8,a.rounds),config=cfg)})
        if a.onebit_verb=='pack':
            vv=_read_values(a.source);r=O.encode_onebit(vv,sequence=a.sequence,source=a.source_id,destination=a.destination_id)
            dst=Path(a.destination)
            if dst.exists():raise Refusal('destination already exists; refusing overwrite')
            dst.parent.mkdir(parents=True,exist_ok=True);SAFE.atomic_write(str(dst),r['packet'])
            return _emit({'schema':'UC/1BIT_PACK/1','path':str(dst),'sha256':r['packet_sha256'],'wire_bytes':r['wire_bytes'],'count':r['count'],'scale':r['scale'],'compression_ratio_vs_fp32':r['compression_ratio_vs_fp32']})
        if a.onebit_verb=='inspect-packet':
            p=Path(a.source)
            if p.is_symlink() or not p.is_file() or p.stat().st_size>O.MAX_PACKET_BYTES:raise Refusal('invalid packet file')
            r=O.decode_packet(p.read_bytes());r.pop('values',None);r.pop('signs',None)
            return _emit({'schema':'UC/1BIT_PACKET_INSPECT/1',**r})
        if a.onebit_verb=='tiff-read':
            t,path,kind,state,parts,packet=_tiff_packet(a.name,a.slot,a.tile)
            if not packet:return _emit({'schema':'UC/1BIT_TIFF/1','berth':a.name,'slot':a.slot,'tile':a.tile,'source':kind,'empty':True,'file_sha256':state['file_sha256']})
            r=O.decode_packet(packet);r.pop('values',None);r.pop('signs',None)
            return _emit({'schema':'UC/1BIT_TIFF/1','berth':a.name,'slot':a.slot,'tile':a.tile,'source':kind,'empty':False,'packet':r,'file_sha256':state['file_sha256']})
        if a.onebit_verb=='tiff-put':
            t,path,kind,state,parts,old=_tiff_packet(a.name,a.slot,a.tile,live_only=True)
            if kind!='live':raise Refusal('tiff-put requires initialized live state')
            if not isinstance(a.expect,str) or len(a.expect)!=64 or a.expect!=state['file_sha256']:raise Refusal('stale or invalid TIFF digest')
            p=Path(a.source)
            if p.is_symlink() or not p.is_file() or p.stat().st_size>O.TIFF_PACKET_LIMIT:raise Refusal('packet must be a regular file no larger than 464 bytes')
            packet=p.read_bytes();decoded=O.decode_onebit(packet)
            if old:
                try:
                    O.decode_onebit(old)
                except O.OneBitError as exc:
                    raise Refusal('refusing to overwrite a non-1-bit TIFF tile; use an empty or existing 1-bit carrier tile') from exc
            slots=list(parts['slots']);slots[2+a.tile]=packet;parts['slots']=slots;newblob=t.build_blob(parts)
            written=TF._write_next(str(path),newblob,state['tick'],expected_sha256=state['file_sha256'])
            return _emit({'schema':'UC/1BIT_TIFF_WRITE/1','berth':a.name,'slot':a.slot,'tile':a.tile,'sequence':decoded['sequence'],'count':decoded['count'],'packet_sha256':decoded['sha256'],'previous_payload_sha256':hashlib.sha256(old).hexdigest() if old else None,'file_sha256':written['sha256'],'pages':written['pages']})
        raise Refusal('unknown onebit operation')
    except O.OneBitError as exc:
        raise Refusal(str(exc)) from exc
