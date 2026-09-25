# INV-34 Compatibility Contract

## Python

The reference logic uses only the Python standard library and targets modern CPython versions supporting dataclass `slots` and PEP 604 unions (Python 3.10+).

## Hypervisor and guest compatibility

No concrete hypervisor or guest operating system is certified by this ZIP. A deployment may enable expansion only after its external compatibility layer establishes all of the following:

- hypervisor CPU hot-add support for the VM type;
- guest ACPI CPU hot-plug support;
- guest ability to online newly presented CPUs;
- configured VM maximum vCPU count;
- current host capacity/headroom;
- stable observation of online-vCPU count after a request.

A versioned matrix covering specific hypervisor, machine type, firmware, guest kernel/OS and control-plane adapter versions remains a required production artifact and is listed in `MISSING_COMPONENTS.md`.
