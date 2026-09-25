#!/usr/bin/env python3
"""Verify preserved workflow identity, then run TIFF/GIF/kernel regression cases."""
from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'ship'))
from unikernel import tiff_workflow as W,Refusal
try:print(json.dumps(W.check(root,deep='--deep' in sys.argv),indent=2),flush=True)
except (Refusal,OSError,ValueError) as e:print('REFUSED: '+str(e),file=sys.stderr);sys.exit(3)
code=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-p','test_pixel_fabric.py','-v'],cwd=root).returncode
print('These checks do not promote the nine full-series phase gates.',flush=True)
sys.exit(code)
