# Browser pane integration — VB-JA21 v9.8.7

HERMIT's browser pane is engine-agnostic. It ships with a working fallback
(plain Chromium `BrowserView`) so the app runs immediately, and it auto-detects
a vendored browser here.

## Primary Harbor path (standalone omni-bin)

For `START_HARBOR.cmd`, Harbor does **not** rely on this Electron slot. The
gateway URL is opened in the **standalone VB-JA21 Portable Optical Desktop**
(WPF/WebView2) via:

- `optical-desktop\portable\` (junction) + `JA21_START_URL` / `-StartUrl`
- see repo-root `optical-desktop\README.md` and `START_HARBOR_BROWSER.cmd`

That is the supported way to put `http://127.0.0.1:<port>/` into JA21's omni-bin.

## Optional Electron drop-in (secondary)

Use this folder only if you want an **in-process** BrowserView adapter inside
the Electron HERMIT shell. The portable JA21 build is WPF-based, so there is
no ready HTML/WASM bundle to point `BUNDLE_ENTRY` at unless you supply one.

1. Unzip a compatible bundle into this folder, e.g.

   ```
   vendor/browser/
     app/               <- bootstrap HTML / optical surface
       index.html
       ...
     index.js           <- the adapter (from index.example.js)
   ```

2. Copy `index.example.js` to `index.js`.

3. Edit `BUNDLE_ENTRY` in `index.js` and choose **Mode A** or **Mode B**.

Restart HERMIT. The pane header will report `VB-JA21/9.8.7` when the adapter
loads.

## The contract

The pane depends on exactly four things (`src/main/browser-adapter.js` is the
authoritative reference):

| member                    | responsibility                                   |
|---------------------------|--------------------------------------------------|
| `name`                    | engine label shown in the UI                     |
| `attach(view, hooks)`     | wire the Electron `BrowserView` (or your surface) |
| `resolveUrl(input)`       | normalize user input → a loadable URL/route      |
| `navigate(url)`           | load a resolved URL                              |

`hooks.onNavigate(url)` should be called whenever the location changes so the
URL bar stays in sync.

## Notes

- The pane runs in its own session partition (`persist:hermit-browser`), isolated
  from the terminal.
- `extraResources` in `package.json` copies `vendor/browser` into the packaged
  app under `resources/browser`, so your bundle ships inside the `.exe`.