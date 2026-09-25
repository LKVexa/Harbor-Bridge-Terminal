"""Versioned local control contracts and honest execution capability selection."""
from __future__ import annotations
import os
import shutil
from . import Refusal, UC_RELEASE
from . import strictjson as J
from .safety import validate_name

SCHEMA = 'UC/CONTROL_REQUEST/1'
OPERATIONS = {'inspect', 'invoke', 'stop', 'snapshot', 'restore', 'boot'}
ISOLATIONS = {'host-process', 'hypervisor'}
ASSURANCES = ('byte_integrity', 'signature_authenticity', 'witness_agreement',
              'application_semantics', 'host_isolation')

def validate_request(value):
    if not isinstance(value, dict): raise Refusal('control request must be an object')
    required = {'schema', 'operation', 'workload', 'generation', 'isolation', 'capabilities'}
    if set(value) != required:
        raise Refusal('control request has missing or unknown fields',
                      {'missing': sorted(required-set(value)), 'unknown': sorted(set(value)-required)})
    if value['schema'] != SCHEMA: raise Refusal('unsupported control contract version')
    if not isinstance(value['operation'],str) or value['operation'] not in OPERATIONS: raise Refusal('unsupported control operation')
    validate_name(value['workload'])
    if type(value['generation']) is not int or not 1 <= value['generation'] < 2**63:
        raise Refusal('generation must be an integer from 1 to 2^63-1')
    if not isinstance(value['isolation'],str) or value['isolation'] not in ISOLATIONS: raise Refusal('unknown isolation class')
    caps = value['capabilities']
    if not isinstance(caps, list) or any(not isinstance(x, str) for x in caps) or len(caps) > 16 or len(caps) != len(set(caps)):
        raise Refusal('capabilities must be a unique bounded string list')
    if set(caps) - {'inspect', 'native-interpretation', 'metadata-witness'}:
        raise Refusal('unsupported capabilities', {'unsupported': sorted(set(caps)-{'inspect','native-interpretation','metadata-witness'})})
    J.canonical_bytes(value)
    return value

def capabilities():
    return {'schema': 'UC/CAPABILITIES/1', 'uc_release': UC_RELEASE,
            'selected_profile': 'trusted-local', 'backend': 'existing-host-adapters',
            'isolation_class': 'host-process', 'network_policy_enforced': False,
            'bootable_guest': False, 'authentication': 'OS account for local CLI; static hashed bearer credential for optional loopback VWS',
            'terminal_bridge': {'available': True, 'launcher': 'TERMINAL.cmd', 'profile': 'LOCAL_VOLATILE',
                                'default': 'read-only allowlist', 'bind': 'numeric loopback only',
                                'control': 'explicit --control plus ship.control capability',
                                'arbitrary_host_shell': False, 'child_memory_limit': 'NOT_ENFORCED'},
            'hypervisor_available': False, 'multi_host_enabled': False,
            'host_probes': {'kvm_device_present': os.path.exists('/dev/kvm'),
                            'qemu_on_path': shutil.which('qemu-system-x86_64') is not None},
            'probe_note': 'Device/PATH presence is informational, not isolation evidence.',
            'assurance_classes': list(ASSURANCES),
            'not_implemented': ['guest boot ABI', 'guest checkpoint/restore', 'guest stop supervision',
                                'tenant isolation', 'independent release trust', 'network filtering'],
            'note': 'Contract validation is not execution or authorization.'}

def require_backend(isolation='host-process'):
    if isolation != 'host-process':
        raise Refusal('required isolation backend is not implemented; fallback refused',
                      {'required': isolation, 'available': 'host-process'})
    return capabilities()
