#!/bin/sh
# Rebuild the binary fixtures.  Requires gcc/binutils for x86_64.  Output is compared with FIXTURES.json.
set -eu
cd "$(dirname "$0")"
F="-nostdlib -static -no-pie -fno-pie -fno-stack-protector -O1 -ffreestanding -Wl,--build-id=sha1 -Wl,-z,noexecstack"
gcc $F -Wl,-e,ukplat_entry -o uk_good.elf src/uk_good.c
gcc $F -Wl,-e,ukplat_entry -DEXTRA='long uk_syscall_r_fork(void){return -1;}' -o uk_fork.elf src/uk_good.c
gcc $F -Wl,-e,ukplat_entry -DEXTRA='long uk_syscall_r_execve(void){return -1;}' -o uk_exec.elf src/uk_good.c
gcc $F -Wl,-e,ukplat_entry -DEXTRA='void *dlopen(const char *p, int f){(void)p;(void)f;return 0;}' -o uk_dlopen.elf src/uk_good.c
gcc $F -Wl,-e,ukplat_entry -DEXTRA='long uk_syscall_r_socket(void){return -1;}' -o uk_socket.elf src/uk_good.c
gcc $F -Wl,-e,ukplat_entry -DEXTRA='int ptrace(void){return -1;}' -o uk_ptrace.elf src/uk_good.c
gcc $F -Wl,-e,ukplat_entry -DEXTRA='__asm__(".globl uk_syscall_r_socket\n.type uk_syscall_r_socket,@notype\nuk_syscall_r_socket: ret");' -o uk_hidden_notype.elf src/uk_good.c
gcc $F -Wl,-e,ukplat_entry -Wl,--omagic -o uk_wx.elf src/uk_good.c
gcc $F -o solo5_good.elf src/solo5_good.c
gcc $F -o plain.elf src/plain.c
gcc -O1 -o dyn_fork_dlopen.elf src/dyn.c -ldl
strip -o uk_stripped.elf uk_good.elf
# header-patched copy: e_machine -> EM_AARCH64 (183); code stays x86 - used only for the arch-mismatch path
python3 - <<'PY'
b = bytearray(open("uk_good.elf", "rb").read()); b[18:20] = (183).to_bytes(2, "little")
open("uk_arch_aarch64.elf", "wb").write(bytes(b))
PY
