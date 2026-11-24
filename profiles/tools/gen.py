# Generate draft Kiln OS OrcaSlicer profiles (machine, process, filament).
# Usage: python3 -I gen.py OUTDIR
import json, math, os, sys

OUT = sys.argv[1]
VERSION = "2.4.0.0"          # import needs a parseable "version" (PresetBundle::import_json_presets)
NOZZLES = ["0.2", "0.25", "0.4", "0.6", "0.8", "1.0"]

def mname(n):
    return f"AD5X {n} nozzle (Kiln)"

# Kiln machine G-code, exactly as docs/orcaslicer.md (and the current orca/*.json)
GCODE = {
    "machine_start_gcode": "SAVE_VARIABLE VARIABLE=use_trash_on_print VALUE={if enable_prime_tower}0{else}1{endif}\nPRINT_START BED=[bed_temperature_initial_layer_single] EXTRUDER=[nozzle_temperature_initial_layer] TOOL=[initial_tool]\nSET_PRINT_STATS_INFO TOTAL_LAYER=[total_layer_count]",
    "machine_end_gcode": "PRINT_END",
    "before_layer_change_gcode": ";BEFORE_LAYER_CHANGE\n;[layer_z]\nG92 E0",
    "layer_change_gcode": ";AFTER_LAYER_CHANGE\n;[layer_z]\nSET_PRINT_STATS_INFO CURRENT_LAYER={layer_num + 1}",
    "change_filament_gcode": "T[next_extruder]",
    "machine_pause_gcode": "PAUSE",
    "time_lapse_gcode": "",
    "change_extrusion_role_gcode": "",
    "printing_by_object_gcode": "",
    "template_custom_gcode": "",
}

# per nozzle: retraction length, z-hop, min/max layer height
NZ = {
    "0.2":  dict(retract="1.0", zhop="0.2", minl="0.04", maxl="0.14"),
    "0.25": dict(retract="1.0", zhop="0.3", minl="0.06", maxl="0.18"),
    "0.4":  dict(retract="1.4", zhop="0.4", minl="0.08", maxl="0.28"),
    "0.6":  dict(retract="1.4", zhop="0.4", minl="0.15", maxl="0.42"),
    "0.8":  dict(retract="1.5", zhop="0.4", minl="0.20", maxl="0.56"),
    "1.0":  dict(retract="1.5", zhop="0.4", minl="0.25", maxl="0.70"),
}

def two(v):
    return [str(v), str(v)]

def machine(n):
    z = NZ[n]
    std = {"0.2": "0.10mm Standard", "0.25": "0.12mm Standard", "0.4": "0.20mm Standard",
           "0.6": "0.30mm Standard", "0.8": "0.40mm Standard", "1.0": "0.50mm Standard"}[n]
    d = {
        "type": "machine",
        "name": mname(n),
        "from": "User",
        "instantiation": "true",
        "inherits": "",
        "version": VERSION,
        "printer_settings_id": mname(n),
        "printer_model": "Flashforge AD5X",
        "printer_variant": n,
        "printer_technology": "FFF",
        "nozzle_diameter": [n],
        "gcode_flavor": "klipper",
        "printable_area": ["0x0", "220x0", "220x220", "0x220"],
        "printable_height": "220",
        "extruder_clearance_radius": "58",
        "extruder_clearance_height_to_rod": "26",
        "extruder_clearance_height_to_lid": "130",
        "extruder_clearance_dist_to_rod": "40",
        "default_print_profile": f"{std} @Kiln AD5X {n}",
        "default_filament_profile": ["AD5X PLA"],
        # machine limits: [printer] in klipper/ad5x.cfg (max_velocity 600, max_accel 20000,
        # square_corner_velocity 25). Orca 2.5 uses jerk X/Y as Klipper's SCV in its time estimate.
        "machine_max_speed_x": two(600), "machine_max_speed_y": two(600),
        "machine_max_speed_z": two(20), "machine_max_speed_e": ["35", "30"],
        "machine_max_acceleration_x": two(20000), "machine_max_acceleration_y": two(20000),
        "machine_max_acceleration_z": two(500), "machine_max_acceleration_e": two(5000),
        "machine_max_acceleration_extruding": two(20000),
        "machine_max_acceleration_retracting": two(5000),
        "machine_max_acceleration_travel": two(20000),
        "machine_max_jerk_x": two(25), "machine_max_jerk_y": two(25),
        "machine_max_jerk_z": two(3), "machine_max_jerk_e": two(2.5),
        "machine_max_junction_deviation": two(0.01),
        "min_layer_height": [z["minl"]],
        "max_layer_height": [z["maxl"]],
        # retraction
        "retraction_length": [z["retract"]],
        "retraction_speed": ["35"],
        "deretraction_speed": ["35"],
        "retraction_minimum_travel": ["1"],
        "retract_restart_extra": ["0"],
        "retract_when_changing_layer": ["1"],
        "wipe": ["0"],
        "z_hop": [z["zhop"]],
        "z_hop_types": ["Normal Lift"],
        "retract_lift_enforce": ["All Surfaces"],
        # Tool change: the printer's swap ends with the new filament 3 mm back
        # (G1 E-3 after the flush, purge_gcode in klipper/ifs.cfg). OrcaSlicer
        # un-retracts what it retracted before the T command, so 3 mm here
        # puts the new filament back at the nozzle tip. Needs a printer test.
        "retract_length_toolchange": ["3"],
        "retract_restart_extra_toolchange": ["0"],
        "use_firmware_retraction": "0",
        "use_relative_e_distances": "1",
        # multi-material: the IFS swaps and purges; no tower, no ramming
        "single_extruder_multi_material": "1",
        "manual_filament_change": "0",
        "purge_in_prime_tower": "0",
        "enable_filament_ramming": "0",
        "cooling_tube_length": "0",
        "cooling_tube_retraction": "0",
        "parking_pos_retraction": "0",
        "extra_loading_move": "0",
        "machine_load_filament_time": "39",
        "machine_unload_filament_time": "39",
        "machine_tool_change_time": "0",
        "auxiliary_fan": "0",
        "support_multi_bed_types": "0",
        "thumbnails": "48x48/PNG,300x300/PNG",
        "printer_notes": "Kiln OS (Klipper) on the Flashforge AD5X. Machine G-code from docs/orcaslicer.md.",
    }
    d.update(GCODE)
    return d

# ---------------------------------------------------------------- process
# (layer, label) per nozzle
LAYERS = {
    "0.2":  [(0.06, "Fine"), (0.10, "Standard")],
    "0.25": [(0.08, "Fine"), (0.12, "Standard")],
    "0.4":  [(0.12, "Fine"), (0.16, "Optimal"), (0.20, "Standard"), (0.24, "Draft")],
    "0.6":  [(0.18, "Fine"), (0.30, "Standard"), (0.42, "Draft")],
    "0.8":  [(0.24, "Fine"), (0.40, "Standard"), (0.56, "Draft")],
    "1.0":  [(0.30, "Fine"), (0.50, "Standard"), (0.70, "Draft")],
}
FIRST = {"0.2": 0.12, "0.25": 0.15, "0.4": 0.20, "0.6": 0.30, "0.8": 0.40, "1.0": 0.50}
# speeds mm/s: outer, inner, sparse, solid, top, gap, first, first_infill, small_perim
SPEED = {
    "0.2":  (50, 80, 100, 80, 60, 50, 20, 30),
    "0.25": (60, 100, 120, 100, 80, 60, 25, 40),
    "0.4":  (120, 180, 220, 180, 100, 100, 40, 60),
    "0.6":  (100, 150, 180, 150, 80, 80, 35, 50),
    "0.8":  (80, 120, 140, 120, 60, 60, 30, 45),
    "1.0":  (60, 100, 120, 100, 50, 50, 25, 40),
}
WALLS = {"0.2": 3, "0.25": 3, "0.4": 3, "0.6": 2, "0.8": 2, "1.0": 2}

def r2(x):
    return f"{x:.2f}".rstrip("0").rstrip(".") if x != int(x) else str(int(x))

def process(n, lh, label):
    d_n = float(n)
    sp = SPEED[n]
    outer, inner, sparse, solid, top, gap, first, first_inf = sp
    if label == "Fine":
        outer, top = int(outer * 0.8), int(top * 0.8)
    small = d_n <= 0.25
    top_t = 0.8 if small else 1.0
    bot_t = 0.5 if small else 0.6
    name = f"{lh:.2f}mm {label} @Kiln AD5X {n}"
    w = lambda f: r2(round(d_n * f, 2))
    d = {
        "type": "process",
        "name": name,
        "from": "User",
        "instantiation": "true",
        "inherits": "",
        "version": VERSION,
        "print_settings_id": name,
        "compatible_printers": [mname(n)],
        "compatible_printers_condition": "",
        "layer_height": r2(lh),
        "initial_layer_print_height": r2(FIRST[n]),
        "line_width": w(1.05),
        "outer_wall_line_width": w(1.05),
        "inner_wall_line_width": w(1.125),
        "sparse_infill_line_width": w(1.125),
        "internal_solid_infill_line_width": w(1.05),
        "top_surface_line_width": w(1.0),
        "initial_layer_line_width": w(1.25),
        "support_line_width": w(1.05),
        "wall_loops": str(WALLS[n]),
        "wall_generator": "arachne" if small else "classic",
        "wall_sequence": "inner wall/outer wall",
        "seam_position": "aligned",
        "top_shell_layers": str(max(3, math.ceil(top_t / lh - 1e-6))),
        "top_shell_thickness": r2(top_t),
        "bottom_shell_layers": str(max(3, math.ceil(bot_t / lh - 1e-6))),
        "bottom_shell_thickness": r2(bot_t),
        "top_surface_pattern": "monotonicline",
        "bottom_surface_pattern": "monotonic",
        "sparse_infill_density": "15%",
        "sparse_infill_pattern": "crosshatch",
        "ensure_vertical_shell_thickness": "ensure_all",
        # speeds (the filament's max volumetric speed caps the fast ones)
        "outer_wall_speed": str(outer),
        "inner_wall_speed": str(inner),
        "sparse_infill_speed": str(sparse),
        "internal_solid_infill_speed": str(solid),
        "top_surface_speed": str(top),
        "gap_infill_speed": str(gap),
        "initial_layer_speed": str(first),
        "initial_layer_infill_speed": str(first_inf),
        "small_perimeter_speed": "50%",
        "bridge_speed": "25",
        "internal_bridge_speed": "50",
        "enable_overhang_speed": "1",
        "overhang_1_4_speed": "0",
        "overhang_2_4_speed": "40",
        "overhang_3_4_speed": "20",
        "overhang_4_4_speed": "10",
        "support_speed": str(min(150, inner)),
        "support_interface_speed": str(min(80, outer)),
        "travel_speed": "400",
        "skirt_speed": "50",
        # accelerations: kept at or under ~7000 mm/s2 (MZV ~49 Hz on Y, measured on one printer)
        "default_acceleration": "5000",
        "outer_wall_acceleration": "2000" if small else "3000",
        "inner_wall_acceleration": "4000" if small else "5000",
        "top_surface_acceleration": "2000" if small else "2500",
        "sparse_infill_acceleration": "7000",
        "internal_solid_infill_acceleration": "5000",
        "bridge_acceleration": "50%",
        "initial_layer_acceleration": "500",
        "travel_acceleration": "7000",
        # keep printer.cfg's minimum_cruise_ratio (0.75); no per-feature jerk (SCV stays 25)
        "accel_to_decel_enable": "0",
        "default_jerk": "0",
        # multi-colour: the IFS purges at the box, no tower
        "enable_prime_tower": "0",
        "flush_into_infill": "0",
        "flush_into_objects": "0",
        "flush_into_support": "0",
        # Klipper: object labels for Kiln's mesh of the print area and for exclude-object;
        # 0.2 mm outline tolerance as upstream Flashforge (fewer points, no "Timer too close")
        "gcode_label_objects": "1",
        "exclude_object": "1",
        "exclude_object_tolerance": "0.2",
        "enable_arc_fitting": "0",
        "print_sequence": "by layer",
        "skirt_loops": "0",
        "brim_type": "auto_brim",
        "brim_width": "5",
        "brim_object_gap": "0.1",
        "enable_support": "0",
        "support_type": "tree(auto)",
        "ironing_type": "no ironing",
    }
    return name, d

# ---------------------------------------------------------------- filament
ALL = [mname(n) for n in NOZZLES]
NO_SMALL = [mname(n) for n in NOZZLES if float(n) >= 0.4]

def plates(t, t0):
    out = {}
    for k in ["hot_plate_temp", "textured_plate_temp", "eng_plate_temp", "cool_plate_temp",
              "textured_cool_plate_temp", "supertack_plate_temp"]:
        out[k] = [str(t)]
        out[k + "_initial_layer"] = [str(t0)]
    return out

def filament(name, ftype, dens, cost, maxvol, noz, noz0, rng, bed, bed0, fan, compat,
             notes, vit, hrc=0, extra=None):
    fmin, fmax, nofan, cool_t, slow_t, slow_min, ovh = fan
    d = {
        "type": "filament",
        "name": name,
        "from": "User",
        "instantiation": "true",
        "inherits": "",
        "version": VERSION,
        "filament_settings_id": [name],
        "filament_type": [ftype],
        "filament_vendor": ["Generic"],
        "filament_diameter": ["1.75"],
        "filament_density": [dens],
        "filament_cost": [cost],
        "filament_flow_ratio": ["0.98"],
        "filament_max_volumetric_speed": [maxvol],
        "nozzle_temperature": [str(noz)],
        "nozzle_temperature_initial_layer": [str(noz0)],
        "nozzle_temperature_range_low": [str(rng[0])],
        "nozzle_temperature_range_high": [str(rng[1])],
        "temperature_vitrification": [str(vit)],
        # the printer's [extruder] pressure_advance (or local.cfg) applies;
        # turn on per filament after OrcaSlicer's PA calibration
        "enable_pressure_advance": ["0"],
        "pressure_advance": ["0.04"],
        "fan_min_speed": [str(fmin)],
        "fan_max_speed": [str(fmax)],
        "close_fan_the_first_x_layers": [str(nofan)],
        "fan_cooling_layer_time": [str(cool_t)],
        "slow_down_for_layer_cooling": ["1"],
        "slow_down_layer_time": [str(slow_t)],
        "slow_down_min_speed": [str(slow_min)],
        "overhang_fan_speed": [str(ovh)],
        "overhang_fan_threshold": ["50%"],
        "additional_cooling_fan_speed": ["0"],
        "required_nozzle_HRC": [str(hrc)],
        "filament_notes": [notes],
        "compatible_printers": compat,
        "compatible_printers_condition": "",
    }
    d.update(plates(bed, bed0))
    if extra:
        d.update(extra)
    return d

HARD = ("Carbon fibre filled: abrasive. Use a hardened steel (or other wear-resistant) nozzle; "
        "it wears a brass or stainless nozzle out quickly. No 0.2 / 0.25 mm nozzle (clogs). ")
FILAMENTS = [
    filament("AD5X PLA", "PLA", "1.24", "20", "12", 220, 220, (190, 240), 50, 55,
             (100, 100, 1, 100, 6, 20, 100), ALL,
             "Starting point; set your spool's temperatures. 220 / 50 (55 first layer), as Flashforge's Generic PLA.", 60),
    filament("AD5X Silk PLA", "PLA", "1.24", "25", "8", 230, 230, (200, 240), 60, 60,
             (100, 100, 1, 100, 8, 20, 100), ALL,
             "Silk PLA. OrcaSlicer has no SILK filament type, so the type is PLA "
             "(the IFS slot type SILK belongs to the PLA family). Slower flow keeps the shine.", 60,
             extra={"filament_flow_ratio": ["0.96"]}),
    filament("AD5X PLA-CF", "PLA-CF", "1.29", "30", "10", 225, 225, (200, 240), 60, 60,
             (100, 100, 1, 100, 8, 20, 100), NO_SMALL, HARD, 60, hrc=40),
    filament("AD5X PETG", "PETG", "1.27", "20", "10", 240, 240, (220, 260), 80, 80,
             (30, 60, 2, 30, 8, 20, 90), ALL,
             "Starting point; set your spool's temperatures. Cooler bed (70) on smooth PEI if parts stick too well.", 70),
    filament("AD5X PETG-CF", "PETG-CF", "1.30", "35", "10", 245, 245, (230, 260), 80, 80,
             (20, 50, 2, 30, 8, 20, 90), NO_SMALL, HARD, 70, hrc=40),
    filament("AD5X ABS", "ABS", "1.04", "20", "12", 255, 260, (240, 270), 100, 100,
             (0, 20, 3, 30, 8, 20, 60), ALL,
             "The AD5X is open (no enclosure, no chamber heater): ABS warps and splits on larger "
             "parts and gives off fumes. Small parts, brim, no drafts, a ventilated room; a cover "
             "box over the printer helps. Part fan mostly off.", 100,
             extra={"chamber_temperature": ["0"], "activate_chamber_temp_control": ["0"]}),
    filament("AD5X TPU", "TPU", "1.21", "30", "3.6", 225, 225, (210, 240), 40, 40,
             (100, 100, 1, 30, 8, 10, 100), NO_SMALL,
             "TPU 95A or harder. Softer TPU does not feed through the IFS. Slow: 3.6 mm3/s.", 60),
]

def write(sub, name, d):
    p = os.path.join(OUT, sub)
    os.makedirs(p, exist_ok=True)
    with open(os.path.join(p, name + ".json"), "w") as f:
        json.dump(d, f, indent=4, ensure_ascii=False)
        f.write("\n")

for n in NOZZLES:
    write("machine", mname(n), machine(n))
    for lh, label in LAYERS[n]:
        name, d = process(n, lh, label)
        write("process", name, d)
for d in FILAMENTS:
    write("filament", d["name"], d)
print("ok")
