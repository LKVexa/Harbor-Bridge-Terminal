"""Durable local identities, monotonic fencing generations and lifecycle events.

SQLite commits are separate from managed-file snapshots. The command lock plus
recovery journal reconciles them. This is NOT a distributed lock or tenant ACL.
Only trusted cooperating callers may use this store; it does not fence native
code that bypasses the ship or prove that a guest became ready.
"""
from __future__ import annotations
import contextlib
import datetime as dt
import sqlite3
import uuid
from pathlib import Path
from . import Refusal
from . import strictjson as J
from .safety import contained_path, reject_link, validate_name

STATES = {'admitted','staged','built','booting','ready','running','draining','stopped','failed','quarantined'}
TRANSITIONS = {
    'admitted': {'staged','failed','quarantined'},
    'staged': {'built','stopped','failed','quarantined'},
    'built': {'booting','running','stopped','staged','failed','quarantined'},
    'booting': {'ready','failed','quarantined','stopped'},
    'ready': {'running','draining','failed','stopped','quarantined'},
    'running': {'draining','stopped','failed','quarantined'},
    'draining': {'stopped','failed','quarantined'},
    'stopped': {'staged','built','booting','running','failed','quarantined'},
    'failed': {'staged','stopped','quarantined'},
    'quarantined': {'staged','stopped'},
}
MAX_EVENTS = 100000
MAX_WORKLOADS = 10000

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()

def generation(value):
    if type(value) is not int or not 1 <= value < 2**63:
        raise Refusal('invalid generation')
    return value

class ControlStore:
    def __init__(self, root):
        self.root = Path(root).absolute()
        self.path = Path(contained_path(str(self.root), '_runs/control/state.sqlite'))
    @contextlib.contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for suffix in ('','-journal','-wal','-shm'): reject_link(str(self.path)+suffix)
        db = sqlite3.connect(str(self.path), timeout=2.0, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute('PRAGMA foreign_keys=ON'); db.execute('PRAGMA synchronous=FULL')
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0,1): raise Refusal('unsupported control database version', {'version': version})
            if version == 0:
                if db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
                    raise Refusal('unversioned nonempty database refused')
                db.executescript('''BEGIN IMMEDIATE;
                CREATE TABLE workloads(name TEXT PRIMARY KEY, workload_id TEXT UNIQUE NOT NULL,
                  generation INTEGER NOT NULL CHECK(generation>0), desired TEXT NOT NULL,
                  observed TEXT NOT NULL, active_operation TEXT, updated TEXT NOT NULL);
                CREATE TABLE events(seq INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                  generation INTEGER NOT NULL, event TEXT NOT NULL, detail TEXT NOT NULL, utc TEXT NOT NULL);
                CREATE TABLE operations(id TEXT PRIMARY KEY, name TEXT NOT NULL,
                  generation INTEGER NOT NULL, action TEXT NOT NULL, status TEXT NOT NULL, utc TEXT NOT NULL);
                PRAGMA user_version=1; COMMIT;''')
            yield db
        finally: db.close()
    @contextlib.contextmanager
    def tx(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            try: yield db; db.execute('COMMIT')
            except BaseException:
                if db.in_transaction: db.execute('ROLLBACK')
                raise
    def _event(self, db, name, gen, event, detail):
        if db.execute('SELECT count(*) FROM events').fetchone()[0] >= MAX_EVENTS:
            raise Refusal('lifecycle event budget exhausted; retain/export evidence before maintenance')
        text = J.canonical_bytes(detail).decode('utf-8')
        if len(text.encode('utf-8')) > 8192: raise Refusal('lifecycle event exceeds byte budget')
        db.execute('INSERT INTO events(name,generation,event,detail,utc) VALUES(?,?,?,?,?)',
                   (name,gen,event,text,now()))
    def _ensure(self, db, name):
        validate_name(name)
        row = db.execute('SELECT * FROM workloads WHERE name=?', (name,)).fetchone()
        if row is None:
            if db.execute('SELECT count(*) FROM workloads').fetchone()[0] >= MAX_WORKLOADS:
                raise Refusal('workload identity budget exhausted')
            exists = Path(contained_path(str(self.root), 'berths/'+name+'/BERTH.json')).is_file()
            observed = 'staged' if exists else 'admitted'
            db.execute('INSERT INTO workloads VALUES(?,?,?,?,?,?,?)',
                       (name,str(uuid.uuid4()),1,'stopped',observed,None,now()))
            self._event(db,name,1,'identity_created', {'observation': observed,
                        'basis': 'BERTH.json presence only; no readiness or correctness claim'})
            row = db.execute('SELECT * FROM workloads WHERE name=?',(name,)).fetchone()
        return dict(row)
    def inspect(self, name=None, limit=100):
        if type(limit) is not int or not 1 <= limit <= 1000: raise Refusal('invalid event limit')
        if name: validate_name(name)
        if not self.path.exists():
            return {'schema':'UC/LIFECYCLE/1','workloads':[],'events':[], 'note':'No tracked operation yet.'}
        with self.connect() as db:
            check = db.execute('PRAGMA quick_check').fetchone()[0]
            if check != 'ok': raise Refusal('control database integrity failure')
            rows = db.execute('SELECT * FROM workloads WHERE name=?' if name else 'SELECT * FROM workloads ORDER BY name',
                              (name,) if name else ()).fetchall()
            events = db.execute('SELECT * FROM events WHERE name=? ORDER BY seq DESC LIMIT ?' if name else
                                'SELECT * FROM events ORDER BY seq DESC LIMIT ?', (name,limit) if name else (limit,)).fetchall()
            return {'schema':'UC/LIFECYCLE/1','workloads':[dict(r) for r in rows],
                    'events':[dict(r) | {'detail':J.loads(r['detail'])} for r in events],
                    'note':'Generation fences cooperating management operations, not arbitrary native processes.'}
    def begin(self, name, action, expected=None, invalidate=False):
        if not isinstance(action,str) or not 1 <= len(action) <= 64: raise Refusal('invalid operation name')
        if expected is not None: generation(expected)
        with self.tx() as db:
            row = self._ensure(db,name)
            if expected is not None and expected != row['generation']:
                raise Refusal('stale generation refused', {'expected':expected,'actual':row['generation']})
            if row['active_operation']: raise Refusal('unfinished operation requires recovery', {'operation':row['active_operation']})
            gen = generation(row['generation'] + (1 if invalidate else 0))
            op = str(uuid.uuid4())
            db.execute('UPDATE workloads SET generation=?, active_operation=?, updated=? WHERE name=?',(gen,op,now(),name))
            db.execute('INSERT INTO operations VALUES(?,?,?,?,?,?)',(op,name,gen,action,'EXECUTING',now()))
            self._event(db,name,gen,'operation_started',{'operation':op,'action':action,'observed':row['observed']})
            return {'name':name,'workload_id':row['workload_id'],'generation':gen,'operation':op}
    def finish(self, token, success, *, observed=None):
        if type(success) is not bool: raise Refusal('operation outcome must be boolean')
        with self.tx() as db:
            row = self._ensure(db,token['name'])
            if row['workload_id'] != token['workload_id'] or row['generation'] != token['generation'] or row['active_operation'] != token['operation']:
                raise Refusal('stale operation result refused')
            state = observed or (row['observed'] if success else 'failed')
            if not isinstance(state,str) or state not in STATES or state in {'ready','booting','running'}:
                raise Refusal('command completion cannot assert guest boot, readiness or running state')
            if state != row['observed'] and state not in TRANSITIONS[row['observed']]:
                raise Refusal('operation completion has an illegal lifecycle predecessor')
            status = 'SUCCEEDED' if success else 'FAILED'
            db.execute('UPDATE workloads SET observed=?,active_operation=NULL,updated=? WHERE name=?',(state,now(),token['name']))
            db.execute('UPDATE operations SET status=? WHERE id=?',(status,token['operation']))
            self._event(db,token['name'],token['generation'],'operation_finished',{'operation':token['operation'],'status':status,'observed':state})
    def transition(self, name, expected, state, *, reason, evidence):
        generation(expected)
        if not isinstance(state,str) or state not in STATES or not reason or not evidence: raise Refusal('state transition requires known state, reason and evidence')
        if not isinstance(reason,str) or not isinstance(evidence,str): raise Refusal('transition references must be strings')
        with self.tx() as db:
            row=self._ensure(db,name)
            if row['generation'] != expected: raise Refusal('stale transition refused')
            if state not in TRANSITIONS[row['observed']]: raise Refusal('illegal lifecycle predecessor',{'from':row['observed'],'to':state})
            db.execute('UPDATE workloads SET observed=?,updated=? WHERE name=?',(state,now(),name))
            self._event(db,name,expected,'state_transition',{'from':row['observed'],'to':state,'reason':reason,'evidence':evidence})
    def recover(self, name, transaction):
        # Recovery invalidates every older token, even if old bytes were restored.
        with self.tx() as db:
            row=self._ensure(db,name); gen=generation(row['generation']+1)
            if row['active_operation']:
                db.execute("UPDATE operations SET status='RECOVERED' WHERE id=?",(row['active_operation'],))
            state='staged' if Path(contained_path(str(self.root),'berths/'+name+'/BERTH.json')).is_file() else 'stopped'
            db.execute('UPDATE workloads SET generation=?,observed=?,active_operation=NULL,updated=? WHERE name=?',(gen,state,now(),name))
            self._event(db,name,gen,'managed_files_recovered',{'transaction':transaction,'observed':state})
            return {'name':name,'generation':gen,'observed':state}
