"""Local TIFF/GIF state tools; live edits are locked, digest-checked transactions."""
from __future__ import annotations
import hashlib
import importlib
import json
from pathlib import Path
import re
from . import Refusal, SLOTS, UC_RELEASE
from . import engines as E, tif_fabric as TF, safety as SAFE


def modules():
    t=TF.codec()
    return t,importlib.import_module('pa21studio.fabric_gif'),importlib.import_module('pa21studio.pixel_kernel')


def configure(sp):
    p=sp.add_parser('pixels',help='inspect TIFF pixel state, export reversible GIFs, or explicitly edit/checkpoint live state')
    sub=p.add_subparsers(dest='pixel_verb',required=True)
    q=sub.add_parser('status');q.set_defaults(fn=run)
    for verb in ('inspect','cell','export-gif','paint','checkpoint'):
        q=sub.add_parser(verb);q.add_argument('name');q.add_argument('slot',choices=SLOTS);q.set_defaults(fn=run)
        if verb in ('cell','paint'):
            q.add_argument('tile',type=int);q.add_argument('word',type=int)
        if verb=='paint':q.add_argument('value',type=int)
        if verb in ('paint','checkpoint'):
            q.add_argument('--generation',type=int,required=True)
            q.add_argument('--expect',required=True,help='current TIFF file SHA-256, from pixels inspect')
        if verb=='export-gif':q.add_argument('--limit',type=int,default=512)
    # Restore is offline: never takes a live berth target. Existing files cannot be replaced.
    q=sub.add_parser('restore-gif');q.add_argument('source');q.add_argument('destination');q.set_defaults(fn=run)


def state_path(name,slot,*,live_only=False):
    SAFE.validate_name(name)
    if slot not in SLOTS:raise Refusal('unknown pixel slot')
    if not Path(TF._berth_dir(name),'BERTH.json').is_file():raise Refusal('unknown berth')
    live=Path(TF.live_path(name,slot))
    if live.is_file():return live,'live'
    if live_only:raise Refusal('live TIFF does not exist; explicitly initialize the fabric first')
    return Path(TF.genesis_path(name,slot)),'sealed_genesis'


def _emit(value):
    print(json.dumps(value,sort_keys=True,indent=2));return 0


def run(a):
    t,g,k=modules()
    try:
        if a.pixel_verb=='status':
            return _emit({'schema':'UC/PIXEL_STATUS/1','uc_release':UC_RELEASE,'codec_version':t.CODEC_VERSION,
                          'live_format':'PA21FABTIF/1','gif_transport':g.KIND,'gif_is_live':False,
                          'max_tiff_bytes':t.G.MAX_FILE_BYTES,'max_pages':t.MAX_PAGES,
                          'guest_tiles':4,'u64_words_per_native_tile':k.WORDS,
                          'operations':['set','add','xor'],'overflow':'checked; wrapping must be explicit',
                          'platform':'local CPU; no GPU, OS-kernel or hypervisor claim'})
        if a.pixel_verb=='restore-gif':
            # An offline file can be reviewed and later explicitly adopted. No live overwrite API.
            dst=t.G.no_links(a.destination)
            root=Path(E.ship_root()).resolve()
            try:rel=dst.relative_to(root)
            except ValueError:rel=None
            if rel is not None and (not rel.parts or rel.parts[0] not in ('_runs','_scratch')):
                raise Refusal('offline restoration inside the ship must target _runs or _scratch, never sealed/live state')
            return _emit(g.restore_tiff(a.source,dst))
        path,kind=state_path(a.name,a.slot,live_only=a.pixel_verb in ('paint','checkpoint'))
        TF._validate_tif(str(path))
        state=t.read_tif(path)
        if a.pixel_verb=='inspect':
            return _emit({'schema':'UC/PIXEL_INSPECT/1','berth':a.name,'slot':a.slot,'source':kind,
                          'path':str(path),'file_sha256':state['file_sha256'],'tick':state['tick'],
                          'pages':state['pages'],'kernel':k.summary(state['blob']),'container':t.inspect(path)})
        if a.pixel_verb=='cell':
            return _emit({'schema':'UC/PIXEL_CELL/1','berth':a.name,'slot':a.slot,'source':kind,
                          'value':k.read_u64(state['blob'],a.tile,a.word),'address':k.coordinates(a.tile,a.word),
                          'file_sha256':state['file_sha256']})
        if a.pixel_verb=='export-gif':
            if not 1<=a.limit<=t.MAX_PAGES:raise Refusal('GIF export limit must be 1..512')
            base=Path(SAFE.contained_path(E.ship_root(),f'_runs/pixels/{a.name}/{a.slot}'))
            base.mkdir(parents=True,exist_ok=True)
            dest=base/f'{state["file_sha256"][:24]}-{a.limit}.gif'
            result=g.export_tiff(path,dest,limit=a.limit)
            return _emit({**result,'berth':a.name,'slot':a.slot,'source':kind,'live_state_changed':False})
        if not re.fullmatch(r'[0-9a-f]{64}',a.expect) or a.expect!=state['file_sha256']:
            raise Refusal('stale or invalid TIFF digest; inspect the live state again')
        if a.pixel_verb=='paint':
            return _emit(TF.paint(str(path),a.tile,a.word,a.value,expected_sha256=a.expect))
        if a.pixel_verb=='checkpoint':
            # Validate every raster before preserving/reducing the history; hashes alone are insufficient.
            frames=t.load_frames(path)
            try:
                original=t.G.read_bytes(path)
                if hashlib.sha256(original).hexdigest()!=a.expect:raise Refusal('TIFF changed during checkpoint preparation')
                base=Path(SAFE.contained_path(E.ship_root(),f'_runs/pixels/{a.name}/{a.slot}'))
                base.mkdir(parents=True,exist_ok=True)
                archive=base/f'{a.expect}.tif'
                if archive.exists():
                    if t.G.read_bytes(archive)!=original:raise Refusal('checkpoint archive collision')
                else:t.G.atomic_bytes(archive,original)
                if hashlib.sha256(t.G.read_bytes(archive)).hexdigest()!=a.expect:
                    raise Refusal('checkpoint archive verification failed')
                result=t.write_tif(state['blob'],path,cols=2,tick=state['tick'],expected_sha256=a.expect)
                return _emit({**result,'schema':'UC/PIXEL_CHECKPOINT/1','archive':str(archive),
                              'archive_sha256':a.expect,'previous_pages':state['pages'],
                              'logical_state_preserved':True})
            finally:
                for f in frames:f.close()
        raise Refusal('unknown pixel operation')
    except t.FabricError as exc:
        raise Refusal(str(exc)) from exc
