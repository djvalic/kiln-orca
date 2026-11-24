# Kiln OS profiles for OrcaSlicer (Flashforge AD5X)

Printer, process and filament profiles for an AD5X running
[Kiln OS](https://github.com/djvalic/kiln-os), made for **OrcaSlicer 2.5**.

## Import

Download `kiln-ad5x-orcaslicer-profiles.zip` from the
[latest release](https://github.com/djvalic/kiln-orca/releases/latest) (or the
JSON files below), then in OrcaSlicer: **File > Import > Import Configs...**
and pick the zip. Then choose the printer for your nozzle, for example
**AD5X 0.4 nozzle (Kiln)**; its process and filament profiles appear with it.

Set the same nozzle on the printer: touch screen Settings > Nozzle Size (or
`SET_NOZZLE_SIZE SIZE=0.6`).

## What's in it

| Folder | Profiles |
|---|---|
| `machine/` | `AD5X 0.2 / 0.25 / 0.4 / 0.6 / 0.8 / 1.0 nozzle (Kiln)`: build area, limits, retraction, and Kiln's G-code (start `PRINT_START`, end `PRINT_END`, colour change `T[next_extruder]`, layer lines, the purge mode from the prime tower switch) |
| `process/` | Fine / Standard (and Optimal, Draft where the nozzle allows) per nozzle, e.g. `0.20mm Standard @Kiln AD5X 0.4`: accelerations at most 7000 mm/s², prime tower off, object labels on (Kiln meshes only the print area) |
| `filament/` | One per IFS slot material: `AD5X PLA`, `AD5X Silk PLA`, `AD5X PLA-CF`, `AD5X PETG`, `AD5X PETG-CF`, `AD5X ABS`, `AD5X TPU`. Starting points; set your spool's values |

Things to know:

- **Colour changes and waste.** The prime tower is off: the printer purges at
  each colour change into its purge box, so OrcaSlicer's flush volumes don't
  change anything. **With the prime tower on** (Others > Prime tower, in the
  process), the start G-code tells the printer to only prime the nozzle at
  each change (`use_trash_on_print 0`, Kiln's nopoop plugin, on by default),
  and the tower does the purging; "Flush into objects' infill" and "Flush
  into objects" then put part of it into the print. Tower and flush settings
  are OrcaSlicer's; they need a print test on your printer. To purge less, measure what your printer needs:
  `IFS_PURGE_TEST FROM=<dark slot> TO=<light slot>`, then
  `IFS_PURGE_RESULT DOT=<first clean dot>`. Colour painted on a top surface
  is carried down through the top shells, and each of those layers changes
  colour.
- **Tool-change retraction** is 3 mm out before the colour change and the same
  3 mm back after it. The printer pulls the new filament back 3 mm after its
  purge, so this puts it back exactly. Needs a print test on every nozzle
  but the 0.6.
- **PLA** uses Flashforge's Generic PLA temperatures (220 °C, bed 55 °C first
  layer, then 50 °C).
- **CF filaments** need a hardened (wear-resistant) nozzle and aren't offered
  for 0.2 / 0.25 mm nozzles; neither is TPU.
- **ABS:** the AD5X has no enclosure or chamber heater. Expect warping on
  bigger parts, and ventilate.
- Retraction has only been printed on a 0.6 mm nozzle; on other sizes, check
  it with a test print.

## Regenerate

The profiles are generated, not edited by hand:

```
python3 -I tools/gen.py out            # writes out/machine, out/process, out/filament
python3 -I tools/validate.py <OrcaSlicer src/libslic3r dir> out
```

`validate.py` checks every key against OrcaSlicer's own `PrintConfig.cpp`
and `Preset.cpp`, so a key that a new OrcaSlicer renamed or dropped shows up
before release.
