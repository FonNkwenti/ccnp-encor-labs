# CCNP ENCOR (350-401) Lab Series

Hands-on labs for the CCNP ENCOR (350-401) exam, built for EVE-NG on Intel/Windows.

Each lab is self-contained: topology file, initial and solution configs, a
student workbook, and automation scripts for initial setup, fault injection,
and solution restoration.

---

## End-to-End Workflow

The full path from a cold laptop to a running lab:

```
[VMware Workstation]                         (host the EVE-NG Ubuntu VM)
         |
         v
[EVE-NG web UI: http://<eve-ng-ip>]          (admin / eve)
         |
         v  import topology/<lab>.unl        (Add New Lab -> Import)
         |
         v  Start all nodes
         |
         v
[Your laptop: terminal]
         |
         v  pip install -r requirements.txt
         |
         v  python setup_lab.py --host <eve-ng-ip>      (push initial configs)
         |
         v
[Open workbook.md, work through Sections 1-8]
         |
         v  (optional) troubleshooting scenarios
         |     apply_solution.py   -> reset to known-good
         |     inject_scenario_NN.py -> break something
         |     diagnose + fix
         |     apply_solution.py   -> restore before next ticket
         v
[Complete checklist in workbook Section 10]
```

---

## Getting Started

### 1. Clone (with submodules)

```bash
git clone --recurse-submodules https://github.com/FonNkwenti/ccnp-encor-labs.git
cd ccnp-encor-labs
```

If you already cloned without submodules:

```bash
git submodule update --init --recursive
```

### 2. Install Python dependencies

Required on whichever machine runs the automation scripts (usually your
laptop, not the EVE-NG host itself):

```bash
pip install -r requirements.txt
```

This installs `netmiko` (console automation) and `requests` (EVE-NG REST
API port discovery).

### 3. Prepare EVE-NG

- Start VMware Workstation and boot the EVE-NG Ubuntu VM
- Note the VM's IP address (shown at the console login prompt)
- Browse to `http://<eve-ng-ip>` — default credentials: `admin` / `eve`
- Confirm the images listed in
  [`.agent/skills/eve-ng/SKILL.md`](.agent/skills/eve-ng/SKILL.md) Section 8
  are present under **System -> System status -> Installed Images**

### 4. Pick a lab — recommended progression

Follow this order to build foundational knowledge before advancing to complex topics.
Each lab builds on prior concepts within its domain.

**Foundation (Start here)**
- `labs/network-design/lab-00-design-principles` — Enterprise network design, 2/3-tier, fabric
- `labs/network-design/lab-01-high-availability` — Redundancy and FHRP concepts

**Layer 2 & Switching (Infrastructure foundation)**
- `labs/switching/lab-00-vlans-and-trunking` — VLANs, 802.1Q trunks
- `labs/switching/lab-01-etherchannel` — Link aggregation
- `labs/switching/lab-02-rstp-and-enhancements` — RSTP, root guard, BPDU guard
- `labs/switching/lab-03-mst` — Multi-Spanning-Tree
- `labs/switching/lab-04-capstone-config` — Capstone: configure L2 design
- `labs/switching/lab-05-capstone-troubleshoot` — Capstone: troubleshoot L2

**Virtualization (Before Layer 3 routing)**
- `labs/virtualization/lab-00-vrf-lite` — VRF data plane separation
- `labs/virtualization/lab-01-vrf-dual-stack` — VRF with IPv4/IPv6
- `labs/virtualization/lab-02-gre-tunnels` — GRE tunneling
- `labs/virtualization/lab-03-ipsec-and-gre-over-ipsec` — IPsec encryption
- `labs/virtualization/lab-04-capstone-config` — Capstone: configure tunneling
- `labs/virtualization/lab-05-capstone-troubleshoot` — Capstone: troubleshoot tunneling

**Layer 3 Routing (Core routing protocols)**
- `labs/ospf/lab-00-single-area-ospfv2` — OSPFv2 single area fundamentals
- `labs/ospf/lab-01-multi-area-ospfv2` — OSPFv2 multi-area
- `labs/ospf/lab-02-network-types` — OSPF network types (broadcast, point-to-point, etc.)
- `labs/ospf/lab-03-area-types` — OSPF area types (normal, stub, NSSA, transit)
- `labs/ospf/lab-04-summarization-filtering` — OSPF route summarization and filtering
- `labs/ospf/lab-05-capstone-config` — Capstone: configure complex OSPF
- `labs/ospf/lab-06-capstone-troubleshoot` — Capstone: troubleshoot OSPF
- `labs/eigrp/lab-00-classic-eigrp` — EIGRP classic mode
- `labs/eigrp/lab-01-named-mode-dual-stack` — EIGRP named mode with IPv4/IPv6
- `labs/eigrp/lab-02-stub-summarization-variance` — EIGRP stubs, summarization, variance
- `labs/eigrp/lab-03-capstone-config` — Capstone: configure EIGRP
- `labs/eigrp/lab-04-capstone-troubleshoot` — Capstone: troubleshoot EIGRP
- `labs/bgp/lab-00-ebgp-peering` — eBGP peer relationships
- `labs/bgp/lab-01-ibgp-and-dual-stack` — iBGP, dual-stack BGP
- `labs/bgp/lab-02-best-path-selection` — BGP best path algorithm
- `labs/bgp/lab-03-capstone-config` — Capstone: configure BGP
- `labs/bgp/lab-04-capstone-troubleshoot` — Capstone: troubleshoot BGP

**IP Services (Application layer services)**
- `labs/ip-services/lab-00-ntp-and-qos` — NTP time sync, QoS
- `labs/ip-services/lab-01-nat-pat` — NAT/PAT translation
- `labs/ip-services/lab-02-hsrp` — HSRP active/standby redundancy
- `labs/ip-services/lab-03-vrrp-dual-stack` — VRRP with dual-stack
- `labs/ip-services/lab-04-capstone-config` — Capstone: configure IP services
- `labs/ip-services/lab-05-capstone-troubleshoot` — Capstone: troubleshoot IP services

**Multicast (IP Services advanced)**
- `labs/multicast/lab-00-pim-sm-and-igmp` — PIM sparse-mode, IGMP
- `labs/multicast/lab-01-rp-discovery-and-igmpv3` — RP discovery, IGMPv3
- `labs/multicast/lab-02-ssm-bidir-msdp` — SSM, bidirectional, MSDP
- `labs/multicast/lab-03-capstone-config` — Capstone: configure multicast
- `labs/multicast/lab-04-capstone-troubleshoot` — Capstone: troubleshoot multicast

**Network Assurance (Monitoring & diagnostics)**
- `labs/network-assurance/lab-00-diagnostics` — ping, traceroute, debug, syslog
- `labs/network-assurance/lab-01-flexible-netflow` — NetFlow v5/v9 collection
- `labs/network-assurance/lab-02-span-rspan` — SPAN, RSPAN traffic capture
- `labs/network-assurance/lab-03-ip-sla` — IP SLA probes and alerting
- `labs/network-assurance/lab-04-capstone-config` — Capstone: design assurance
- `labs/network-assurance/lab-05-capstone-troubleshoot` — Capstone: troubleshoot assurance

**Security (Device & infrastructure hardening)**
- `labs/security/lab-00-device-access` — Console, SSH, privilege levels
- `labs/security/lab-01-aaa` — AAA (TACACS+, RADIUS) authentication/authorization
- `labs/security/lab-02-acls` — Standard and extended ACLs
- `labs/security/lab-03-copp` — Control Plane Policing
- `labs/security/lab-04-capstone-config` — Capstone: secure infrastructure
- `labs/security/lab-05-capstone-troubleshoot` — Capstone: troubleshoot security

**Overlay Technologies (Network virtualization)**
- `labs/overlay-technologies/lab-00-device-virtualization` — Hypervisors, virtual switching
- `labs/overlay-technologies/lab-01-lisp-and-vxlan` — LISP, VXLAN encapsulation
- `labs/overlay-technologies/lab-02-capstone-review` — Capstone: review overlay concepts

**SD-Networking (Modern architecture & automation foundation)**
- `labs/sd-networking/lab-00-sdwan-fabric-bringup` — SD-WAN fabric startup
- `labs/sd-networking/lab-01-sdwan-omp-and-policies` — Overlay Management Protocol (OMP)
- `labs/sd-networking/lab-02-sdwan-data-plane` — SD-WAN data forwarding
- `labs/sd-networking/lab-03-sd-access-concepts` — SD-Access control/data planes
- `labs/sd-networking/lab-04-capstone-config` — Capstone: configure SD-x
- `labs/sd-networking/lab-05-capstone-troubleshoot` — Capstone: troubleshoot SD-x

**Security Concepts (Design & architecture)**
- `labs/security-concepts/lab-00-security-design` — Threat defense, endpoint, NGFW
- `labs/security-concepts/lab-01-catalyst-center-and-apis` — Catalyst Center APIs
- `labs/security-concepts/lab-02-capstone-review` — Capstone: security design review

**Automation (Capstone skills — do last)**
- `labs/automation/lab-00-eem-applets` — EEM event-driven automation
- `labs/automation/lab-01-python-and-json` — Python scripting and JSON
- `labs/automation/lab-02-netconf` — NETCONF device configuration
- `labs/automation/lab-03-restconf` — RESTCONF REST-based config
- `labs/automation/lab-04-capstone-config` — Capstone: automation & config
- `labs/automation/lab-05-capstone-troubleshoot` — Capstone: automation troubleshooting

**[Optional] Demo Labs**
- `labs/ospf/lab-00-single-area-ospfv2(demo)` — Demonstration version with solutions

```bash
cd labs/switching/lab-00-vlans-and-trunking
```

Each lab directory has:

| File / Folder | Purpose |
|--------------|---------|
| `README.md` | Lab-specific quick-start (stages, timing, exam refs) |
| `meta.yaml` | Machine-readable metadata (devices, difficulty, blueprint refs) |
| `workbook.md` | Student-facing walkthrough — this is where you spend most time |
| `topology/` | `.drawio` diagram + EVE-NG `.unl` file + import README |
| `initial-configs/` | Starting configs pushed by `setup_lab.py` (bare-minimum) |
| `solutions/` | Full solution configs used by `apply_solution.py` |
| `setup_lab.py` | One-shot initial config loader |
| `scripts/fault-injection/` | Troubleshooting scenarios + solution restore |

### 5. Build the topology

Import `topology/<lab-name>.unl` into EVE-NG (see
`topology/README.md` in each lab for the exact steps). Start all nodes.

### 6. Push initial configs

```bash
python setup_lab.py --host <eve-ng-ip>
```

Ports are discovered automatically via the EVE-NG REST API — no port-number
editing required.

### 7. Work the workbook

Open `workbook.md` and follow Sections 1-8. Section 9 contains optional
troubleshooting scenarios; Section 10 is the completion checklist.

---

## Repository Layout

```
ccnp-encor-labs/
  blueprint/350-401/       # Exam blueprint (source of truth for scope)
  specs/                   # Topic-level planning: topic-plan.yaml
  labs/
    <topic>/               # e.g. switching/, ospf/, bgp/
      spec.md              # Topic spec (design decisions)
      baseline.yaml        # Shared topology core across labs in this topic
      lab-NN-<slug>/       # One lab per blueprint sub-objective
    common/tools/          # Shared automation (eve_ng.py, lab_utils.py)
  tasks/                   # todo.md, lessons.md (planning + retrospectives)
  .agent/skills/           # Submodule: platform-agnostic skill library
  requirements.txt
```

---

## Three-Phase Lab Development Workflow

Lab authors use a repeatable pipeline:

1. **Plan** — upload blueprint, run `exam-planner` skill → generates
   `specs/topic-plan.yaml` + empty `labs/<topic>/` folders
2. **Spec** — run `spec-creator` per topic → generates `spec.md` +
   `baseline.yaml` (reviewed before next step)
3. **Build** — run `lab-assembler` per lab → generates workbook,
   configs, topology, scripts (reviewed before next lab)

See [`CLAUDE.md`](CLAUDE.md) and
[`.agent/skills/CLAUDE.md`](.agent/skills/CLAUDE.md) for skill details.

---

## Updating the skills submodule

```bash
git submodule update --remote .agent/skills
git add .agent/skills
git commit -m "chore: bump skills submodule"
```

---

## Exam

- **CCNP ENCOR 350-401** -- current blueprint at
  [`blueprint/350-401/blueprint.md`](blueprint/350-401/blueprint.md)
- **Platform:** EVE-NG on Dell Latitude 5540 (Intel/Windows)
- **Image inventory:** confirmed on this lab host; see eve-ng skill Section 8
