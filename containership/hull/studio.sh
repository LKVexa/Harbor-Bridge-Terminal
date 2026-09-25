#!/bin/sh
HERE=$(cd "$(dirname "$0")" && pwd)
exec python3 "$HERE/studio.py" "$@"
