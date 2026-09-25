#!/usr/bin/env python3
"""Entry point: `python3 studio.py <command>` from this directory."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pa21studio.cli import main
raise SystemExit(main())
