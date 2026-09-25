# Browser pane integration — VB-JA21 v9.8.7

HERMIT's browser pane is engine-agnostic. It ships with a working fallback
(plain Chromium `BrowserView`) so the app runs immediately, and it auto-detects
a vendored browser here.

## Drop-in steps

1. Unzip your build into this folder, e.g.

   ```
   vendor/browser/
     app/               <- your VB-JA21-VEC1-Portable-Optical-Desktop-9.8.7 bundle
       index.html
       ...
     index.js           <- the adapter (from index.example.js)
   ```

2. Copy `index.example.js` to `index.js`.

3. Edit `BUNDLE_ENTRY` in `index.js` to point at your bundle's bootstrap page,
   and choose **Mode A** (URL navigation) or **Mode B** (optical/WASM surface)
   per the comments in that file.

That's it — restart HERMIT. The pane header will report `VB-JA21/9.8.7` and the
terminal's `browser info` command will show the active engine.

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
