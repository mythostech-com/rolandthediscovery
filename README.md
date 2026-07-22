# roland-the-discovery (v2.1)

## What's new vs v2.0
- **Switch stack support in the asset catalog**: a stacked switch (e.g. a stack of 3850s) reports one
  ENTITY-MIB chassis entry *per physical stack member*, each with its own make/model/serial. Previously only
  the first member was captured. Now every member is captured:
  - `out/inventory.csv` gets one row per physical stack member (not per node) - a `stack_unit` column (e.g.
    "Switch 1", "Switch 2") identifies which one, and hostname/location/ip are repeated across the rows so
    you can still filter/group by device.
  - Non-stacked (single-chassis) devices are unaffected - still exactly one row, `stack_unit` blank.
  - `topology.json` nodes get a new `device_stack` list (one entry per member); the existing single
    `device_make`/`device_model`/`device_serial` fields still reflect the first/primary member, for anything
    that only cares about one summary value per node.
  - The HTML tooltip shows a `Stack: N units` breakdown with each member's model/serial when a node has more
    than one stack member.

## What's new vs v1.9
- **`--retry-failed`**: combined with `--resume`, re-queues any node that previously failed SNMP poll or SSH
  enrichment (checked via `poll_status`/`ssh_status` in the saved state), instead of requiring a full re-crawl
  to pick up transient failures. Re-queued at the node's original discovery depth. No retry-count limit — keep
  passing the flag across runs until a device succeeds or you decide to stop (e.g. a device that's genuinely
  out of scope, like one managed by another team).
  ```powershell
  roland-discovery --resume out\state.json --retry-failed --seed 10.21.250.41 --depth 6 --ssh --html out\topology.html
  ```

## What's new vs v1.8
- Clears the terminal right before the startup banner, for a clean first screen instead of the banner
  appearing after whatever was already scrolled in your console. Uses the native `cls`/`clear` command rather
  than an ANSI escape (same reasoning as the progress bar fix above — not every console interprets those).
  Skipped automatically when stdout isn't a terminal.

## What's new vs v1.7
- **Fixed progress bar corruption on Windows consoles that don't interpret ANSI escapes**: the bar previously
  cleared each line with `\x1b[2K`, which some Windows consoles print literally (`←[2K`) instead of acting on,
  leaving stale characters from a longer previous line behind when the new line was shorter. It now pads with
  trailing spaces to the previous line's length instead — no ANSI codes involved at all.
- Downgraded `[WARN cdp hex fail]` to `--debug`-only and gave it real context (OID + raw value) when it does
  show — it fires routinely for CDP neighbors (phones, APs, etc.) that don't report a management address, so
  it was never actually an actionable warning, just confusing noise (previously showed as a bare `→ Not 4 bytes`
  with no indication of which neighbor or field).

## What's new vs v1.6
- **Startup banner**: a run now immediately prints seed/depth/max-nodes/SSH/traverse-all/inventory settings
  before any network calls happen, so you get instant confirmation the tool launched — regardless of how slow
  the crawl itself ends up being.
- **"What's happening now" phase tags** on the progress bar (`[SNMP: interface map]`, `[CDP neighbors]`,
  `[SSH enrich]`, etc.) so a slow/stuck step is visible instead of the bar just sitting there looking frozen.
- Fixed `snmp/cdp.py` (SNMP-based CDP neighbor discovery) printing a dense, unconditional per-neighbor debug
  trace (`[RAW SNMP cdpCacheDeviceId]`, `[DEBUG cdp mgmt_raw]`, `[DEBUG cdp neighbor]`) that got missed in the
  v1.5 quiet-output pass — this was gluing straight onto the end of the progress bar line with no line break.
  Also fixed one stray unconditional debug print in `ssh/enrich.py`. Both now respect `--debug` like everything
  else.

## What's new vs v1.5
- **Live progress bar**: interactive runs now show a single in-place bar (`Discovering [████░░░░] 55% 138/250
  nodes depth=3 queue=41 10.21.250.87 (HUB-BB-NX01)`) instead of a scrolling line per node. Any real warning or
  error (failed poll, SNMP health-check failure, SSH failure) still prints as its own permanent line — the bar
  breaks for it, then resumes underneath. Falls back to the old plain scrolling line automatically when stdout
  isn't a terminal (redirected to a file, etc.) or when `--debug` is set.

## What's new vs v1.4
- **Quiet by default**: normal runs now print a clean set of progress/status lines instead of dozens of
  `[DEBUG]`/`[SNMP]`/`[RAW SNMP]`/`[LOGGED RAW]` lines per device. All internal tracing is still available —
  pass `--debug` to get it back. See [Console output / --debug](#console-output---debug) below.
- Removed a dead duplicate `log_raw_response()` in `ssh/client.py` that shadowed the shared one in
  `util/logging.py` (no behavior change — SSH raw-response logging still works the same).

## What's new vs v1.3
- **Asset catalog**: Roland now records `device_make`, `device_model`, `device_serial` (via ENTITY-MIB) and
  `location` (the device's SNMP hostname) on every polled node, and writes them to a new `out/inventory.csv`.
  See [Asset catalog (make/model/serial/location)](#asset-catalog-makemodelserialslocation) below.
- Fixed the HTML viewer's "hide leaf / hide unpolled / hide failed / only infra" filter checkboxes — they were
  silent no-ops because the node data they filter on (`roland_status`/`roland_role`/`roland_degree`) was never
  attached to graph nodes.
- Removed stray backup/scratch files (`*.bak`, `build3.py`, top-level `build.py`/`client.py`, `graph/utils.py`)
  and committed `.zip`/`.diff` snapshots that weren't part of the actual package.

## What's new vs v0.8
- Progress output now includes **queue size** and **neighbors/enqueue counts** so you can estimate “how much left”.
  Example:
  - `[roland] processing depth=2 node=10.21.250.22 visited=17/250 queue=9`
  - `[roland] polled node=10.21.250.22 neighbors=6 enqueued=2 queue=11`

## Run
```powershell
roland-discovery --seed 10.21.90.1 --community COMMUNITY --depth 3 --max-nodes 250 --include-subnet 10.21.0.0/16 --html out/topology.html --summary
```

## Outputs
- JSON: `out/topology.json`
- DOT:  `out/topology.dot`
- HTML: `out/topology.html` (interactive zoom/pan/drag)
- CSV:  `out/inventory.csv` (asset catalog: make/model/serial/location, see below)

## Graphviz tips
- Prefer SVG for crisp zoom:
```powershell
dot -Tsvg out/topology.dot -o out/topology.svg
```


## Hostname merge / de-dup
By default, Roland will **merge nodes that resolve to the same sysName** (hostname) to reduce duplicate “extra spiders”.
- Disable with `--no-merge-hostname`
- In the HTML graph, the node tooltip will show all known IPs for the merged device.

## Ignoring non-network CDP/LLDP neighbors (e.g. Axis cameras)
By default, neighbors whose **remote device name starts with `axis`** (case-insensitive) are ignored
(not added to the graph and never enqueued for discovery).

- Override default behavior with `--include-axis`
- Add additional ignore prefixes with `--ignore-hostname-prefix <prefix>` (repeatable)


## Fixes
- Fixed Windows DOT exporter newline handling (no more `illegal newline value`).

## IP alias correlation (fixing “spider legs” to interface IPs)
Some CDP/LLDP neighbors report a management address that is actually **another IP on a device you've already discovered**
(SVI, loopback, secondary interface IP, etc).

Roland now:
- Walks the device IP list via `ipAddrTable` (IP-MIB OID `1.3.6.1.2.1.4.20.1.1`)
- Stores them on the node as `ips`
- Uses a global IP→node map so if a neighbor points at an already-known alias IP, it is connected to the existing node
  instead of creating a new dangling node.

## Device classification
Roland classifies devices from `sysDescr` and hostname into:
- `device_role` (switch/router/endpoint/camera/unknown)
- `device_family` (catalyst/nexus/ie2000/ios/…)
- `device_vendor`

This is used for display today and will be used for traversal filtering next.

## Traversal filtering (avoid crawling non-infrastructure)
By default Roland will only *spider into* devices classified as `device_role` in:
- `switch`
- `router`

Other discovered neighbors (servers, cameras, unknowns, etc.) can still appear in the graph, but are treated as leaf nodes.

Override with:
- `--traverse-all` to spider into everything
- `--traverse-role <role>` (repeatable) to customize allowed roles


## HTML viewer improvements
- Tooltips render newlines properly
- Added a simple search box (top-left): type and press Enter to zoom to a match
- Nodes are colored by poll status (ok/failed/unpolled)


## Console output / --debug

By default Roland prints a clean set of lines: one per node as it's processed (`[roland] processing
depth=... node=... visited=... queue=...`), phase markers (`[INFO] Running final edge deduplication...`, etc.),
and real warnings/errors (failed polls, SSH failures, SNMP health-check failures). Internal step-by-step
tracing (per-OID SNMP walks, per-command SSH chatter, raw-response log confirmations, CDP resolution steps,
per-edge classification) is suppressed.

Pass `--debug` (or set `ROLAND_SNMP_DEBUG=1` / `--ssh-debug` for just the SNMP/SSH wire-level dumps) to get
the full verbose trace back — useful when a specific device is behaving unexpectedly and you need to see
exactly what was sent/received.

## Asset catalog (make/model/serial/location)

On by default, Roland queries **ENTITY-MIB** (`1.3.6.1.2.1.47.1.1.1.1`) on every polled device to record:
- `device_make` (`entPhysicalMfgName`, e.g. "Cisco Systems, Inc.")
- `device_model` (`entPhysicalModelName`, e.g. "N5K-C5010P-BF")
- `device_serial` (`entPhysicalSerialNum`)

These come from the chassis entry (`entPhysicalClass=3`), falling back to the lowest physical index if a device
doesn't report a class. Lookup is best-effort: devices that don't support ENTITY-MIB simply get no make/model/serial.

**Location** is recorded as the device's SNMP hostname (`sysName`) verbatim — no parsing or site-code extraction.

These fields are:
- written to every node in `topology.json` and shown in the HTML tooltip
- written as one row per device to `out/inventory.csv` (columns: hostname, location, main_ip, ips, device_make,
  device_model, device_serial, device_role, device_vendor, device_family, poll_status)

Disable with `--no-inventory`. Change the CSV path with `--inventory-csv <path>` (pass `--inventory-csv ""` to skip
writing it).

## SSH enrichment (optional)

Roland can optionally enrich nodes via SSH using the system `ssh` client (key-based auth).

Example:

```powershell
$env:ROLAND_SSH_USER="admin"
roland-discovery --seed 10.21.90.1 --community <community> --depth 2 --ssh --html out\top.html
```
