#!/usr/bin/env python3
"""Photon status — report what this vendored Photon can and cannot do, honestly.

Usage:  python PHOTON_STATUS.py [--json]

Exit codes
  0  Photon present and internally consistent (control plane usable; host UNBOUND is expected)
  1  Photon present but internally inconsistent (files missing or checksums drifted)
  2  Photon not found
"""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CP = HERE / 'control_plane'
SHELL = HERE / 'shell'


def _sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8'))
    except Exception:
        return default


def check_inventory():
    """Verify PHOTON/SHA256SUMS.txt against what is actually on disk."""
    sums = HERE / 'SHA256SUMS.txt'
    rec = {'inventory_file': sums.name, 'expected': 0, 'verified': 0,
           'missing': [], 'mismatched': [], 'ok': False}
    if not sums.is_file():
        rec['error'] = 'SHA256SUMS.txt missing'
        return rec
    rows = []
    for line in sums.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        digest, _, rel = line.partition('  ')
        if digest and rel:
            rows.append((digest.lower(), rel))
    rec['expected'] = len(rows)
    for digest, rel in rows:
        p = HERE / Path(*rel.split('/'))
        if not p.is_file():
            rec['missing'].append(rel)
            continue
        try:
            got = _sha256(p)
        except OSError as e:
            rec['mismatched'].append({'path': rel, 'error': str(e)})
            continue
        if got != digest:
            rec['mismatched'].append({'path': rel, 'expected': digest, 'actual': got})
        else:
            rec['verified'] += 1
    rec['ok'] = not rec['missing'] and not rec['mismatched'] and rec['expected'] > 0
    return rec


def main():
    ap = argparse.ArgumentParser(description='Report Photon installation status.')
    ap.add_argument('--json', action='store_true', help='emit the full record as JSON')
    a = ap.parse_args()

    if not CP.is_dir() and not SHELL.is_dir():
        print('PHOTON: not found beside this script', file=sys.stderr)
        return 2

    host = _load(CP / 'config' / 'photon_host.json', {}) or {}
    manifest = _load(HERE / 'MANIFEST.json', {}) or {}
    inv = check_inventory()

    out = {
        'schema': 'PHOTON/STATUS/1',
        'photon_root': str(HERE),
        'host_product': host.get('host_product', 'UNKNOWN'),
        'host_product_root': host.get('host_product_root', 'UNKNOWN'),
        'integration_profile': host.get('integration_profile', 'UNKNOWN'),
        'bound': bool(host.get('bound')),
        'photon_version': manifest.get('photon_version'),
        'control_plane_version': manifest.get('control_plane_version'),
        'shell_version': manifest.get('shell_version'),
        'python': sys.version.split()[0],
        'python_ok': sys.version_info >= (3, 10),
        'components': {
            'control_plane': CP.is_dir(),
            'shell': SHELL.is_dir(),
            'bridge': (HERE / 'bridge').is_dir(),
        },
        'inventory': inv,
        'available_now': [
            'electron identity, canonical state and semantic validation',
            'snapshot / fork / lineage / restore / diff / equivalence',
            'append-only hash-chained event ledger with full verification',
            'execution receipts and evidence records',
            'security policy, filesystem confinement, quota enforcement',
            'offline dashboard UI (static surfaces)',
        ],
        'blocked_until_bound': [
            'host attestation (no node reports bound)',
            'host build of native products',
            'workload execution and cross-node differential comparison',
            'promotion of any electron to VERIFIED',
            'shell Fabric attestation, topology and diagnostic surfaces',
        ],
        'to_bind': 'edit PHOTON/control_plane/vec1/dfbridge.py; see PHOTON/bridge/BRIDGE_CONTRACT.md',
    }
    out['ok'] = bool(inv['ok'] and out['python_ok'] and out['components']['control_plane'])

    if a.json:
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0 if out['ok'] else 1

    w = print
    w(f"Photon            : {out['photon_version']}  (control plane {out['control_plane_version']}, shell {out['shell_version']})")
    w(f"Host product      : {out['host_product']}")
    w(f"Integration       : {out['integration_profile']}   bound={out['bound']}")
    w(f"Python            : {out['python']}  ({'ok' if out['python_ok'] else 'NEEDS 3.10+'})")
    w(f"Inventory         : {inv['verified']}/{inv['expected']} files verified"
      + (f"  MISSING={len(inv['missing'])}" if inv['missing'] else '')
      + (f"  MISMATCHED={len(inv['mismatched'])}" if inv['mismatched'] else ''))
    w('')
    w('Working now:')
    for x in out['available_now']:
        w(f'  + {x}')
    w('')
    w('Blocked until a host bridge is written (by design, fail-closed):')
    for x in out['blocked_until_bound']:
        w(f'  - {x}')
    w('')
    w(f"To bind: {out['to_bind']}")
    return 0 if out['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
