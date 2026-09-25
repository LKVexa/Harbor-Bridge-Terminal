# Runbook — emergency freeze / quarantine
* **Freeze all launches** (deletes still proceed): operator API `Switchboard.freeze(reason)`; audited as `switch.freeze`. Workloads show `INV67_FROZEN` and requeue.
* **Quarantine a namespace or object:** `quarantine("ns:<ns>" | "<ns>/<name>", reason)` — terminal refusal until released.
* **Full disable:** scale Deployment to 0. Running workloads continue in the runtime; deletions will wait (finalizers) until the controller returns.
* Unfreeze only with incident commander approval; record in the incident timeline.
