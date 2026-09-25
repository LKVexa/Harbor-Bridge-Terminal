'use strict';

/**
 * VB-JA21 v9.8.7 — HERMIT browser adapter (TEMPLATE)
 * ===========================================================================
 * Rename this file to `index.js` in the same folder to activate it. HERMIT's
 * BrowserPane auto-detects `vendor/browser/index.js` at startup and uses the
 * adapter it exports in place of the built-in fallback.
 *
 * Two integration modes are shown below — pick the one that matches how your
 * v9.8.7 build renders:
 *
 *   A. "URL engine"  — your browser is reachable as a normal loadable entry
 *                      (an index.html / bootstrap page). HERMIT hands it URLs
 *                      and it navigates. This is the common case.
 *
 *   B. "Optical/WASM surface" — your build paints its own surface and handles
 *                      navigation over its own channel. You load your bootstrap
 *                      once in `attach`, then forward URLs into it via
 *                      postMessage / a preload bridge of your own.
 *
 * Contract expected by BrowserPane (see src/main/browser-adapter.js):
 *   createAdapter() -> { name, attach(view, hooks), resolveUrl(input), navigate(url) }
 */

const path = require('node:path');
const { pathToFileURL } = require('node:url');

// ── Point this at your extracted v9.8.7 bundle ────────────────────────────
// If you unzip VB-JA21-VEC1-Portable-Optical-Desktop-9.8.7 into this folder,
// set BUNDLE_ENTRY to its bootstrap HTML (relative to this file).
const BUNDLE_ENTRY = path.join(__dirname, 'app', 'index.html'); // <-- edit me
const SEARCH = 'https://duckduckgo.com/?q=';

function normalize(input) {
  const s = String(input || '').trim();
  if (!s) return 'about:blank';
  // Pass through VB-JA21 internal routes and any explicit scheme.
  if (/^(vbja21|vec1|optical):/i.test(s)) return s;
  if (/^[a-z][a-z0-9+.-]*:\/\//i.test(s)) return s;
  if (/^(about|data|blob|file):/i.test(s)) return s;
  if (/^[^\s]+\.[^\s]+$/.test(s) && !s.includes(' ')) return 'https://' + s;
  if (/^localhost([:/]|$)/.test(s)) return 'http://' + s;
  return SEARCH + encodeURIComponent(s);
}

function createAdapter() {
  let view = null;
  let hooks = { onNavigate() {} };

  return {
    name: 'VB-JA21/9.8.7',

    attach(browserView, h) {
      view = browserView;
      hooks = h || hooks;
      const wc = view.webContents;

      // ── MODE B bootstrap (optical/WASM): load your app shell once. ──────
      // Comment this out if you are using MODE A (plain URL navigation).
      try {
        const fs = require('node:fs');
        if (fs.existsSync(BUNDLE_ENTRY)) {
          wc.loadURL(pathToFileURL(BUNDLE_ENTRY).toString());
        }
      } catch (_) { /* fall back to URL navigation */ }

      wc.setWindowOpenHandler(({ url }) => { wc.loadURL(normalize(url)); return { action: 'deny' }; });
      wc.on('did-navigate', (_e, url) => hooks.onNavigate(url));
      wc.on('did-navigate-in-page', (_e, url) => hooks.onNavigate(url));
    },

    resolveUrl: normalize,

    navigate(url) {
      if (!view) return;
      // MODE A: navigate the view directly.
      view.webContents.loadURL(url);

      // MODE B alternative: forward the target into your already-loaded shell
      // instead of loadURL, e.g.
      //   view.webContents.send('vbja21:navigate', url);
      // and have your bundle's preload handle it.
    }
  };
}

module.exports = { createAdapter };
