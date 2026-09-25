#!/usr/bin/env bash
# Cross-host test using two Linux network namespaces joined by a veth pair
# (requires root). Server in ns "a" (10.61.0.1), client in ns "b" (10.61.0.2).
set -euo pipefail
cd "$(dirname "$0")/.."
ip netns add inv61a; ip netns add inv61b
trap 'ip netns del inv61a; ip netns del inv61b' EXIT
ip link add va type veth peer name vb
ip link set va netns inv61a; ip link set vb netns inv61b
ip -n inv61a addr add 10.61.0.1/24 dev va; ip -n inv61a link set va up; ip -n inv61a link set lo up
ip -n inv61b addr add 10.61.0.2/24 dev vb; ip -n inv61b link set vb up; ip -n inv61b link set lo up
W=$(mktemp -d)
python3 - "$W" <<'PY'
import json, secrets, sys, pathlib
w = pathlib.Path(sys.argv[1]); s = secrets.token_bytes(32)
(w / "keys.json").write_text(json.dumps([{"key_id": "client-a-k1", "principal": "client-a", "secret_hex": s.hex()}]))
(w / "audit.key").write_bytes(secrets.token_bytes(32))
PY
export PYTHONPATH="$(cd .. && pwd)"
ip netns exec inv61a python3 -m "$(basename "$PWD")".demo_node --keyring "$W/keys.json" --audit-key-file "$W/audit.key" \
   --workdir "$W/run" --host 10.61.0.1 --port 7461 & SRV=$!
sleep 1
ip netns exec inv61b python3 - "$W" "$(basename "$PWD")" <<'PY'
import json, sys, pathlib, importlib
w, pkg = pathlib.Path(sys.argv[1]), sys.argv[2]
sec = importlib.import_module(pkg + ".security"); tr = importlib.import_module(pkg + ".transport")
wm = importlib.import_module(pkg + ".wit_model")
row = json.loads((w / "keys.json").read_text())[0]
k = sec.Key(row["key_id"], row["principal"], bytes.fromhex(row["secret_hex"]))
kv = wm.parse((pathlib.Path(pkg) / "wit" / "kv.wit").read_text() if pathlib.Path(pkg).exists() else open("wit/kv.wit").read())[0]
c = tr.RpcClient("10.61.0.1", 7461, k)
assert c.call(kv, "echo", [[1, 2, 3]])["value"] == [1, 2, 3]
print("cross-namespace call OK")
PY
kill -TERM $SRV; wait $SRV
