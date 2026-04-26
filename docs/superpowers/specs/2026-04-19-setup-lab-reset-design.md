# Design: setup_lab.py Config Reset (`--reset` Flag)

## Problem

When a student completes a lab and saves it, re-running `setup_lab.py` overlays
new configs on top of their existing running-config. Orphaned configs (old routing
protocols, ACLs, etc.) can persist and interfere with the fresh lab experience.

## Goal

Add a `--reset` flag to every lab's `setup_lab.py` that erases existing device
configs before pushing initial configs — giving students a guaranteed clean slate
without modifying the EVE-NG topology.

## Scope

- All `setup_lab.py` scripts under `labs/*/lab-*/`
- Affects Cisco IOS router/switch nodes only (VPCs are unchanged)

## Design

### Flag

```
python setup_lab.py --host <ip> --reset
```

- Optional flag; default behavior (no flag) is unchanged.
- When present, runs a two-phase operation.

### Two-Phase Operation

**Phase 1 — Reset all devices:**

- For each device in the lab's `DEVICES` list:
  - Connect to the device via telnet (same `connect_node()` helper)
  - Send `write erase` (clears startup-config in memory; running-config is left
    intact until push phase overwrites it)
  - Log success or failure per device
- Print a phase summary: `N reset, M failed`
- Reset failures are non-fatal — all devices are attempted regardless

**Phase 2 — Push initial configs (existing behavior):**

- Proceeds exactly as today: loop through DEVICES, call `push_device()`
- Config push overwrites the running-config, which combined with the erased
  startup-config gives students a clean state after the lab

### Why No Reload?

`write erase` clears startup-config. The initial-config push (Phase 2) immediately
overwrites the running-config. A reload is unnecessary because the push replaces all
student-added config. Reload would add 1-2 min of wait time per device with no
benefit for this use case.

### New Function: `reset_device()`

```python
def reset_device(host: str, name: str, port: int) -> bool:
    # Connect, send "write erase", disconnect
    # Returns True on success, False on failure
```

Mirrors the signature of `push_device()` for consistency.

### Modified `main()` Flow

```
parse args
discover_ports()
if --reset:
    Phase 1: for each device → reset_device()
    print Phase 1 summary
Phase 2: for each device → push_device()
print Phase 2 summary
exit(fail_count > 0)
```

### Output Format

```
============================================================
Lab Setup: OSPF Lab 00 -- Single-Area OSPFv2 Fundamentals
============================================================

Phase 1: Resetting devices...
[*] R1: erasing config...
[+] R1: config erased.
[*] R2: erasing config...
[!] R2: reset failed -- connection refused
...
[=] Phase 1 complete: 4 reset, 1 failed.

Phase 2: Pushing initial configs...
[*] R1: connecting to 192.168.1.50:32769 ...
[+] R1: config applied.
...
[=] All devices configured. PC1/PC2 load their .vpc files on boot.
```

### Error Handling

- Reset failures are logged but do not abort the run
- Push failures follow existing behavior (tracked, logged, reflected in exit code)
- Final exit code = 1 if any device fails in either phase; 0 if all succeed

## Future Considerations (Out of Scope)

- Selective device reset (`--reset R1,R2`) — deferred, can be added later
- Reload-based reset (`--reload`) — not needed for current lab configs
