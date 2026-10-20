# Kiln IFS Tool Map (OrcaSlicer plugin)

An [OrcaSlicer](https://github.com/OrcaSlicer/OrcaSlicer) plugin for
Flashforge AD5X printers running [Kiln OS](https://github.com/djvalic/kiln-os).
When you export or upload a print, it looks at what is loaded in the IFS and
sends each slicer tool to the slot that holds its filament. Nothing needs
installing on the printer.

## What it does

On Kiln OS, slicer tool T0-T3 loads IFS slot 1-4 unless the file says
otherwise. At the G-code post-processing step this plugin:

1. reads the tools the file uses and their filament type and colour;
2. asks the printer what is in each slot (Moonraker,
   `/printer/objects/query?ifs_materials&ifs`, read-only);
3. picks for each tool a slot with filament and the same material (exact
   match first, then the same family such as PLA-CF for PLA), nearest colour
   first, and the tool's own slot on a tie;
4. adds `IFS_MAP_TOOL TOOL=n SLOT=m` lines at the top of the file, with a
   comment per tool:

```
; kiln-orca start (tool map from http://192.168.1.56)
; kiln-orca: T0 PLA #FF0000 -> slot 3 PLA #E60A0A
IFS_MAP_TOOL TOOL=0 SLOT=3
; kiln-orca: T2 PETG #FFFFFF -> slot 1 PETG #FAFAFA
IFS_MAP_TOOL TOOL=2 SLOT=1
; kiln-orca end
```

The map applies to that print only. If a mapped slot is empty when the print
starts, the printer stops with an error instead of printing the wrong
filament.

Slot materials come from the printer's touch screen or
`IFS_SET_MATERIAL SLOT=n TYPE=PLA COLOR=RRGGBB`. A slot without a type is
matched by colour alone.

## Requirements

- OrcaSlicer with the plugin system: nightly builds or a release after 2.4.2.
- A printer on Kiln OS v0.0.4 or later.
- The printer added in OrcaSlicer as an Octo/Klipper physical printer
  (upload), or any export.

## Install

1. In OrcaSlicer: main menu > **Plugins** > **Install local plugin**, then
   pick `kiln_ifs_map.py`.
2. Open **Kiln IFS Tool Map** > **Config** and set `printer_url`, e.g.
   `http://192.168.1.56`.
3. Turn it on for your printer's process preset: in Advanced mode, set
   **Slicing pipeline plugin** (`slicing_pipeline_plugin`) to
   *Kiln IFS Tool Map*.
4. On the first export, OrcaSlicer asks whether the plugin may connect to the
   printer. Answer Yes; OrcaSlicer remembers it.

## Settings

| Key | Default | Meaning |
|---|---|---|
| `printer_url` | `""` | The printer, e.g. `http://192.168.1.56`. If empty, the plugin uses the physical printer's host when OrcaSlicer passes it. |
| `on_mismatch` | `"error"` | `error`: stop the export when a tool's material is in no slot (or no slot has filament). `keep`: leave that tool on its default slot and map the rest. |
| `if_offline` | `"skip"` | `skip`: printer unreachable, file left unchanged. `error`: stop the export. |
| `timeout` | `3` | Seconds to wait for the printer. |

## Related: filament sync

Kiln OS also publishes the slots in Moonraker's `lane_data`. OrcaSlicer's
Moonraker printer agent reads it to fill the filament list (Preferences >
Developer > "Use printer agents instead of print hosts"). If your project's
filaments already come from the printer in slot order, the default map is
right, and this plugin only confirms it.

## Development

```
python3 test_kiln_ifs_map.py                        # offline tests
python3 test_kiln_ifs_map.py http://192.168.1.56    # + a read-only query of a printer
```

OrcaSlicer's plugin API is new and may change; this plugin uses only
`orca.slicing.SlicingPipelineCapabilityBase` at `Step.psGCodePostProcess`.

Licence: GPL-3.0 (LICENSE).
