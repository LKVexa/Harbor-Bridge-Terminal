# Harbor `brctl` install location

Built by `scripts\build-brctl.cmd` from the linked Bottle Rocket product
(`mobile-platform/bottle-rocket/product`, Makefile target `.build/brctl`).

Requires **MSYS2 UCRT64** `gcc` + `make` + OpenSSL (`libcrypto`) on Windows.
The MinGW build drops upstream `-Werror` for Windows and injects `wincompat.h`
(`fsync`→`_commit`, `getline` shim).

Verified on MoneyMoneyMoney (2026-09-25 PT): `assemble examples/boot.mssl` **PASS**.
Full `selftest` may report host-side FAIL (assembler/persist/image/apdu/update) under
MinGW; that does not block Harbor compile assemble when the binary is present.

Do not commit secrets. Binary is Windows x86_64 PE.
