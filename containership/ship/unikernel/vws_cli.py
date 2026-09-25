"""Launch the integrated local terminal without retaining the ship mutation lock."""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess
import sys
from . import Refusal
from . import engines as E

def configure(sp):
    p=sp.add_parser('terminal',help='authenticated loopback HERMIT/RAMWS terminal (read-only by default)')
    p.add_argument('--control',action='store_true');p.add_argument('--new-token',action='store_true')
    p.add_argument('--no-browser',action='store_true');p.add_argument('--check',action='store_true')
    p.add_argument('--port',type=int,default=10000);p.set_defaults(fn=launch)
    p=sp.add_parser('vws-workflow',help='inspect and verify the complete 6,360-pack VWS reapplication')
    p.add_argument('verb',choices=['status','check','show']);p.add_argument('task',nargs='?');p.set_defaults(fn=workflow)

def launch(a):
    if not 1<=a.port<=65535:raise Refusal('terminal port must be 1..65535')
    root=Path(E.ship_root());node=os.environ.get('NODE') or shutil.which('node')
    if not node:raise Refusal('Node.js 22+ is required. Nothing was installed.')
    probe=subprocess.run([node,'-p','process.versions.node'],capture_output=True,text=True,timeout=10)
    try:major=int(probe.stdout.strip().split('.')[0])
    except (ValueError,IndexError):raise Refusal('configured Node executable failed its version probe')
    if probe.returncode or major<22:raise Refusal('Node.js 22+ is required by the integrated terminal launcher')
    argv=[node,str(root/'vws/tools/start-ship.js'),'--port',str(a.port)]
    for name in ('control','new_token','no_browser','check'):
        if getattr(a,name):argv.append('--'+name.replace('_','-'))
    env=dict(os.environ,UC_PYTHON=sys.executable)
    # Do not hold SAFE.ship_lock while the service runs: its own UC requests take that lock.
    p=subprocess.Popen(argv,cwd=root,env=env)
    try:return p.wait()
    except KeyboardInterrupt:
        try:return p.wait(timeout=25)
        except subprocess.TimeoutExpired:p.terminate();return p.wait(timeout=5)

def workflow(a):
    from . import vws_workflow as W
    from .cli import _emit
    if a.verb=='status':return _emit(W.status(E.ship_root()))
    if a.verb=='check':return _emit(W.check(E.ship_root()))
    if not a.task:raise Refusal('VWS task ID is required')
    return _emit(W.show(E.ship_root(),a.task))
