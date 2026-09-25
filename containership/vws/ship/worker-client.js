'use strict';
const crypto = require('node:crypto');
const { StringDecoder } = require('node:string_decoder');
const { vetArgv } = require('./policy');
/** One bounded request per session. Buffered results arrive as capped 4 KiB chunks. */
function createShipClient(emit, { control = false } = {}) {
  let current = null;
  const finish = (r) => {
    const p = current; if (!p) return; current = null;
    p.signal?.removeEventListener('abort', p.abort);
    for (const key of ['stdout', 'stderr']) { const tail = p.decoders[key].end(); if (tail) p[key].write(tail); }
    if (r.outcome !== 'COMPLETED') p.stderr.write(`ship: ${r.outcome}: ${r.reason || 'inspect lifecycle before retrying'}\n`);
    p.resolve(r.code);
  };
  return {
    control,
    run(argv, ctx) {
      vetArgv(argv, { control });
      if (current) return Promise.reject(new Error('ship request already pending'));
      if (ctx.signal?.aborted) return Promise.resolve(130);
      return new Promise(resolve => {
        const id = crypto.randomBytes(12).toString('hex');
        current = { id, resolve, stdout: ctx.stdout, stderr: ctx.stderr, signal: ctx.signal, bytes: 0, decoders: { stdout: new StringDecoder('utf8'), stderr: new StringDecoder('utf8') }, abort: () => emit({ t: 'ship.cancel', id }) };
        ctx.signal?.addEventListener('abort', current.abort, { once: true });
        emit({ t: 'ship.request', id, argv });
      });
    },
    handle(r) {
      if (!current || r.id !== current.id) return;
      if (r.t === 'ship.chunk') {
        const b = Buffer.from(r.data, 'base64'); current.bytes += b.length;
        if (b.length > 4096 || current.bytes > 1048576) { emit({ t: 'ship.cancel', id: current.id }); return finish({ code: 125, outcome: 'OUTPUT_LIMIT', reason: 'bridge result exceeds worker cap' }); }
        current[r.stream].write(current.decoders[r.stream].write(b));
      } else if (r.t === 'ship.result') finish(r);
    },
    close() { if (current) { emit({ t: 'ship.cancel', id: current.id }); finish({ code: 130, outcome: 'CANCELLED', reason: 'session closed' }); } }
  };
}
module.exports = { createShipClient };
