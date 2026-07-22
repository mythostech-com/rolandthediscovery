from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

# ENTITY-MIB (RFC 2737) entPhysicalTable columns.
ENT_PHYSICAL_CLASS_OID = "1.3.6.1.2.1.47.1.1.1.1.5"
ENT_PHYSICAL_NAME_OID = "1.3.6.1.2.1.47.1.1.1.1.7"
ENT_PHYSICAL_SERIAL_OID = "1.3.6.1.2.1.47.1.1.1.1.11"
ENT_PHYSICAL_MFG_NAME_OID = "1.3.6.1.2.1.47.1.1.1.1.12"
ENT_PHYSICAL_MODEL_NAME_OID = "1.3.6.1.2.1.47.1.1.1.1.13"

ENT_PHYSICAL_CLASS_CHASSIS = "3"


@dataclass(frozen=True)
class DeviceInventory:
    make: Optional[str] = None
    model: Optional[str] = None
    serial: Optional[str] = None
    name: Optional[str] = None  # entPhysicalName, e.g. "Switch 1" - the stack member label, if any


def _clean_value(v: str) -> str:
    if ":" in v:
        v = v.split(":", 1)[1].strip()
    return v.strip().strip('"')


def _index_map(snmp, oid: str) -> Dict[int, str]:
    out: Dict[int, str] = {}
    for entry_oid, val in snmp.walk(oid):
        out[int(entry_oid.split(".")[-1])] = _clean_value(val)
    return out


def get_device_inventory(snmp) -> List[DeviceInventory]:
    """Best-effort chassis make/model/serial via ENTITY-MIB - one entry per
    physical chassis (entPhysicalClass=3).

    A standalone switch has exactly one chassis entry. A switch *stack*
    (e.g. a stack of 3850s) reports one chassis entry per stack member, each
    with its own make/model/serial - so this returns a list rather than a
    single value, with each member's entPhysicalName (typically "Switch 1",
    "Switch 2", etc.) included for identification.

    Falls back to the lowest-numbered physical index if no entry reports a
    chassis class (some platforms omit it) - matches prior single-chassis
    behavior for non-stacked devices.
    """
    classes = _index_map(snmp, ENT_PHYSICAL_CLASS_OID)
    serials = _index_map(snmp, ENT_PHYSICAL_SERIAL_OID)
    makes = _index_map(snmp, ENT_PHYSICAL_MFG_NAME_OID)
    models = _index_map(snmp, ENT_PHYSICAL_MODEL_NAME_OID)
    names = _index_map(snmp, ENT_PHYSICAL_NAME_OID)

    chassis_indices = sorted(idx for idx, cls in classes.items() if cls == ENT_PHYSICAL_CLASS_CHASSIS)

    if not chassis_indices:
        candidates = sorted(set(serials) | set(makes) | set(models))
        chassis_indices = candidates[:1]

    return [
        DeviceInventory(
            make=makes.get(idx) or None,
            model=models.get(idx) or None,
            serial=serials.get(idx) or None,
            name=names.get(idx) or None,
        )
        for idx in chassis_indices
    ]
