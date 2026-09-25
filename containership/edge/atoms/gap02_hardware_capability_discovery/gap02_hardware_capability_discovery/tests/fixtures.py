"""Hardware fixture library (MC-42 software half / MC-43 conformance inputs).
Each fixture is a synthetic host: files + fixed command replies."""
from gap02_hardware_capability_discovery.production.accelerators import NV_QUERY, NV_LIST, CLINFO, ROCM_SMI
from gap02_hardware_capability_discovery.production.evidence import Host

NV_OK = "GPU-aaaa-1, 0, 550.54.15, 81920, 80000, Disabled, 0\n"
NV_MIG = "GPU-aaaa-1, 0, 550.54.15, 81920, 80000, Enabled, 0\n"
NV_LIST_MIG = ("GPU 0: A100 (UUID: GPU-aaaa-1)\n"
               "  MIG 3g.40gb Device 0: (UUID: MIG-bbbb-1)\n"
               "  MIG 3g.40gb Device 1: (UUID: MIG-bbbb-2)\n")


def linux(files=None, commands=None, **kw):
    return Host(files=files or {}, commands=commands or {}, system="Linux", machine=kw.pop("machine", "x86_64"), **kw)


def nvidia(q=NV_OK, lst="", rc=0):
    return linux(commands={NV_QUERY: (rc, q), NV_LIST: (0, lst)})


CPUINFO_X86 = "processor\t: 0\nvendor_id\t: GenuineIntel\nflags\t\t: fpu sse4_2 avx avx2 aes vmx ept\n"
CPUINFO_ARM = "processor\t: 0\nFeatures\t: fp asimd aes sha2 atomics sve\nCPU implementer\t: 0x41\n"

NUMA2 = {
    "/sys/devices/system/node/node0/meminfo": "Node 0 MemTotal:  1024 kB\nNode 0 MemFree:  512 kB\n",
    "/sys/devices/system/node/node0/distance": "10 21",
    "/sys/devices/system/node/node0/cpulist": "0-3",
    "/sys/devices/system/node/node1/meminfo": "Node 1 MemTotal:  2048 kB\nNode 1 MemFree:  1024 kB\n",
    "/sys/devices/system/node/node1/distance": "21 10",
    "/sys/devices/system/node/node1/cpulist": "4-7",
    "/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages": "16",
}
