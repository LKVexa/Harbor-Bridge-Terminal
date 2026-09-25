#!/usr/bin/env python3
"""Print an exact original VWS work pack and this candidate's current disposition.
No model calls, deployment, or task-completion marking are performed.
"""
from pathlib import Path
import argparse,json,sys,zipfile
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'ship'))
from unikernel import vws_workflow as W
from unikernel import Refusal
p=argparse.ArgumentParser(description=__doc__);p.add_argument('task');a=p.parse_args()
try:
 value=W.show(root,a.task);record=value['source_workpack'];phase=record['phase']
 print('# Current candidate disposition\n\n```json\n'+json.dumps(value['current_disposition'],indent=2)+'\n```\n')
 with zipfile.ZipFile(root/'vwsflow/series.zip') as z:
  for rel in ['MASTER.md','docs/EXECUTION.md','docs/ARCHITECTURE.md','docs/RESEARCH.md',f'phases/{phase}.md',record['path']]:
   print('\n---\n\n# Original source: '+rel+'\n\n'+z.read('VWS200/'+rel).decode('utf-8'))
except (Refusal,ValueError,KeyError) as e:print('REFUSED: '+str(e),file=sys.stderr);sys.exit(3)
