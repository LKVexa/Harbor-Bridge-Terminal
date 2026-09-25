# Mobile platform closure verification (America/Los_Angeles)

Generated: 2026-09-25 ~14:15 PT (MoneyMoneyMoney)

## 1. brctl
- Built with MSYS2 UCRT64 `gcc` + `make` + OpenSSL via `scripts/build-brctl.cmd` pattern (wincompat.h shim).
- Installed: `mobile-platform/compiler/bin/brctl.exe` (144137 bytes).
- `brctl assemble examples/boot.mssl …` → **PASS** (176-byte BRIM).
- `brctl selftest` → FAIL (5 host cases under MinGW: assembler/persist/image/apdu/update). Compile contract uses **assemble**, which succeeds.
- Compile step `brctl-assemble` status **ok** with `payload/boot.brimg` present.

## 2. Physical device delivery
- `adb` **not** on PATH and not under common Android SDK locations on this machine.
- `deliver-mobile-vm-node` → **staged** (honest); evidence under `docs/verification/mobile-delivery/`.
- `--wait-device` supported; with no `adb`, remains staged (does not fake push).
- No real device push performed (no device / no adb).

## 3. SPIRAL login → mobile-auth hook
- Wired: `bridge-terminal/gateway/mobile-auth-hook.js` called after successful `POST /api/ws-ticket`.
- `start-local` enables hook + `watch-auth-queue.js` by default; disable `HARBOR_MOBILE_AUTH_HOOK=0`.
- Measured probe (port 10017): Bearer ticket mint returned 200; hook wrote queue job + `docs/verification/mobile-auth-hook/LATEST.json` with `fired: true`, platform `android` from `X-Harbor-Mobile-Platform` header, principal `local/operator`.

## Gaps remaining
- Install Android platform-tools + connect a device to exercise real `adb push`.
- MinGW `brctl selftest` failures (upstream POSIX surface); assemble works.
- iOS delivery remains staged-only (no Apple deploy automation).
