# Fault Injection -- Multicast Lab 04 (Capstone II)

This capstone lab ships pre-broken. All six faults are already baked into
`initial-configs/` and are applied by the normal `setup_lab.py`. There are no
per-ticket inject scripts -- the troubleshooting tickets in `workbook.md`
Section 9 describe the symptoms you will observe on the pre-broken network.

## Prerequisites

1. The lab is running in EVE-NG (`multicast/lab-04-capstone-troubleshoot.unl`).
2. Pre-broken configs pushed with `python3 ../../setup_lab.py --host <eve-ng-ip>`.

## Restore

Once you have worked through every ticket (or want a clean slate to retry), run:

```bash
python3 apply_solution.py
```

This pushes the reference solution (identical to lab-03 end-state) to R1-R4.
