# /// script
# requires-python = ">=3.12"
#
# [tool.orcaslicer.plugin]
# name = "Kiln IFS Tool Map"
# description = "Kiln OS (Flashforge AD5X): sends each tool to the IFS slot that holds its filament, by material and colour."
# author = "Kiln OS"
# version = "0.1.0"
# type = "slicing-pipeline"
# ///
"""Kiln IFS Tool Map: an OrcaSlicer slicing-pipeline plugin for printers on
Kiln OS (Flashforge AD5X with the IFS, 4 slots).

On Kiln OS a slicer tool T0-T3 loads IFS slot 1-4 unless the file says
otherwise with IFS_MAP_TOOL TOOL=n SLOT=m (valid for that print). At the
G-code post-process step (export or upload) this plugin:

1. reads which tools the file uses and their filament type and colour
   (OrcaSlicer's "filament used", filament_type and filament_colour);
2. asks the printer's Moonraker what is in each slot
   (GET /printer/objects/query?ifs_materials&ifs);
3. picks for each tool the slot with the same material (exact, then the
   same family: PLA-CF ~ PLA) and the nearest colour;
4. writes one IFS_MAP_TOOL line per used tool at the top of the file.

Nothing to install on the printer: Kiln OS has IFS_MAP_TOOL and the
ifs_materials status already. The printer refuses a mapped slot without
filament when the print starts.

Config (Plugins > Kiln IFS Tool Map > Config):
  printer_url   "http://192.168.1.56" (empty: the physical printer's host,
                when OrcaSlicer passes it)
  on_mismatch   "error": stop the export/upload when a tool's material is in
                no slot; "keep": leave that tool on its default slot
  if_offline    "skip": printer unreachable -> file unchanged; "error": stop
  timeout       seconds for the printer query (3)

This file may be distributed under the terms of the GNU GPLv3 license.
"""
import json
import re
import urllib.error
import urllib.request

try:
    import orca
except ImportError:		# tests: a stand-in is installed before import
    orca = None

SLOTS = (1, 2, 3, 4)
TOOLS = (0, 1, 2, 3)
MARK = "; kiln-orca"
DEFAULTS = {
    "printer_url": "",
    "on_mismatch": "error",
    "if_offline": "skip",
    "timeout": 3,
}
# OrcaSlicer filament_type -> IFS family (Kiln OS slot types: PLA, PLA-CF,
# SILK, TPU, ABS, PETG, PETG-CF, or what the user typed)
FAMILY = {"SILK": "PLA", "PLA+": "PLA", "PLA-S": "PLA", "PETG-HF": "PETG"}


# --- G-code ---------------------------------------------------------------

def config_list(lines, key):
    """Values of an OrcaSlicer config comment '; key = a;b;c' (last wins)."""
    pat = re.compile(r"^;\s*" + re.escape(key) + r"\s*=\s*(.*)$")
    found = None
    for line in lines:
        m = pat.match(line)
        if m:
            found = m.group(1).strip()
    if found is None:
        return []
    sep = ";" if ";" in found or "," not in found else ","
    return [v.strip().strip('"') for v in found.split(sep)]


def used_tools(lines):
    """Tools the file uses: 'filament used' > 0, T<n> commands, TOOL=."""
    used = set()
    for key in ("filament used [mm]", "filament used [g]"):
        for i, v in enumerate(config_list(lines, key)):
            try:
                if float(v) > 0:
                    used.add(i)
            except ValueError:
                pass
    tcmd = re.compile(r"^\s*T([0-9])\b")
    tool = re.compile(r"^\s*(?:PRINT_START|START_PRINT)\b.*\bTOOL=([0-9])\b",
                      re.I)
    for line in lines:
        if line.startswith(";"):
            continue
        m = tcmd.match(line) or tool.match(line)
        if m:
            used.add(int(m.group(1)))
    return sorted(t for t in used if t in TOOLS)


def strip_previous(lines):
    """Drop the lines an earlier run of this plugin added."""
    out, skip = [], False
    for line in lines:
        if line.startswith(MARK + " start"):
            skip = True
            continue
        if skip and line.startswith(MARK + " end"):
            skip = False
            continue
        if not skip:
            out.append(line)
    return out


# --- matching -------------------------------------------------------------

def parse_color(text):
    m = re.match(r"^#?([0-9a-fA-F]{6})(?:[0-9a-fA-F]{2})?$",
                 (text or "").strip())
    if not m:
        return None
    v = int(m.group(1), 16)
    return (v >> 16 & 0xff, v >> 8 & 0xff, v & 0xff)


def color_distance(a, b):
    """'Redmean' RGB distance, 0 (same) .. ~765; None if either unknown."""
    if a is None or b is None:
        return None
    rm = (a[0] + b[0]) / 2.
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return ((2 + rm / 256.) * dr * dr + 4 * dg * dg
            + (2 + (255 - rm) / 256.) * db * db) ** .5


def family(mtype):
    t = (mtype or "").strip().upper()
    t = FAMILY.get(t, t)
    return re.split(r"[-+ _]", t)[0] if t else ""


def material_rank(want, have):
    """0 same material, 1 same family, 2 slot type unknown, 3 different."""
    w, h = (want or "").strip().upper(), (have or "").strip().upper()
    if not h:
        return 2
    if not w or w == h:
        return 0
    if family(w) == family(h):
        return 1
    return 3


def choose(tools, filaments, slots, present):
    """tool -> (slot, rank, distance) for each used tool.

    filaments: tool -> (type, (r,g,b) or None) from the file
    slots: slot -> (type, (r,g,b) or None) from the printer
    present: slots with filament (None: unknown, all count)
    """
    result = {}
    for t in tools:
        ftype, fcol = filaments.get(t, ("", None))
        best = None
        for s in SLOTS:
            if present is not None and s not in present:
                continue
            stype, scol = slots.get(s, ("", None))
            rank = material_rank(ftype, stype)
            d = color_distance(fcol, scol)
            key = (rank, d if d is not None else 1000., s != t + 1, s)
            if best is None or key < best[0]:
                best = (key, s, rank, d)
        if best is not None:
            result[t] = (best[1], best[2], best[3])
    return result


# --- printer --------------------------------------------------------------

def query_printer(url, timeout):
    q = url.rstrip("/") + "/printer/objects/query?ifs_materials&ifs"
    with urllib.request.urlopen(q, timeout=timeout) as r:
        st = json.load(r)["result"]["status"]
    mats = st.get("ifs_materials")
    if not mats:
        raise LookupError("the printer reports no IFS (ifs_materials); "
                          "is it on Kiln OS?")
    slots = {}
    for k, v in (mats.get("slots") or {}).items():
        slots[int(k)] = ((v or {}).get("type") or "",
                         parse_color((v or {}).get("color")))
    ifs = st.get("ifs") or {}
    present = None
    if ifs.get("connected") and ifs.get("loaded_channels") is not None:
        present = set(ifs["loaded_channels"])
    return slots, present


def printer_url(cfg, ctx):
    url = (cfg.get("printer_url") or "").strip()
    if not url and ctx is not None:
        try:
            url = (ctx.config_value("print_host") or "").strip()
        except Exception:
            url = ""
    if url and not re.match(r"^https?://", url):
        url = "http://" + url
    return url


def describe(ftype, col):
    c = "#%02X%02X%02X" % col if col else "?"
    return f"{ftype or '?'} {c}"


def process(path, cfg, ctx=None, query=None):
    """Edit the G-code at path. Returns (ok, message)."""
    query = query or query_printer
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = strip_previous(f.readlines())
    tools = used_tools(lines)
    if not tools:
        return True, "no tools used, file unchanged"
    types = config_list(lines, "filament_type")
    colors = config_list(lines, "filament_colour")
    filaments = {t: (types[t] if t < len(types) else "",
                     parse_color(colors[t]) if t < len(colors) else None)
                 for t in tools}
    url = printer_url(cfg, ctx)
    if not url:
        return (cfg.get("if_offline") != "error",
                "no printer_url set (plugin config), file unchanged")
    try:
        slots, present = query(url, float(cfg.get("timeout") or 3))
    except (OSError, urllib.error.URLError, ValueError, KeyError,
            LookupError) as e:
        msg = f"printer {url} not reachable or not Kiln OS ({e})"
        if cfg.get("if_offline") == "error":
            return False, msg
        return True, msg + ", file unchanged"
    picks = choose(tools, filaments, slots, present)
    out, problems = [], []
    for t in tools:
        want = describe(*filaments[t])
        if t not in picks:
            problems.append(f"T{t} ({want}): no slot has filament")
            continue
        s, rank, d = picks[t]
        have = describe(*slots.get(s, ("", None)))
        if rank == 3:
            problems.append(f"T{t} ({want}): no slot has this material "
                            f"(closest slot {s}: {have})")
            if cfg.get("on_mismatch") != "error":
                out.append(f"{MARK}: T{t} {want}: no matching slot, "
                           f"left on slot {t + 1}\n")
            continue
        note = "" if rank == 0 else (" (same family)" if rank == 1
                                     else " (slot type not set)")
        if d is not None and d > 150:
            note += " (colour differs)"
        out.append(f"{MARK}: T{t} {want} -> slot {s} {have}{note}\n")
        out.append(f"IFS_MAP_TOOL TOOL={t} SLOT={s}\n")
    if problems and cfg.get("on_mismatch", "error") == "error":
        return False, "IFS slots don't match the file: " + "; ".join(problems)
    block = [f"{MARK} start (tool map from {url})\n"] + out + [f"{MARK} end\n"]
    # Keep the first line first (some printers expect a header line)
    at = 1 if lines and lines[0].startswith(";") else 0
    lines[at:at] = block
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    maps = ", ".join(f"T{t}->slot {picks[t][0]}" for t in tools
                     if t in picks and picks[t][1] != 3) or "no tool mapped"
    return True, maps + (("; " + "; ".join(problems)) if problems else "")


# --- OrcaSlicer -----------------------------------------------------------

if orca is not None:
    class KilnIfsToolMap(orca.slicing.SlicingPipelineCapabilityBase):
        def get_name(self):
            return "Kiln IFS Tool Map"

        def get_default_config(self):
            return dict(DEFAULTS)

        def _config(self):
            cfg = dict(DEFAULTS)
            try:
                cfg.update(json.loads(self.get_config()) or {})
            except (TypeError, ValueError):
                pass
            return cfg

        def execute(self, ctx):
            if ctx.step != orca.slicing.Step.psGCodePostProcess:
                return orca.ExecutionResult.success()
            if not ctx.gcode_path:
                return orca.ExecutionResult.success("no G-code file")
            ok, msg = process(ctx.gcode_path, self._config(), ctx)
            if not ok:
                return orca.ExecutionResult.failure(
                    orca.PluginResult.RecoverableError, "Kiln IFS: " + msg)
            return orca.ExecutionResult.success("Kiln IFS: " + msg)

    @orca.plugin
    class KilnIfsToolMapPackage(orca.base):
        def register_capabilities(self):
            orca.register_capability(KilnIfsToolMap)
