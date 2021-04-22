def get_type_fields(type):
    entry = {}
    entry["pointer_lvl"] = type.count("*")
    if entry["pointer_lvl"] > 0:
        entry["type"] = type.split("*")[0]
    if type.count("[") > 0:
        entry["is_array"] = True
        split1 = type.split("[")
        if not entry.get("type", False):
            entry["type"] = split1[0]

        entry["dimensions"] = []
        for d in split1[1:]:
            split2 = d.split("]")
            if split2[0] != "":
                entry["dimensions"] += [{"value": split2[0], "type": "int"}]
            else:
                #May need to fix later
                entry["dimensions"] +=["variable"]
    else:
        entry["is_array"] = False
        if not entry.get("type", False):
            entry["type"] = type
    return entry

def get_flookup_type(p):
    final_type = p["type"] + "*" * p.get("pointer_lvl", 0)
    if p.get("is_array", False):
        for i, d in enumerate(p["dimensions"]):
            if d == "variable":
                final_type += "*"
                return final_type
            elif type(d) is str:
                final_type += f"[{d}]"
            else:
                final_type += f"[{d['value']}]"
    return final_type
