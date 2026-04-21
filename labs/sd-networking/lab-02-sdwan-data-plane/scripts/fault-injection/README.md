# Fault Injection — SD-WAN Lab 02

Each script injects one fault. Work through the corresponding ticket in
`workbook.md` Section 9 before looking at the solution.

## Prerequisites

- EVE-NG lab must be running with all nodes started
- All nodes accessible via their EVE-NG console ports (telnet to `<eve-ng-ip>:<dynamic-port>`)
- Console ports are dynamic — obtain them from the EVE-NG web UI after lab creation
- Python 3.x installed
- `netmiko` library installed (`pip install netmiko`)

## Inject a Fault

```bash
python3 inject_scenario_01.py --host <eve-ng-ip> --port <vSmart-console-port>   # Ticket 1
python3 inject_scenario_02.py --host <eve-ng-ip> --port <vSmart-console-port>   # Ticket 2
python3 inject_scenario_03.py --host <eve-ng-ip> --port <vEdge2-console-port>   # Ticket 3
```

## Restore

After completing each ticket, restore all affected devices to the known-good state:

```bash
python3 apply_solution.py \
  --host <eve-ng-ip> \
  --vSmart-port <port> \
  --vEdge2-port <port>
```

The `--reset` flag is accepted for CLI consistency but is a no-op for Viptela OS
devices (no non-interactive config erase equivalent). Solution configs are pushed
additively and the commit overwrites any injected fault values.
