import csv
import os

_COLUMNS = [
    "hostname",
    "location",
    "main_ip",
    "ips",
    "device_make",
    "device_model",
    "device_serial",
    "device_role",
    "device_vendor",
    "device_family",
    "poll_status",
]


def export_inventory_csv(g, path: str) -> None:
    """Write a flat asset catalog: one row per discovered device.

    Columns cover make/model/serial (via ENTITY-MIB, best-effort) and
    location (the device's SNMP hostname/sysName, per Roland's naming
    convention). Nodes with no real hostname are skipped since they carry
    no cataloging value.
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
        rows.append(
            {
                "hostname": hostname,
                "location": attrs.get("location", ""),
                "main_ip": main_ip,
                "ips": ";".join(ips),
                "device_make": attrs.get("device_make", ""),
                "device_model": attrs.get("device_model", ""),
                "device_serial": attrs.get("device_serial", ""),
                "device_role": attrs.get("device_role", ""),
                "device_vendor": attrs.get("device_vendor", ""),
                "device_family": attrs.get("device_family", ""),
                "poll_status": attrs.get("poll_status", ""),
            }
        )

    rows.sort(key=lambda r: r["hostname"].lower())

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
