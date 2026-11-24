# Validate generated profiles against OrcaSlicer source key lists.  usage: validate.py SRC_DIR PROFILE_DIR...
import json, os, sys, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orcadefs
defs, lists = orcadefs.load(sys.argv[1])
META = {"type", "name", "from", "instantiation", "inherits", "version", "setting_id", "filament_id", "description"}
IDKEY = {"machine": "printer_settings_id", "process": "print_settings_id", "filament": "filament_settings_id"}
VEC = lambda t: t.endswith("s") and t not in ("coBools_",) and t not in ("coPoints",) or t == "coPoints"
errs = 0
for root in sys.argv[2:]:
    for f in sorted(glob.glob(os.path.join(root, "**", "*.json"), recursive=True)):
        d = json.load(open(f)); kind = d.get("type")
        bad = []
        if "version" not in d: bad.append("no version (import will skip it)")
        if IDKEY.get(kind) not in d: bad.append("no " + str(IDKEY.get(kind)))
        if d.get("name") + ".json" != os.path.basename(f): bad.append("file name != name")
        for k, v in d.items():
            if k in META or k == IDKEY.get(kind): continue
            if k not in defs: bad.append(f"unknown key {k}"); continue
            if k not in lists.get(kind, set()): bad.append(f"key {k} not a {kind} option (would be removed)")
            typ, enums, _ = defs[k]
            vec = typ.endswith("s") or typ == "coPoints"
            if isinstance(v, list) and not vec: bad.append(f"{k}: {typ} but value {'list' if isinstance(v, list) else 'scalar'}")
            vals = v if isinstance(v, list) else [v]
            if enums and typ.startswith("coEnum"):
                for x in vals:
                    if x not in enums and not (k == 'enable_arc_fitting' and x in ('0', '1')): bad.append(f"{k}: '{x}' not in {enums}")
            if typ.startswith(("coFloat", "coInt", "coPercent")) and "OrPercent" not in typ:
                for x in vals:
                    try: float(str(x).rstrip("%"))
                    except ValueError: bad.append(f"{k}: not numeric {x}")
            if typ.startswith("coBool"):
                for x in vals:
                    if str(x) not in ("0", "1", "true", "false"): bad.append(f"{k}: not bool {x}")
        if bad:
            errs += 1; print("FAIL", os.path.relpath(f, root)); [print("   ", b) for b in bad]
        else:
            print("ok  ", os.path.relpath(f, root))
print("errors:", errs)
