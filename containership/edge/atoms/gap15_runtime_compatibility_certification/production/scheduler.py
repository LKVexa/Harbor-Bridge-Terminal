"""Automatic recertification scheduler (component 22).

A durable-by-design idempotent work queue: every job key is
``scope|trigger|trigger_revision`` so repeated scans enqueue nothing new
(MC-22-02). Workers take *leases* with a fencing token; a result from a
stale lease is rejected (MC-22-05). Priority = expiry urgency, criticality,
fleet population, security severity, coverage gap (MC-22-03); per-lab
concurrency quotas bound storms (MC-22-04). Nothing the scheduler does can
produce a verdict — it only records that a retest is queued/running/failed;
certification still requires ingested evidence (MC-22-06).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Optional

TRIGGERS = {"ttl-expiry", "lifecycle-deadline", "input-change", "policy-revision", "trust-change",
            "revocation-advisory", "coverage-gap", "negative-aged"}


class SchedulerError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


@dataclass
class Job:
    job_key: str
    scope: str
    trigger: str
    trigger_revision: int
    lab: str
    priority: float
    state: str = "queued"  # queued | leased | done | failed | dead | cancelled | superseded
    attempts: int = 0
    lease_owner: Optional[str] = None
    lease_until: int = 0
    fence: int = 0
    last_error: Optional[str] = None
    created_at: int = 0


def priority(*, seconds_to_expiry: int, criticality: int, population: int, severity: int, coverage_gap: bool) -> float:
    urgency = 1000.0 / max(seconds_to_expiry, 1)
    return round(urgency * 10 + criticality * 5 + min(population, 10000) / 100 + severity * 20 + (15 if coverage_gap else 0), 4)


class RecertScheduler:
    def __init__(self, *, lab_quota: dict, max_attempts: int = 3, lease_s: int = 600, paused: bool = False) -> None:
        self.jobs: dict = {}
        self.lab_quota = dict(lab_quota)
        self.max_attempts = max_attempts
        self.lease_s = lease_s
        self.paused = paused
        self._fence = 0
        self._lock = threading.Lock()
        self.audit: list = []

    def enqueue(self, scope: str, trigger: str, trigger_revision: int, *, lab: str, prio: float, now: int) -> tuple:
        if trigger not in TRIGGERS:
            raise SchedulerError("E_SCHED_TRIGGER", trigger)
        key = f"{scope}|{trigger}|{trigger_revision}"
        with self._lock:
            if key in self.jobs:
                return self.jobs[key], False
            # a newer revision of the same scope/trigger supersedes queued older work (MC-22-07)
            for j in self.jobs.values():
                if j.scope == scope and j.trigger == trigger and j.trigger_revision < trigger_revision and j.state == "queued":
                    j.state = "superseded"
            job = self.jobs[key] = Job(key, scope, trigger, trigger_revision, lab, prio, created_at=now)
            return job, True

    def lease(self, worker: str, now: int) -> Optional[Job]:
        with self._lock:
            if self.paused:
                return None
            for j in self.jobs.values():  # expire dead leases
                if j.state == "leased" and j.lease_until <= now:
                    j.state, j.lease_owner = "queued", None
            running = {}
            for j in self.jobs.values():
                if j.state == "leased":
                    running[j.lab] = running.get(j.lab, 0) + 1
            ready = sorted((j for j in self.jobs.values() if j.state == "queued"
                            and running.get(j.lab, 0) < self.lab_quota.get(j.lab, 0)),
                           key=lambda j: (-j.priority, j.created_at, j.job_key))
            if not ready:
                return None
            job = ready[0]
            self._fence += 1
            job.state, job.lease_owner, job.lease_until, job.fence = "leased", worker, now + self.lease_s, self._fence
            job.attempts += 1
            return job

    def complete(self, job_key: str, worker: str, fence: int, *, ok: bool, error: Optional[str] = None) -> Job:
        with self._lock:
            job = self.jobs[job_key]
            if job.state != "leased" or job.lease_owner != worker or job.fence != fence:
                raise SchedulerError("E_SCHED_STALE_LEASE", "lease was lost or fenced off")
            if ok:
                job.state = "done"  # 'done' means the test RAN; the verdict comes only from ingested evidence
            else:
                job.last_error = error
                job.state = "dead" if job.attempts >= self.max_attempts else "queued"
            job.lease_owner = None
            return job

    def cancel(self, job_key: str, *, actor: str, reason: str) -> None:
        with self._lock:
            self.jobs[job_key].state = "cancelled"
            self.audit.append({"action": "cancel", "job": job_key, "actor": actor, "reason": reason})

    def control(self, action: str, *, actor: str) -> None:
        if action not in ("pause", "resume", "drain"):
            raise SchedulerError("E_SCHED_CONTROL", action)
        with self._lock:
            self.paused = action in ("pause", "drain")
            self.audit.append({"action": action, "actor": actor})

    def metrics(self, now: int) -> dict:
        queued = [j for j in self.jobs.values() if j.state == "queued"]
        return {"depth": len(queued), "oldest_age_s": max((now - j.created_at for j in queued), default=0),
                "leased": sum(1 for j in self.jobs.values() if j.state == "leased"),
                "dead": sum(1 for j in self.jobs.values() if j.state == "dead"),
                "done": sum(1 for j in self.jobs.values() if j.state == "done")}
