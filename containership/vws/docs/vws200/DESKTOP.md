# Desktop (LOCAL) profile: what changed and what could not be run

**Electron was not executed in this run.** `npm install` is blocked by the environment's egress policy, so there is no Electron binary, no GUI session and no Windows host. Every change below is either a pure function with unit tests (`tests/desktop-ipc/guard.test.js`, `tests/ui/client-units.test.js`) or a small, reviewed edit to Electron-facing code that has passed `node --check` only. First launch on a real desktop is an OPEN acceptance step (I041, I043–I045, I055).

## IPC authorization (F11 / I041)

`src/main/ipc-guard.js`, applied to every channel in `main.js` through one gate: (1) sender is our window's `webContents`, top-level frame, URL equal to our `index.html` file URL; (2) payload matches the channel's exact shape (geometry, `sN` ids, input <= 65 536 chars, `SIGINT` only, dock fractions 0..1, no payload where none is expected); (3) session-scoped channels require that this sender opened the session. Output and exit events are sent only to the owning renderer; sessions are closed when their renderer is destroyed. The main window refuses navigation and `window.open`.

New channel `spiral:start` releases the open barrier; `spiral:open` accepts `deferStart`. The renderer reaches them only through `client/ipc-adapter.js`.

## Browser capabilities (F12 / I042)

Browser commands (`browser`, `open`) and Photon delegation are **not installed** in remote workers, `hello` advertises `browserPane:false`, and the web page hides the pane chrome. A remote session therefore has no path to the desktop pane. Locally the pane remains a capability of the owning renderer only.

## Navigation (F16 / I044)

`src/main/nav-policy.js`: allow `https:`, `http:`, `about:blank`, and schemes a vendored adapter lists in `internalSchemes`; refuse `file: data: blob: javascript: chrome: devtools: view-source:` and custom handlers, URLs with credentials, and anything over 2048 chars — for typed input, `window.open`, `will-navigate` and `will-redirect`. Permission requests and checks are denied; `<webview>` attachment is prevented. The pane re-checks even a vendored adapter's resolution.

**BrowserView -> WebContentsView.** Electron deprecates `BrowserView` in favour of `WebContentsView` (series R16/R17). The migration touches `_ensureView`, `show`/`hide` (`contentView.addChildView/removeChildView` instead of `setBrowserView`), and `reflow`. It was **not performed**: it cannot be exercised without Electron, and an untested rewrite of the only browser surface would be worse than the deprecation. Recommended as the first desktop task once a pinned Electron version is installed.

## Adapter discovery and packaging (F14, F15 / I043, I045)

Discovery order: `<resources>/browser/index.js` (where electron-builder's `extraResources` puts `vendor/browser` in a packaged app) then repository `vendor/browser/index.js`; an adapter must expose `attach`, `navigate`, `resolveUrl`. `state()` reports `engineSource: vendored | builtin-fallback`. The supplied archive still contains no VB-JA21 bundle, so the engine is the Chromium fallback and is labelled as such. `package.json` now ships `client/**` and `protocol/**`. No lockfile exists; desktop reproducibility is OPEN.

## Profile parity

| Capability | LOCAL | WEB |
|---|---|---|
| VT rendering, tabs, scrollback, keyboard, paste, IME surface | same code | same code (OBSERVED in Chromium) |
| Shell built-ins, pipelines, VFS | yes, unlimited VFS | yes, quotas |
| `df` / `fabric` / `node` | full arguments, `df use`, Photon delegation | allowlisted arguments, operator root, no Photon; per-principal |
| Browser pane, window controls | yes | reported unavailable |
| Status bar cwd / node hub | live | connection state, fabric on/off |
| Sessions share a filesystem | yes (single user) | no (process per session) |
