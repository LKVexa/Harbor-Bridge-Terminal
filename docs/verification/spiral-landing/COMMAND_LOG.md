# SPIRAL / landing verification command log (America/Los_Angeles)

Generated: 2026-09-25 13:39:08 PT

## Pre-existing listeners
- 127.0.0.1:10000 node (Post Kubernetes World hermit-ramws) — /health 200
- 127.0.0.1:10001 Harbor-Bridge-Terminal gateway/server.js — /health 200, /config.json fabric:true
- 127.0.0.1:10002 Harbor-Bridge-Terminal gateway/server.js — /health 200

## Controlled start
```
cd bridge-terminal
node tools/start-local.js --no-browser --port 10003
```
Log excerpt: HERMIT -> http://127.0.0.1:10003/ ; fabric ON; qnodes ON; browser skipped; gateway.listening host=127.0.0.1 port=10003

## Probes (measured)
See port10003-http-probes.json, port10003-ws-ticket.json, port10003-ws-upgrade.json, fleet-board-locator.json, SPIRAL_LANDING_VERIFICATION_SUMMARY.json

## Cleanup
Stopped start-local PID 43560 and gateway PID 30460. Left 10000/10001/10002 running.
