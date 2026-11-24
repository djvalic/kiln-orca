# Parse OrcaSlicer PrintConfig.cpp / Preset.cpp key lists (static text parse).
import re
def load(src_dir):
    pc = open(src_dir + "/PrintConfig.cpp").read()
    pr = open(src_dir + "/Preset.cpp").read()
    defs = {}
    for m in re.finditer(r'this->add(?:_nullable)?\("([A-Za-z0-9_]+)",\s*(co\w+)\)', pc):
        key, typ = m.group(1), m.group(2)
        start = m.end()
        nxt = re.search(r'this->add(?:_nullable)?\("', pc[start:])
        body = pc[start:start + (nxt.start() if nxt else 4000)]
        enums = re.findall(r'enum_values\.push_back\("([^"]*)"\)', body)
        dflt = re.search(r'set_default_value\((.*?)\);', body)
        defs.setdefault(key, (typ, enums, dflt.group(1) if dflt else None))
    for kind in ("speed", "acceleration", "jerk"):
        for ax in "xyze":
            defs.setdefault(f"machine_max_{kind}_{ax}", ("coFloats", [], None))
    def strlist(name):
        m = re.search(r'static std::vector<std::string> ' + name + r'\s*\{(.*?)\n\s*\};', pr, re.S)
        body = re.sub(r'//[^\n]*', '', m.group(1))
        body = re.sub(r'/\*.*?\*/', '', body, flags=re.S)
        return set(re.findall(r'"([^"]+)"', body))
    m = re.search(r'm_extruder_option_keys = \{(.*?)\};', pc, re.S)
    ext = set(re.findall(r'"([^"]+)"', m.group(1)))
    m = re.search(r'm_filament_option_keys = \{(.*?)\};', pc, re.S)
    fil_ext = set(re.findall(r'"([^"]+)"', m.group(1)))
    lists = {
        "process": strlist("s_Preset_print_options"),
        "filament": strlist("s_Preset_filament_options"),
        "machine": strlist("s_Preset_printer_options") | strlist("s_Preset_machine_limits_options") | ext,
    }
    return defs, lists
