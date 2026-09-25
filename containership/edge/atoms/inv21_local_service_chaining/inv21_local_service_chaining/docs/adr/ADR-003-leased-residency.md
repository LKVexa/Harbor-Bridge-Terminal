# ADR-003: Residency as a leased cache over the INV-10 feed
Status: PROPOSED · Date: 2026-09-23
Decision: placements carry lease/epoch/source; expired, unverified or unhealthy placements are never served locally; restarts restore unverified and reconcile. A stale entry falls back to the network path instead of serving stale code.
