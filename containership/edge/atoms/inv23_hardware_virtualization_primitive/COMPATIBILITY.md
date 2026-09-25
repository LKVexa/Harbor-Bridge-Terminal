# INV-23 compatibility matrix

_Generated from `compatibility.json` by `tools/gen_compat.py`; do not edit by hand._

Only rows marked **verified** carry hardware/VM evidence. No row is production-supported until it is verified.

| Status | Meaning |
|---|---|
| verified | hardware/VM-backed test evidence recorded |
| implemented-unverified | backend path implemented and unit-tested with mocks; awaiting lab evidence - NOT production-supported |
| experimental | implemented, platform code never executed on real hardware |
| unsupported | fails explicitly with indeterminate |

| ID | OS | Versions | Arch | CPU | Technology | Backend | Nested | Claim provider | Status | Expected | Limitations | Last verified |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LNX-BM-INTEL | linux | >=4.19 | x86_64 | Intel | VT-x+EPT | linux-kvm | no (L0) | posix-flock | **implemented-unverified** | usable/ok, bare_metal=true | — | — |
| LNX-BM-AMD | linux | >=4.19 | x86_64 | AMD | AMD-V+NPT | linux-kvm | no (L0) | posix-flock | **implemented-unverified** | usable/ok, bare_metal=true | — | — |
| LNX-GUEST-NOVT | linux | >=4.19 | x86_64 | any | none exposed | linux-kvm | L1 guest, VMX/SVM hidden | posix-flock | **verified** | absent/capability_absent, bare_metal=false | depth reported null (unknown), never 0 | 2026-09-23 (Anthropic cloud sandbox, Linux 6.18 x86_64 GenuineIntel guest, Python 3.11.15) |
| LNX-GUEST-NESTED | linux | >=4.19 | x86_64 | any | VT-x/AMD-V exposed | linux-kvm | L1 guest with nested virt | posix-flock | **implemented-unverified** | usable/ok, bare_metal=false | exact depth unobservable: nesting_depth null; claim requires allow_unknown_depth | — |
| LNX-NO-DEVKVM | linux | >=4.19 | x86_64 | any | VT-x/AMD-V | linux-kvm | any | posix-flock | **implemented-unverified** | present-disabled/device_absent, bare_metal=false | module not loaded or firmware-disabled; indistinguishable without dmesg | — |
| LNX-DEVKVM-EACCES | linux | >=4.19 | x86_64 | any | VT-x/AMD-V | linux-kvm | any | posix-flock | **implemented-unverified** | present-disabled/permission_denied, bare_metal=false | — | — |
| LNX-CTR-HIDDEN | linux | >=4.19 | x86_64 | any | container, device not passed | linux-kvm | any | posix-flock | **implemented-unverified** | present-disabled/device_absent, bare_metal=false | cpuinfo reflects host CPU | — |
| LNX-CTR-PASSTHRU | linux | >=4.19 | x86_64 | any | container with /dev/kvm | linux-kvm | any | posix-flock (per container unless state dir shared) | **implemented-unverified** | usable/ok, bare_metal=true | claim namespace is per state directory | — |
| LNX-ARM64 | linux | any | aarch64 | any | KVM/arm64 | none | n/a | posix-flock | **unsupported** | indeterminate/unsupported_architecture, bare_metal=false | — | — |
| WIN-X64-INTEL-HV | windows | 10 1803+, Server 2019+ | amd64 | Intel | VT-x+EPT, Hyper-V on | windows-whpx | root partition | windows-lockfile | **experimental** | usable/ok, bare_metal=false | depth unknown inside the root partition | — |
| WIN-X64-AMD-HV | windows | 10 1803+, Server 2019+ | amd64 | AMD | AMD-V+NPT, Hyper-V on | windows-whpx | root partition | windows-lockfile | **experimental** | usable/ok, bare_metal=false | — | — |
| WIN-X64-HV-OFF | windows | 10 1803+ | amd64 | any | Hyper-V/WHPX feature off | windows-whpx | L0 | windows-lockfile | **experimental** | present-disabled/kernel_api_unavailable, bare_metal=false | — | — |
| WIN-GUEST-NESTED-OFF | windows | 10+ | amd64 | any | guest without nested | windows-whpx | L1 | windows-lockfile | **experimental** | indeterminate/firmware_disabled, bare_metal=false | public API cannot separate firmware-off from absent | — |
| WIN-ARM64 | windows | any | arm64 | any | n/a | none | n/a | windows-lockfile | **unsupported** | indeterminate/unsupported_architecture, bare_metal=false | — | — |
| MAC-ARM64-HVF | darwin | 11+ | arm64 | Apple | Hypervisor.framework | macos-hvf | L0 | posix-flock | **experimental** | usable/ok, bare_metal=true | entitlement com.apple.security.hypervisor not verified by probe | — |
| MAC-X64-HVF | darwin | 10.15+ | x86_64 | Intel | Hypervisor.framework | macos-hvf | L0 | posix-flock | **experimental** | usable/ok, bare_metal=true | — | — |
| MAC-VIRTUALIZED | darwin | 11+ | any | any | macOS guest | macos-hvf | L1 | posix-flock | **experimental** | absent/capability_absent, bare_metal=false | — | — |
| OTHER-OS | freebsd/other | any | any | any | bhyve/other | none | n/a | none | **unsupported** | indeterminate/unsupported_platform, bare_metal=false | — | — |
