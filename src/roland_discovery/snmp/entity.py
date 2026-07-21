from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

# ENTITY-MIB (RFC 2737) entPhysicalTable columns.
ENT_PHYSICAL_CLASS_OID = "1.3.6.1.2.1.47.1.1.1.1.5"
ENT_PHYSICAL_SERIAL_OID = "1.3.6.1.2.1.47.1.1.1.1.11"
ENT_PHYSICAL_MFG_NAME_OID = "1.3.6.1.2.1.47.1.1.1.1.12"
ENT_PHYSICAL_MODEL_NAME_OID = "1.3.6.1.2.1.47.1.1.1.1.13"

ENT_PHYSICAL_CLASS_CHASSIS = "3"


@dataclass(frozen=True)
class DeviceInventory:
    make: Optional[str] = None
    model: Optional[str] = None
    serial: Optional[str] = None


def _clean_value(v: str) -> str:
    if ":" in v:
        v = v.split(":", 1)[1].strip()
    return v.strip().strip('"')


def _index_map(snmp, oid: str) -> Dict[int, str]:
    out: Dict[int, str] = {}
    for entry_oid, val in snmp.walk(oid):
        out[int(entry_oid.split(".")[-1])] = _clean_value(val)
    return out


def get_device_inventory(snmp) -> DeviceInventory:
    """Best-effort chassis make/model/serial via ENTITY-MIB.

    Picks the first entPhysicalIndex classified as a chassis (class=3). If no
    entry reports a chassis class (some platforms omit it), falls back to the
    lowest-numbered physical index, which is conventionally the chassis on
    Cisco IOS/IOS-XE/NX-OS.
    """
    classes = _index_map(snmp, ENT_PHYSICAL_CLASS_OID)
    serials = _index_map(snmp, ENT_PHYSICAL_SERIAL_OID)
    makes = _index_map(snmp, ENT_PHYSICAL_MFG_NAME_OID)
    models = _index_map(snmp, ENT_PHYSICAL_MODEL_NAME_OID)

    chassis_idx = None
    for idx, cls in classes.items():
        if cls == ENT_PHYSICAL_CLASS_CHASSIS:
            chassis_idx = idx
            break

    if chassis_idx is None:
        candidates = sorted(set(serials) | set(makes) | set(models))
        chassis_idx = candidates[0] if candidates else None

    if chassis_idx is None:
        return DeviceInventory()

    return DeviceInventory(
        make=makes.get(chassis_idx) or None,
        model=models.get(chassis_idx) or None,
        serial=serials.get(chassis_idx) or None,
    )
