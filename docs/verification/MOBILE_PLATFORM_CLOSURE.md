# Mobile platform / cubby closure (America/Los_Angeles)

Generated: 2026-09-25 ~14:30 PT (MoneyMoneyMoney)

## Primary architecture
- Enter Harbor = **cubby spawn + browser projection on local 127**.
- Device does **not** download the VM.
- QVM + containership are cubbies too; desktop projects them directly.
- Mobile must create live BR mobile cubby (`MC-*`) before QVM/containership attach (403 `mobile_br_cubby_required` otherwise).

## 1. brctl (cubby materializer)
- Installed: `mobile-platform/compiler/bin/brctl.exe`.
- `brctl assemble` = cubby image prep (PASS historically).
- `brctl serve` listed in help — advanced host-state hint; Harbor projection page is the browser path.

## 2. Sideload (demoted)
- `adb` optional; delivery evidence under `docs/verification/mobile-delivery/`.
- Not the enter-Harbor path.

## 3. SPIRAL → mobile cubby
- `mobile-auth-hook.js` allocates `MC-*`, writes session, enriches ticket with `projection_url`.
- Evidence: `docs/verification/mobile-cubby/`.

## Gaps
- Full BR UI embedded in projection page vs stub.
- Real device `adb` push when platform-tools present.
