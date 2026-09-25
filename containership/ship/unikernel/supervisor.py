"""Bounded local subprocess execution for the ship's native build commands.

POSIX commands get a new session and timeout/output-limit process-group cleanup.
Windows uses taskkill /T when available. Neither path is a hypervisor, security
sandbox, aggregate quota, or parent-crash orphan guarantee. Imported runtime
adapters are not automatically intercepted by this helper.
"""
from __future__ import annotations
import math
import os
import signal
import subprocess
import threading
import time
from . import Refusal

MAX_OUTPUT=1024*1024
MAX_TIMEOUT=7200

def run(argv,*,cwd,timeout=3600,max_output=MAX_OUTPUT,env=None):
    if not isinstance(argv,(list,tuple)) or not argv or len(argv)>256 or any(not isinstance(x,str) or '\0' in x or len(x)>32768 for x in argv):
        raise Refusal('invalid subprocess argument vector')
    if isinstance(timeout,bool) or not isinstance(timeout,(int,float)) or not math.isfinite(timeout) or not 0<timeout<=MAX_TIMEOUT:
        raise Refusal('subprocess timeout out of range')
    if type(max_output) is not int or not 1024<=max_output<=8*1024*1024:raise Refusal('subprocess output budget out of range')
    t0=time.monotonic();overflow=threading.Event();tails=[bytearray(),bytearray()];counts=[0,0]
    flags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0
    p=subprocess.Popen(list(argv),cwd=cwd,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                       bufsize=0,start_new_session=os.name!='nt',creationflags=flags,env=env)
    def drain(stream,index):
        try:
            while True:
                chunk=os.read(stream.fileno(),65536)
                if not chunk:break
                counts[index]+=len(chunk);tails[index].extend(chunk)
                if len(tails[index])>max_output:del tails[index][:-max_output]
                if sum(counts)>max_output:overflow.set()
        except (OSError,ValueError):pass
    threads=[threading.Thread(target=drain,args=(p.stdout,0),daemon=True),threading.Thread(target=drain,args=(p.stderr,1),daemon=True)]
    for t in threads:t.start()
    cleanup='posix-process-group' if os.name!='nt' else 'windows-taskkill-tree-best-effort'
    def kill():
        if os.name!='nt':
            try:os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        else:
            try:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
            except (OSError,subprocess.TimeoutExpired):p.kill()
    timed_out=False
    try:
        while p.poll() is None:
            timed_out=time.monotonic()-t0>=timeout
            if timed_out or overflow.is_set():kill();break
            time.sleep(0.01)
        p.wait(timeout=5)
        # Reap surviving group members even if the direct child exited first.
        if os.name!='nt':kill()
        for thread in threads:thread.join(timeout=2)
    except BaseException:
        kill();p.wait(timeout=5);raise
    finally:
        p.stdout.close();p.stderr.close()
    limited=overflow.is_set()
    return {'argv':list(argv),'returncode':p.returncode if not (timed_out or limited) else 124 if timed_out else 125,
            'seconds':round(time.monotonic()-t0,3),'stdout':bytes(tails[0]).decode('utf-8','replace'),
            'stderr':bytes(tails[1]).decode('utf-8','replace'),'output_bytes':sum(counts),
            'output_limited':limited,'timed_out':timed_out,'cleanup':cleanup,
            'isolation_class':'host-process'}
