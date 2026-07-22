import csv
import os

_COLUMNS = [
    "hostname",
    "location",
    "main_ip",
    "ips",
    "stack_unit",
    "device_make",
    "device_model",
    "device_serial",
    "device_role",
    "device_vendor",
    "device_family",
    "poll_status",
]


def export_inventory_csv(g, path: str) -> None:
    """Write a flat asset catalog: one row per physical device.

    Columns cover make/model/serial (via ENTITY-MIB, best-effort) and
    location (the device's SNMP hostname/sysName, per Roland's naming
    convention). A switch *stack* (multiple physical chassis reporting as one
    logical node - e.g. a stack of 3850s) gets one row per stack member, each
    with its own make/model/serial and a `stack_unit` label (e.g. "Switch 1")
    identifying which physical unit it is; all rows share the same
    hostname/location/ip. Nodes with no real hostname are skipped since they
    carry no cataloging value.
    """
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)

    rows = []
    for n, attrs in g.nodes(data=True):
        hostname = attrs.get("hostname")
        main_ip = attrs.get("main_ip") or attrs.get("ip") or n
        if not hostname or hostname == main_ip:
            continue
        ips = attrs.get("ips") or ([main_ip] if main_ip else [])

        base = {
            "hostname": hostname,
            "location": attrs.get("location", ""),
            "main_ip": main_ip,
            "ips": ";".join(ips),
            "device_role": attrs.get("device_role", ""),
            "device_vendor": attrs.get("device_vendor", ""),
            "device_family": attrs.get("device_family", ""),
            "poll_status": attrs.get("poll_status", ""),
        }

        stack = attrs.get("device_stack") or []
        if not stack:
            rows.append({
                **base,
                "stack_unit": "",
                "device_make": attrs.get("device_make", ""),
                "device_model": attrs.get("device_model", ""),
                "device_serial": attrs.get("device_serial", ""),
            })
        else:
            for member in stack:
                rows.append({
                    **base,
                    "stack_unit": member.get("name") or "",
                    "device_make": member.get("make") or "",
                    "device_model": member.get("model") or "",
                    "device_serial": member.get("serial") or "",
                })

    rows.sort(key=lambda r: (r["hostname"].lower(), r["stack_unit"]))

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
