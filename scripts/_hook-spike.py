#!/usr/bin/env python3
import json, sys, os
from pathlib import Path

payload = json.load(sys.stdin)

spike_out = Path("logs/_spike-payload.json")
spike_out.parent.mkdir(exist_ok=True)
spike_out.write_text(json.dumps(payload, indent=2))

# Also dump env vars
env_out = Path("logs/_spike-env.txt")
env_out.write_text("\n".join(f"{k}={v}" for k, v in sorted(os.environ.items())))
