#!/bin/sh
# Opens the Language Studio install window in the default browser.
# Nothing is installed until the button in that window is pressed.
HERE=$(cd "$(dirname "$0")" && pwd)
exec python3 "$HERE/studio.py" ui "$@"
