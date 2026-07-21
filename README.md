# roland-the-discovery (v1.4)

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
