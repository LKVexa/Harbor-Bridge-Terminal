'use strict';
const HELP = `Unikernel Containership — authenticated local control surface
  ship status                         ship and engine status
  ship berths                         registered workloads
  ship capabilities                   actual isolation boundaries
  ship doctor                         source/runtime preflight
  ship lifecycle [BERTH]              generation and operation history
  ship fabric status BERTH            TIFF fabric state
  ship recover list                   pending managed-file transactions
  ship workflow status                original 96,000-task application
  ship vws-workflow status             VWS 6,360-work-pack reapplication
  ship tiff-workflow status            TIFF 325,000-task disposition
  ship onebit-workflow status          JYRM 1BNCF 275,000-workflow disposition
  ship master-workflow status          UC 375,000-record master-series disposition
  ship platform status                 bounded local platform-service capabilities
  ship onebit status                   local 1-bit communication capabilities
  ship onebit tiff-read BERTH SLOT TILE     inspect a 1-bit packet carried in a TIFF tile
  ship pixels status                  local TIFF/GIF/kernel capabilities
  ship pixels inspect BERTH SLOT      file digest and logical pixel state
  ship pixels cell BERTH SLOT TILE WORD    checked u64 pixel-cell read

Explicit control mode only (TERMINAL.cmd --control):
  ship run BERTH --sealed --generation N
  ship run BERTH --ticks 1 --generation N   (1..10 ticks)
  ship verify BERTH                     one berth quick gate battery

Read generation from lifecycle; never automatically retry an interrupted command.
LOAD, UNLOAD, BUILD, SEAL, pixel edits/checkpoints/exports and recovery writes remain local CLI operations.
`;
module.exports = [{ name: 'ship', summary: 'inspect and operate the bound Unikernel Containership', usage: 'ship <help|status|berths|capabilities|doctor|lifecycle|fabric|recover|workflow|vws-workflow|tiff-workflow|onebit-workflow|master-workflow|platform|pixels|onebit|run|verify>',
  async run(ctx) {
    const bridge = ctx.host && ctx.host.shipBridge;
    if (!bridge) { ctx.stderr.write('ship: no operator-bound containership bridge\n'); return 3; }
    if (!ctx.argv.length || ctx.argv[0] === 'help') { ctx.stdout.write(HELP + `Mode: ${bridge.control ? 'CONTROL (allowlisted)' : 'READ ONLY'}\n`); return 0; }
    try { return await bridge.run(ctx.argv, ctx); } catch (e) { ctx.stderr.write(`ship: ${e.message}\n`); return 3; }
  }, complete(ctx, partial) { return ['help','status','berths','capabilities','doctor','lifecycle','fabric','recover','workflow','vws-workflow','tiff-workflow','onebit-workflow','master-workflow','platform','pixels','onebit','run','verify'].filter(x => x.startsWith(partial)); }
}];
