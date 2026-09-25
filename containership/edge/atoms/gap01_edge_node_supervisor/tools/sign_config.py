"""Sign a config document: python tools/sign_config.py config.json keyfile > signed.json"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from gap01_edge_node_supervisor.config import SecretBoundary, SupervisorConfig, sign  # noqa: E402

doc = json.loads(pathlib.Path(sys.argv[1]).read_text())
body = doc.get("config", doc)
SupervisorConfig(**body)  # validate before signing
key = SecretBoundary.from_file(sys.argv[2]).reveal()
print(json.dumps({"config": body, "signature": sign(body, key)}, indent=2, sort_keys=True))
