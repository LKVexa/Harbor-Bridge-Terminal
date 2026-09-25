# KVM host prerequisites (MC-002)

| Check | How verified | Failure code | Retryable |
|---|---|---|---|
| `/dev/kvm` exists | `open()` | `HOST_KVM_UNAVAILABLE` | no |
| runtime identity can open it (group `kvm`) | `open(O_RDWR)` | `HOST_KVM_PERMISSION` | no |
| transient EBUSY/EINTR/EAGAIN | `open()` errno | `HOST_KVM_TRANSIENT` | yes |
| `KVM_GET_API_VERSION == 12` | ioctl `0xAE00` | `HOST_KVM_INCOMPATIBLE` | no |
| required caps (IRQCHIP, USER_MEMORY, IOEVENTFD, IRQFD, MP_STATE + arch caps) | `KVM_CHECK_EXTENSION` | `HOST_KVM_INCOMPATIBLE` | no |
| arch ∈ {x86_64, aarch64} | `platform.machine()` | `HOST_KVM_INCOMPATIBLE` | no |
| device revoked after open | ioctl ENODEV | `HOST_KVM_UNAVAILABLE` | no |

Containers without `/dev/kvm` passthrough fail as `HOST_KVM_UNAVAILABLE`.
Nested virtualization is detected (`/sys/module/kvm_*/parameters/nested`) and
reported in `HostProfile.notes`; it must be certified as its own profile.
The profile is exposed via `HostProfile.to_dict()` (`PK_MICROVM_HOST/1`) to admission readiness and health.
