#!/usr/bin/env python3
"""
Batch-adds --reset flag to all apply_solution.py files.

Three targeted text substitutions per file:
  1. Import: add erase_device_config to eve_ng import line
  2. Parser: add --reset argument before args = parser.parse_args()
  3. Main:   insert Phase 1 erase block between "fail = 0" and "for name in DEVICES:"
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

OLD_IMPORT = (
    "from eve_ng import EveNgError, connect_node, discover_ports, require_host"
)
NEW_IMPORT = (
    "from eve_ng import EveNgError, connect_node, discover_ports, erase_device_config, require_host"
)

OLD_PARSE = "    args = parser.parse_args()"
NEW_PARSE = (
    '    parser.add_argument("--reset", action="store_true",\n'
    '                        help="Erase device configs before pushing solution (guaranteed clean slate)")\n'
    "    args = parser.parse_args()"
)

OLD_LOOP = "    fail = 0\n    for name in DEVICES:"
NEW_LOOP = (
    "    fail = 0\n"
    "\n"
    "    if args.reset:\n"
    '        print("\\nPhase 1: Resetting devices...")\n'
    "        reset_fail = 0\n"
    "        for name in DEVICES:\n"
    "            port = ports.get(name)\n"
    "            if port is None:\n"
    '                print(f"[!] {name}: not found in lab {args.lab_path} — skipping reset")\n'
    "                reset_fail += 1\n"
    "                continue\n"
    "            if not erase_device_config(host, name, port):\n"
    "                reset_fail += 1\n"
    '        print(f"[=] Phase 1 complete: {len(DEVICES) - reset_fail} reset, {reset_fail} failed.")\n'
    "        fail += reset_fail\n"
    '        print(f"\\nPhase 2: Pushing solution configs...")\n'
    "\n"
    "    for name in DEVICES:"
)

# Some files use "ok = fail = 0" with a success counter
OLD_LOOP_V2 = "    ok = fail = 0\n    for name in DEVICES:"
NEW_LOOP_V2 = (
    "    ok = fail = 0\n"
    "\n"
    "    if args.reset:\n"
    '        print("\\nPhase 1: Resetting devices...")\n'
    "        reset_fail = 0\n"
    "        for name in DEVICES:\n"
    "            port = ports.get(name)\n"
    "            if port is None:\n"
    '                print(f"[!] {name}: not found in lab {args.lab_path} — skipping reset")\n'
    "                reset_fail += 1\n"
    "                continue\n"
    "            if not erase_device_config(host, name, port):\n"
    "                reset_fail += 1\n"
    '        print(f"[=] Phase 1 complete: {len(DEVICES) - reset_fail} reset, {reset_fail} failed.")\n'
    "        fail += reset_fail\n"
    '        print(f"\\nPhase 2: Pushing solution configs...")\n'
    "\n"
    "    for name in DEVICES:"
)

files = sorted((REPO / "labs").rglob("apply_solution.py"))
print(f"Found {len(files)} apply_solution.py files.\n")

changed = 0
skipped = 0
errors = 0

for path in files:
    text = path.read_text(encoding="utf-8")
    original = text

    # Skip already-updated files
    if "erase_device_config" in text:
        print(f"[skip] {path.relative_to(REPO)} — already has erase_device_config")
        skipped += 1
        continue

    missing = []
    if OLD_IMPORT not in text:
        missing.append("import line")
    if OLD_PARSE not in text:
        missing.append("parse_args line")
    has_loop = OLD_LOOP in text or OLD_LOOP_V2 in text
    if not has_loop:
        missing.append("fail=0/for loop")

    if missing:
        print(f"[WARN] {path.relative_to(REPO)} — cannot find: {', '.join(missing)}")
        errors += 1
        continue

    text = text.replace(OLD_IMPORT, NEW_IMPORT, 1)
    text = text.replace(OLD_PARSE, NEW_PARSE, 1)
    if OLD_LOOP in text:
        text = text.replace(OLD_LOOP, NEW_LOOP, 1)
    else:
        text = text.replace(OLD_LOOP_V2, NEW_LOOP_V2, 1)
    path.write_text(text, encoding="utf-8")

    # Syntax check
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(path)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[ERROR] {path.relative_to(REPO)} — SyntaxError after transform:")
        print(result.stderr)
        # Restore original
        path.write_text(original, encoding="utf-8")
        errors += 1
        continue

    print(f"[ok]   {path.relative_to(REPO)}")
    changed += 1

print(f"\nDone: {changed} updated, {skipped} skipped (already done), {errors} errors.")
if errors:
    sys.exit(1)
