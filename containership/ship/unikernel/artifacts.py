"""Typed artifact DAG and verified local content-addressed storage primitives.

No signatures, independently trusted builders or automatic executable admission
are supplied by this module. Every read verifies bytes, not authority.
"""
from __future__ import annotations
import hashlib
import os
import re
from pathlib import Path
from . import Refusal
from . import strictjson as J
from .safety import contained_path, atomic_write, ship_lock, reject_link

HEX = re.compile(r'[0-9a-f]{64}\Z')
KINDS = {'source', 'compiler', 'runtime', 'configuration', 'image', 'state_schema', 'evidence'}
MAX_BLOB = 64 * 1024 * 1024
MAX_STORE = 1024 * 1024 * 1024
MIN_FREE = 64 * 1024 * 1024

def validate_graph(value):
    if not isinstance(value, dict) or set(value) != {'schema', 'nodes'} or value['schema'] != 'UC/ARTIFACT_GRAPH/1':
        raise Refusal('invalid artifact graph contract')
    nodes = value['nodes']
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= 10000: raise Refusal('graph node count out of bounds')
    mapping = {}; edge_count = 0
    for node in nodes:
        if not isinstance(node, dict) or set(node) != {'id', 'kind', 'sha256', 'dependencies'}:
            raise Refusal('invalid artifact node fields')
        nid = node['id']
        if not isinstance(nid, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]{0,95}', nid):
            raise Refusal('invalid graph node ID')
        if nid in mapping: raise Refusal('duplicate graph node ID', {'id': nid})
        if not isinstance(node['kind'],str) or node['kind'] not in KINDS or not isinstance(node['sha256'], str) or not HEX.fullmatch(node['sha256']):
            raise Refusal('invalid graph kind or digest')
        deps = node['dependencies']
        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps) or len(deps) != len(set(deps)):
            raise Refusal('invalid or duplicated dependency edge')
        edge_count += len(deps)
        if edge_count > 100000: raise Refusal('graph edge budget exceeded')
        mapping[nid] = node
    for nid, node in mapping.items():
        for dep in node['dependencies']:
            if dep not in mapping: raise Refusal('missing graph dependency', {'id': nid, 'dependency': dep})
    # Kahn ordering, not recursive DFS: hostile depth cannot exhaust the stack.
    import heapq
    count = {k: len(n['dependencies']) for k,n in mapping.items()}
    reverse = {k: [] for k in mapping}
    for k,n in mapping.items():
        for d in n['dependencies']: reverse[d].append(k)
    ready = [k for k,v in count.items() if v == 0]; heapq.heapify(ready); order = []
    while ready:
        key = heapq.heappop(ready); order.append(key)
        for child in reverse[key]:
            count[child] -= 1
            if count[child] == 0: heapq.heappush(ready, child)
    if len(order) != len(mapping): raise Refusal('artifact dependency cycle')
    return {'schema': 'UC/GRAPH_RESULT/1', 'node_count': len(nodes), 'edge_count': edge_count,
            'order': order, 'graph_sha256': hashlib.sha256(J.canonical_bytes(value)).hexdigest()}

def affected(value, changed):
    valid = validate_graph(value); names = set(valid['order'])
    if not isinstance(changed, list) or not changed or any(c not in names for c in changed):
        raise Refusal('changed IDs must name existing graph nodes')
    selected = set(changed)
    nodes = {n['id']:n for n in value['nodes']}
    for nid in valid['order']:
        if set(nodes[nid]['dependencies']) & selected: selected.add(nid)
    return [nid for nid in valid['order'] if nid in selected]

class ObjectStore:
    def __init__(self, root):
        self.root = Path(root).absolute()
        self.base = Path(contained_path(str(self.root), '_runs/objects'))
    def path(self, digest):
        if not isinstance(digest, str) or not HEX.fullmatch(digest): raise Refusal('invalid SHA-256 object ID')
        return Path(contained_path(str(self.root), '_runs/objects/' + digest))
    def read(self, digest):
        p = self.path(digest)
        if not p.is_file(): raise Refusal('object is absent', {'sha256': digest})
        reject_link(str(p))
        with p.open('rb') as fh: data = fh.read(MAX_BLOB+1)
        if len(data) > MAX_BLOB or hashlib.sha256(data).hexdigest() != digest:
            raise Refusal('object bytes fail digest or size validation', {'sha256': digest})
        return data
    def put(self, data):
        import shutil
        if not isinstance(data, bytes) or len(data) > MAX_BLOB: raise Refusal('object exceeds byte budget')
        digest = hashlib.sha256(data).hexdigest()
        with ship_lock(str(self.root)):
            p = self.path(digest)
            if p.exists(): self.read(digest); return {'sha256':digest,'bytes':len(data),'created':False}
            self.base.mkdir(parents=True, exist_ok=True)
            total = 0
            for old in self.base.iterdir():
                reject_link(str(old))
                if not old.is_file(): raise Refusal('unexpected directory in object store')
                total += old.stat().st_size
            if total + len(data) > MAX_STORE or shutil.disk_usage(self.root).free < len(data)+MIN_FREE:
                raise Refusal('object store capacity exhausted')
            atomic_write(str(p), data, mode=0o600)
            self.read(digest)
            return {'sha256':digest, 'bytes':len(data), 'created':True}
