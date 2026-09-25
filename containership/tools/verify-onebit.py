#!/usr/bin/env python3
"""Verify JYRM 1BNCF source identity and run the bounded local adaptation tests."""
from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'ship'))
from unikernel import onebit_workflow as W,Refusal
try:
    print(json.dumps(W.check(root,deep='--deep' in sys.argv),indent=2),flush=True)
except (Refusal,OSError,ValueError) as e:
    print('REFUSED: '+str(e),file=sys.stderr);sys.exit(3)
patterns=['test_onebit.py','test_onebit_workflow.py']
for pattern in patterns:
    code=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-p',pattern,'-v'],cwd=root).returncode
    if code:sys.exit(code)
print('Local adaptation checks passed. These checks do not promote the ten source phase gates.',flush=True)
