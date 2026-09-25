"""Read-only inspection surface for bounded UC-2.8.0 platform primitives."""
from __future__ import annotations
from . import engines as E
from . import platform_services as P
from . import kernel_contracts as K
from .cli import _emit

def configure(sp):
    p=sp.add_parser('platform',help='inspect bounded local platform-service capabilities')
    p.add_argument('verb',choices=('status','health','hardware','kernel','compatibility','audit-check'))
    p.set_defaults(fn=run)

def _edge(root):
    try:
        from . import edge_atoms as X
        st=X.status(root)
        return {k:st[k] for k in ('elements','variants','requested_archives','stored_unique_archives','bound_to_pk_components','recorded_evidence')}
    except Exception as exc:  # noqa: BLE001 -- inspection must not fail on a ship without edge atoms
        return {'absent':True,'reason':str(exc)}

def run(a):
    root=E.ship_root()
    if a.verb=='health': value=P.health_snapshot(root)
    elif a.verb=='hardware': value=P.hardware_capabilities()
    elif a.verb=='kernel': value=K.descriptor()
    elif a.verb=='compatibility': value=P.compatibility_matrix()
    elif a.verb=='audit-check': value=P.AuditLedger(root).verify()
    else:
        from . import master_workflow as M
        value={'schema':'UC/PLATFORM_STATUS/1','candidate':'UC-2.8.0','health':P.health_snapshot(root),
               'hardware':P.hardware_capabilities(),'kernel':K.descriptor(),'compatibility':P.compatibility_matrix(),
               'master_workflow':M.status(root),
               'edge_atoms':_edge(root),
               'boundaries':['local process only','no hypervisor guest backend','no multi-host consensus','no production key authority']}
    return _emit(value)
