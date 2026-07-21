from __future__ import annotations

import os
import sys

_bar_active = False
_last_line_len = 0
_BAR_WIDTH = 20


def _is_tty() -> bool:
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


def clear_screen() -> None:
    """Clear the terminal at startup, for a clean first screen. No-op when stdout
    isn't a terminal (redirected output, CI, etc).

    Uses the native OS command (cls/clear) rather than an ANSI escape - the same
    reason render() avoids ANSI: not every console interprets those, and printing
    one literally would be a worse first impression than not clearing at all.
    """
    if not _is_tty():
        return
    os.system("cls" if os.name == "nt" else "clear")


def render(current: int, total: int, *, depth: int, queue: int, label: str, phase: str = "") -> None:
    """Draw (or redraw in place) a single-line progress bar.

    `phase` is a short "what's happening right now" tag (e.g. "SNMP: sysName",
    "CDP neighbors", "SSH enrich") so a slow/stuck step is visible instead of
    the bar just sitting there looking frozen.

    Falls back to a plain scrolling line when stdout isn't a terminal (redirected
    to a file, CI, etc.) so a live-updating bar never garbles non-interactive output.

    Redraws via a bare carriage return, padded with trailing spaces to fully
    overwrite whatever was on the line before - deliberately NOT using an ANSI
    "clear line" escape (\\x1b[2K), since plenty of Windows consoles print that
    literally instead of interpreting it, which garbles the output.
    """
    global _bar_active, _last_line_len

    suffix = f"  [{phase}]" if phase else ""

    if not _is_tty():
        print(f"[roland] processing depth={depth} node={label} visited={current}/{total} queue={queue}{suffix}")
        return

    total = max(total, 1)
    frac = min(1.0, max(0.0, current / total))
    filled = int(_BAR_WIDTH * frac)
    bar = "█" * filled + "░" * (_BAR_WIDTH - filled)
    pct = int(frac * 100)
    line = f"Discovering  [{bar}]  {pct:3d}%  {current}/{total} nodes  depth={depth}  queue={queue}  {label}{suffix}"

    sys.stdout.write("\r" + line.ljust(_last_line_len))
    sys.stdout.flush()
    _last_line_len = len(line)
    _bar_active = True


def break_line() -> None:
    """Move off the active bar line before printing something else. No-op if no bar is active."""
    global _bar_active, _last_line_len
    if _bar_active:
        sys.stdout.write("\n")
        sys.stdout.flush()
        _bar_active = False
        _last_line_len = 0


def status(msg: str) -> None:
    """Print a permanent status/warning/error line, breaking out of any active bar first."""
    break_line()
    print(msg)


def finish() -> None:
    """Call once the crawl loop ends, to leave the cursor on a fresh line."""
    break_line()
