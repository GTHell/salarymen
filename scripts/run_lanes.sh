#!/usr/bin/env bash
# run_lanes.sh — detached lane pipeline: intake -> builder ticks until board clear
PROJECT="$1"
SAL="/home/gthell/dev/salarymen"
PY=python3
cd "$PROJECT" || exit 1

export SALARYMAN_PI_PROVIDER=ox
export SALARYMAN_PI_MODEL=x-preview-f-free

$PY - <<'EOF'
import sys
sys.path.insert(0, "/home/gthell/dev/salarymen")
from salaryman.lanes.intake import process_inbox
from salaryman.drivers import PiDriver
import salaryman.lanes.intake as intake_mod
intake_mod.get_driver = lambda n: PiDriver(provider="ox", model="x-preview-f-free")
created = process_inbox("BOARD.md", ".")
print(f"intake: {len(created)} cards", flush=True)
EOF

MAX=12
i=0
while [ $i -lt $MAX ]; do
  OUT=$($PY - <<'EOF'
import sys
sys.path.insert(0, "/home/gthell/dev/salarymen")
from salaryman.lanes.builder import builder_tick
from salaryman.drivers import PiDriver
import salaryman.lanes.builder as builder_mod
builder_mod.get_driver = lambda n: PiDriver(provider="ox", model="x-preview-f-free")
res = builder_tick(".")
print(res.get("outcome") or res)
EOF
) || true
  echo "builder tick $((i+1)): $OUT" >&2
  case "$OUT" in
    *done*) : ;;
    *) break ;;
  esac
  i=$((i+1))
done

# critic: attach evidence to any unevidenced DONE (probe only; screenshots by workers)
$PY - <<'EOF'
import sys
sys.path.insert(0, "/home/gthell/dev/salarymen")
from salaryman.lanes.critic import critic_tick
print("critic:", critic_tick(".", live_urls=["http://localhost:3457/"]), flush=True)
EOF

# docs backfill
$PY -c "
import sys; sys.path.insert(0, '/home/gthell/dev/salarymen')
from salaryman.features import backfill
from pathlib import Path
w = backfill(Path('BOARD.md'), Path('docs/features'))
print('docs:', len(w))"

# auditor
$PY - <<'EOF'
import sys
sys.path.insert(0, "/home/gthell/dev/salarymen")
from salaryman.lanes.auditor import auditor_tick
print("audit:", auditor_tick("."), flush=True)
EOF
