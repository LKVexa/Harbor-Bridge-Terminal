# Optical desktop (VB-JA21 9.8.7)

Harbor opens the local gateway URL inside **VB-JA21 Portable Optical Desktop**
(the WPF/WebView2 omni-bin window), **not** the Windows default browser.

## On-disk layout

```
optical-desktop/
  PRODUCT_LINK.txt     absolute path to the Downloads portable (committed)
  VERSION              9.8.7 (committed)
  portable/            directory junction → JA21-Portable-Desktop-9.8.7 (gitignored)
```

Create / refresh the junction:

```bat
scripts\link-optical-desktop.cmd
```

`START_HARBOR.cmd` calls that automatically. The Downloads source is never
modified in place.

## How the start URL is passed

JA21 9.8.7 reads **`JA21_START_URL`** (environment) and/or PowerShell
`-StartUrl` on `host\Start-JA21Browser.ps1`. On window load the presenter
navigates the active tab to that URL (omni address / start navigation).

Harbor sets both after the gateway listens on `127.0.0.1:<port>/`, and sets `JA21_ALLOW_PRIVATE_HOSTS=1` so loopback is inside the JA21 network boundary (otherwise JA21 shows *Addresses on this machine or this private network are outside the JA21 network boundary*):

- `bridge-terminal\tools\start-local.js` — primary path from `START_HARBOR.cmd`
- `START_HARBOR_BROWSER.cmd` — launch JA21 alone (probes ports 10000–10019 if
  no URL argument is given)

There is **no** `start http://...` / Edge / Chrome call.

## Sign-in inside JA21

Paste the contents of repo-root **`ACCESS_TOKEN.txt`** (local only, gitignored)
into the Harbor sign-in box inside the JA21 window. Same token workflow as before.

## Electron vendor adapter (secondary)

`bridge-terminal\vendor\browser\` remains an optional Electron `BrowserView`
slot. The portable JA21 is a standalone WPF host, so the **primary** integration
is this optical-desktop junction + start-URL launch — not the Electron pane.