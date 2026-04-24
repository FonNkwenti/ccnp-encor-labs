# Multicast Labs — Linux End-Host Delta Spec

**Parent spec:** [`spec.md`](./spec.md) · **Baseline:** [`baseline.yaml`](./baseline.yaml)
**Platform reference:** `.agent/skills/eve-ng/SKILL.md` §4b

---

## 1. Context and Rationale

The parent spec uses VPCS for PC1 (source) and PC2 (receiver) across all five multicast
labs. VPCS has no multicast stack — it cannot send IGMP reports, receive multicast streams,
or do IGMPv3 source-specific filtering. Lab-00 and lab-01 work around this with the
`ip igmp join-group` trick on the router itself, which is pedagogically honest for the
router-side mechanics those labs are teaching.

From lab-02 onward the VPCS limitation stops being a workaround and starts actively
preventing the lesson:

- **SSM** is *defined* by the host sending an IGMPv3 Include(S,G) report. A router faking
  an IGMP join cannot demonstrate source-specific filtering as a host-driven mechanism.
- **MSDP** demonstrates that a receiver in one PIM domain gets traffic from a source in
  another domain via SA messages between RPs. This is only convincing with real receivers
  that actually consume packets.
- **Capstone labs** cannot be end-to-end validated — "did traffic reach the receiver?" is
  the fundamental success criterion and VPCS cannot answer it.

EVE-NG now has Alpine 3.18.4 and TinyCore 17.0 images registered (see
`.agent/skills/eve-ng/SKILL.md` §4b), giving us lightweight Linux end-hosts with real
multicast stacks. This delta specifies exactly how the multicast lab series adopts them.

---

## 2. Decision

Keep labs 00 and 01 on VPCS. Swap **both** PC1 and PC2 to Alpine Linux starting at lab-02.

| Lab | PC1 platform | PC2 platform | Notes |
|-----|--------------|--------------|-------|
| lab-00 | `vpc` (VPCS) | `vpc` (VPCS) | Unchanged — router-side mechanics only |
| lab-01 | `vpc` (VPCS) | `vpc` (VPCS) | Unchanged — RP discovery is router-side |
| lab-02 | `linux-alpine-3.18.4` | `linux-alpine-3.18.4` | **Introduces Linux hosts** for SSM IGMPv3 and MSDP end-to-end |
| lab-03 | `linux-alpine-3.18.4` | `linux-alpine-3.18.4` | Capstone config — real end-to-end validation |
| lab-04 | `linux-alpine-3.18.4` | `linux-alpine-3.18.4` | Capstone troubleshoot — host-side diagnostic vantage |

### Why this cut, not earlier

Moving lab-00/01 to Linux would add ~512 MB RAM per lab run for marginal pedagogical gain
(the router-side mechanics in those labs are fully observable with VPCS plus the
`ip igmp join-group` trick). The tradeoff flips at lab-02 where IGMPv3 source filtering is
the subject of the lesson, not an implementation detail.

### Why Alpine for both (not mixed Alpine + TinyCore)

The eve-ng skill prescribes Alpine for senders and TinyCore for receivers, and that split
would save ~128 MB per lab. We rejected the split for two reasons:

1. **One image to maintain.** Per-image prep (pre-installed packages, kernel sysctls,
   persistence mechanics) is duplicated work across two distros. Alpine alone keeps image
   management simple.
2. **Symmetric tooling for troubleshoot lab-04.** Lab-04's host-side diagnostic tickets
   are easier to author and run when both hosts expose the same CLI surface (same
   `tcpdump`, same `ip`, same `iperf`, same `socat`). TinyCore's `tce-load` package
   model and different shell defaults would add friction in the troubleshoot flow.

Cost of the decision: +128 MB per lab vs the asymmetric plan. On a 16 GB EVE-NG host this
is comfortable; on 8 GB hosts close other labs before running lab-02+.

---

## 3. Resource Budget

### Per-lab RAM totals

| Lab | Routers | Linux hosts | Total RAM |
|-----|---------|-------------|-----------|
| lab-00 (VPCS) | 3× IOSv = 1536 MB | 2× VPC ≈ 32 MB | ~1568 MB |
| lab-01 (VPCS) | 3× IOSv = 1536 MB | 2× VPC ≈ 32 MB | ~1568 MB |
| lab-02 (Linux) | 4× IOSv = 2048 MB | 2× Alpine = 512 MB | **~2560 MB** |
| lab-03 (Linux) | 4× IOSv = 2048 MB | 2× Alpine = 512 MB | **~2560 MB** |
| lab-04 (Linux) | 4× IOSv = 2048 MB | 2× Alpine = 512 MB | **~2560 MB** |

On a 16 GB EVE-NG host these fit comfortably; on 8 GB hosts close other labs before
running lab-02+.

### Disk (qcow2 overhead per node instance)

- Alpine: ~150 MB × 2 = ~300 MB per lab run

---

## 4. `baseline.yaml` Delta

The existing `core_topology.devices` list (VPCS) becomes the default. Add a new
`platform_overrides` section that specifies per-lab substitutions:

```yaml
# ──────────────────────────────────────────────
# Per-lab platform overrides
# Labs 00 and 01 inherit the defaults from core_topology.
# Labs 02+ swap VPCS end-hosts for Alpine Linux nodes per the delta spec.
# ──────────────────────────────────────────────
platform_overrides:
  - applies_to: [lab-02-ssm-bidir-msdp, lab-03-capstone-config, lab-04-capstone-troubleshoot]
    devices:
      - name: PC1
        platform: linux-alpine-3.18.4
        role: Multicast source — iperf/socat generator with real IGMP/UDP stack
        ram_mb: 256
        login: root/alpine
        ip: 10.1.1.10/24
        gateway: 10.1.1.1
        dns: 8.8.8.8
        required_packages: [iperf, socat, tcpdump, iproute2]
        optional_packages: [mcjoin]   # build from source — not in alpine main/community
        host_config: initial-configs/PC1.sh
      - name: PC2
        platform: linux-alpine-3.18.4
        role: Multicast receiver — IGMP joiner and iperf/socat UDP sink
        ram_mb: 256
        login: root/alpine
        ip: 10.1.3.10/24
        gateway: 10.1.3.1
        dns: 8.8.8.8
        required_packages: [iperf, socat, tcpdump, iproute2]
        optional_packages: [mcjoin]
        host_config: initial-configs/PC2.sh
```

The `core_topology.devices` entries for PC1 and PC2 stay as `platform: vpcs` — that keeps
labs 00 and 01 working off the unmodified baseline.

---

## 5. Host Configuration Convention

### File layout

Replace `.vpc` files with shell scripts for Linux hosts. Each lab's `initial-configs/`
directory owns its own host configs so a lab is self-contained:

```
labs/multicast/lab-02-ssm-bidir-msdp/
├── initial-configs/
│   ├── R1.cfg
│   ├── R2.cfg
│   ├── R3.cfg
│   ├── R4.cfg
│   ├── PC1.sh        # Alpine boot script — IP, route, IGMP version
│   └── PC2.sh        # Alpine boot script — IP, route, IGMP version
```

### Persistence model — always-push

`setup_lab.py` re-applies `PC1.sh` and `PC2.sh` on every run. We do **not** rely on
Alpine's `lbu commit` to bake config into the qcow2. Rationale:

- Consistent with the router path (Netmiko always pushes `initial-configs/*.cfg`)
- Known-good state lives in git, not inside a qcow2 snapshot
- Lets us iterate on host config without rebuilding images

The scripts are idempotent — `ip addr flush` + `ip addr add` handles repeated runs
cleanly.

### `PC1.sh` (Alpine, source)

```sh
#!/bin/sh
# Alpine Linux — multicast source for Multicast Lab 02+
# Applied on every setup_lab.py run via EVE-NG console push. Idempotent.

set -e

# Static IP + default route
ip addr flush dev eth0
ip addr add 10.1.1.10/24 dev eth0
ip link set eth0 up
ip route replace default via 10.1.1.1

# DNS (used by apk during image prep; not required at runtime)
echo "nameserver 8.8.8.8" > /etc/resolv.conf

# IGMPv3 for SSM source-specific reports (default kernel behavior on Alpine 3.18)
echo 3 > /proc/sys/net/ipv4/conf/eth0/force_igmp_version

echo "[+] PC1 (Alpine source) configured — 10.1.1.10/24"
```

### `PC2.sh` (Alpine, receiver)

```sh
#!/bin/sh
# Alpine Linux — multicast receiver for Multicast Lab 02+
# Applied on every setup_lab.py run via EVE-NG console push. Idempotent.

set -e

ip addr flush dev eth0
ip addr add 10.1.3.10/24 dev eth0
ip link set eth0 up
ip route replace default via 10.1.3.1

echo "nameserver 8.8.8.8" > /etc/resolv.conf

# IGMPv3 for SSM source-specific joins
echo 3 > /proc/sys/net/ipv4/conf/eth0/force_igmp_version

# Raise IGMP membership ceiling so capstone labs can join many groups on one iface
echo 64 > /proc/sys/net/ipv4/igmp_max_memberships

echo "[+] PC2 (Alpine receiver) configured — 10.1.3.10/24"
```

### Pre-baked image (one-time EVE-NG prep)

The base `linux-alpine-3.18.4` qcow2 must have these packages pre-installed:

```sh
apk add iperf socat tcpdump iproute2 bash
```

This is a one-time preparation outside the lab workflow. Document in
`.agent/skills/eve-ng/SKILL.md` §4b image-prep subsection.

### `mcjoin` status — not in Alpine main/community

`mcjoin` is present only in **Alpine edge/testing** (v2.11-r0, 2022), not in any stable
release including 3.18.4. We do **not** depend on it. Decisions:

1. **Primary tool for IGMP joins:** `socat` from Alpine main. Supports IGMPv3
   Include(S,G) via `ip-add-source-membership=<group>:<iface>:<source>`.
2. **Traffic generation:** `iperf` (iperf2) from Alpine main. Multicast client mode
   sends to a group; server mode with `-B <group>` joins ASM.
3. **Optional mcjoin:** If a workbook author wants explicit mcjoin CLI semantics, build
   from source during image prep:
   ```sh
   apk add --virtual .build-deps build-base git autoconf automake
   git clone https://github.com/troglobit/mcjoin /tmp/mcjoin
   cd /tmp/mcjoin && ./autogen.sh && ./configure && make install
   apk del .build-deps
   ```
   Treat as a nice-to-have, not a dependency.

### Tool substitution table

| Purpose | Primary (Alpine main) | Alternative |
|---------|----------------------|-------------|
| ASM receiver (*, G) | `iperf -s -u -B 239.1.1.1` | `socat UDP4-RECV:5000,ip-add-membership=239.1.1.1:eth0 STDOUT` |
| SSM receiver (S, G) | `socat UDP4-RECV:5000,ip-add-source-membership=232.1.1.1:eth0:10.1.1.10 STDOUT` | `mcjoin -g 232.1.1.1 -s 10.1.1.10` (if built) |
| Source (sender) | `iperf -c 239.1.1.1 -u -T 32 -t 60 -b 1M` | `socat - UDP4-DATAGRAM:239.1.1.1:5000,ttl=32` |
| Capture | `tcpdump -i eth0 -n igmp` | — |
| Host-view groups | `ip maddr show dev eth0` | `netstat -gn` |

---

## 6. `setup_lab.py` Delta

The existing script pushes router configs via Netmiko (telnet to EVE-NG console + IOS
command mode). For Linux hosts we need a second push path: telnet + shell-mode command
execution.

### New convention — `push_linux_host(host, name, port, script_path)`

Add to `labs/common/tools/eve_ng.py` (or a new `linux_host.py` module alongside it):

```python
def push_linux_host(
    host: str,
    name: str,
    port: int,
    script_path: Path,
    user: str = "root",
    passwd: str = "alpine",
) -> bool:
    """
    Push a shell script to an Alpine Linux end-host console via telnet.

    - Opens telnet to <host>:<port>
    - Sends a newline to wake the console
    - Detects login prompt, sends user + passwd
    - Reads script_path line-by-line, strips comments/blank lines
    - Writes each line at the shell prompt, one at a time
    - Does NOT run `lbu commit` — config is pushed fresh on every run
    """
    # Implementation: use pexpect or telnetlib3. Expect 'login:' → send user;
    # 'Password:' → send passwd; '#' → send each command. Short sleep between
    # commands to avoid line coalescing.
```

Each lab's `setup_lab.py` (labs 02+) will:

```python
DEVICES_IOS = ["R1", "R2", "R3", "R4"]
DEVICES_LINUX = ["PC1", "PC2"]   # both Alpine; same creds

for name in DEVICES_IOS:
    push_device(host, name, ports[name])

for name in DEVICES_LINUX:
    script_path = CONFIG_DIR / f"{name}.sh"
    push_linux_host(host, name, ports[name], script_path)
```

### Reuse policy

Build `push_linux_host()` once in shared tooling. Labs 02/03/04 import it; we don't
duplicate telnet-shell push logic in each lab.

---

## 7. Per-Lab Implications

### lab-02-ssm-bidir-msdp — New Linux-driven content

- **Section 5 tasks added / changed:**
  - Task: On PC2, join `(10.1.1.10, 232.1.1.1)` via `socat UDP4-RECV:5000,
    ip-add-source-membership=232.1.1.1:eth0:10.1.1.10 STDOUT > /dev/null &`
    (IGMPv3 Include(S,G)).
  - Task: On PC1, send `iperf -c 232.1.1.1 -u -T 32 -t 60 -b 1M` and observe (S,G)
    state on R1 directly (no shared tree, no RP involvement).
  - Task: For MSDP verification, start a receiver on PC2 for a group sourced in the
    R4 domain; verify SA propagation reaches R2 and the receiver actually gets packets
    (`iperf` bandwidth > 0 at the receiver).

- **Section 6 verification added:**
  - `tcpdump -i eth0 -n igmp` on PC2 — shows real IGMPv3 Include(S,G) PDU
  - `iperf -s -u -B 232.1.1.1 -i 1` on PC2 — bandwidth/jitter/loss stats prove
    end-to-end forwarding
  - `ip maddr show dev eth0` on PC2 — host-side view of joined groups

- **Section 9 troubleshooting:**
  - New fault candidate: `force_igmp_version=2` on PC2 (breaks SSM because v2 has no
    source list). Diagnose via `tcpdump` on PC2 showing v2 reports where v3 is needed.

### lab-03-capstone-config — End-to-end validation

- **Completion check** becomes real: every multicast mode (ASM, SSM, bidir) is
  verified with an actual iperf receiver on PC2 showing non-zero throughput.
- Workbook Section 10 checklist adds:
  - [ ] `iperf -s -u -B 239.1.1.1` on PC2 shows bandwidth received
  - [ ] `socat UDP4-RECV:5000,ip-add-source-membership=232.1.1.1:eth0:10.1.1.10` on
    PC2 captures SSM packets
  - [ ] `iperf -s -u -B 239.2.2.1` on PC2 shows bandwidth for bidir

### lab-04-capstone-troubleshoot — Host-side diagnostics

- New fault vantage point: PC2 `tcpdump` on `eth0` filters for IGMP or the multicast
  group. Tickets can plant host-side faults (wrong IGMP version, firewall rule, MAC
  filter) that only surface from the Linux side.
- Workbook Section 9 can include a "host-side" ticket — e.g., `igmp_max_memberships`
  set too low, or `force_igmp_version=2` on a lab where SSM is expected.

### lab-00 and lab-01 — No change

These labs keep `PC1.vpc` / `PC2.vpc`. The Section 3 hardware table still lists VPCS.
No workbook edits required for this delta.

---

## 8. Topology Diagram Delta

`topology/topology.drawio` for labs 02/03/04:

- PC1 and PC2 icons: swap from VPCS icon to "linux" / "server" icon; label
  "PC1 / Alpine" and "PC2 / Alpine"
- All other elements (routers, links, IPs) unchanged

The `drawio` skill handles icon swapping via its palette — no change to diagram structure.

---

## 9. Fault-Injection Delta

Labs 02–04 fault scripts continue to use Netmiko → IOS for router-side faults. For
host-side faults (lab-04 only), add a helper that uses telnet + shell:

```python
# fault-injection/inject_host_fault.py
from linux_host import push_linux_host
push_linux_host(host, "PC2", port, Path("faults/pc2_force_igmpv2.sh"))
```

Keep host faults optional — default fault mix stays on the router side so lab-04's
core lesson is CLI-driven troubleshooting.

---

## 10. Implementation Order

When building lab-02 (next lab in the queue after lab-01), follow this sequence:

1. Update `labs/multicast/baseline.yaml` — add `platform_overrides` block per §4
2. Add `push_linux_host()` to `labs/common/tools/` (new `linux_host.py` module
   alongside `eve_ng.py`)
3. Verify Alpine image prep: `iperf`, `socat`, `tcpdump`, `iproute2`, `bash` all
   `apk add`-ed and baked into the EVE-NG qcow2
4. Generate the lab normally via `lab-assembler` — the skill should pick up
   the platform override from baseline.yaml for PC1/PC2
5. Author `PC1.sh` and `PC2.sh` in `initial-configs/`
6. Run `setup_lab.py` against the EVE-NG host to verify Alpine nodes receive config
7. Generate `topology.drawio` with Linux icons
8. Run the full workbook end-to-end with real iperf/socat streams before committing

For labs 03/04, reuse the same overrides and host scripts. The host scripts themselves
are identical across 02/03/04 (same IP plan) — copy, don't re-author.

---

## 11. Validation (post-build)

Before ticking lab-02 complete:

- [ ] `iperf -s -u -B 239.1.1.1 -i 1` on PC2 shows non-zero bandwidth when PC1 sends
- [ ] `socat UDP4-RECV:5000,ip-add-source-membership=232.1.1.1:eth0:10.1.1.10 STDOUT`
  on PC2 receives SSM bytes when PC1 sends to 232.1.1.1
- [ ] `tcpdump -i eth0 igmp` on PC2 captures IGMPv3 Include(S,G) for the SSM task
- [ ] `show ip igmp groups` on R3 shows PC2's IP (10.1.3.10) as `Last Reporter`
  — not R3's loopback, as it would be with the VPCS workaround
- [ ] `show ip msdp sa-cache` on R2 shows SA entries sourced from R4's domain
- [ ] `setup_lab.py` is idempotent — two successive runs produce identical host state
  (verified by `ip addr show eth0` before/after)

---

## 12. Resolved Questions

- **Persistence model:** *Resolved — always-push.* `setup_lab.py` re-applies host
  scripts on every run; we do not use `lbu commit`. Known-good state lives in git.
- **`mcjoin` availability:** *Resolved — not in Alpine main.* mcjoin is in edge/
  testing only. `socat` (main) covers the IGMPv3 Include(S,G) requirement. mcjoin
  is listed as `optional_packages` in baseline.yaml — authors may build from source
  during image prep but workbooks do not assume it.
- **VPCS → Linux transition shock:** The lab-02 workbook must include a short "you
  are now using real Linux hosts" callout so students aren't surprised by the syntax
  change from VPCS `ip 10.1.1.10 255.255.255.0 10.1.1.1` to a shell prompt.
