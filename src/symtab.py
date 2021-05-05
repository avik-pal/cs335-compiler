from typing import Union, List, Tuple
import csv
import os

DATATYPE2SIZE = {
    "VOID": 0,
    "CHAR": 1,
    "SIGNED CHAR": 1,
    "UNSIGNED CHAR": 1,
    "SHORT": 2,
    "SHORT INT": 2,
    "SIGNED SHORT": 2,
    "SIGNED SHORT INT": 2,
    "UNSIGNED SHORT": 2,
    "UNSIGNED SHORT INT": 2,
    "INT": 4,
    "SIGNED INT": 4,
    "UNSIGNED INT": 4,
    "SIGNED": 4,
    "UNSIGNED": 4,
    "LONG": 8,
    "LONG INT": 8,
    "SIGNED LONG INT": 8,
    "SIGNED LONG": 8,
    "UNSIGNED LONG": 8,
    "UNSIGNED LONG INT": 8,
    "LONG LONG": 8,
    "LONG LONG INT": 8,
    "SIGNED LONG LONG": 8,
    "SIGNED LONG LONG INT": 8,
    "UNSIGNED LONG LONG": 8,
    "UNSIGNED LONG LONG INT": 8,
    "FLOAT": 4,
    "DOUBLE": 8,
    "LONG DOUBLE": 16,
}


CHARACTER_TYPES = ["CHAR", "SIGNED CHAR", "UNSIGNED CHAR"]

INTEGER_TYPES = [
    "SHORT",
    "SHORT INT",
    "SIGNED SHORT",
    "SIGNED SHORT INT",
    "UNSIGNED SHORT",
    "UNSIGNED SHORT INT",
    "INT",
    "SIGNED INT",
    "UNSIGNED INT",
    "SIGNED",
    "UNSIGNED",
    "LONG",
    "LONG INT",
    "SIGNED LONG INT",
    "SIGNED LONG",
    "UNSIGNED LONG",
    "UNSIGNED LONG INT",
    "LONG LONG",
    "LONG LONG INT",
    "SIGNED LONG LONG",
    "SIGNED LONG LONG INT",
    "UNSIGNED LONG LONG",
    "UNSIGNED LONG LONG INT",
]

FLOATING_POINT_TYPES = [
    "FLOAT",
    "DOUBLE",
    "LONG DOUBLE",
]


NUMERIC_TYPES = INTEGER_TYPES + FLOATING_POINT_TYPES

BASIC_TYPES = NUMERIC_TYPES + CHARACTER_TYPES


TABLENUMBER = 0

num_display_invocations = 0


class SymbolTable:
    # kind = 0 for ID
    #        1 for FN
    #        2 for ST
    #        3 for CL
    #        4 for EN
    #        5 for UN
    def __init__(self, parent=None, function_scope=None) -> None:
        global TABLENUMBER
        self.func_scope = function_scope if TABLENUMBER != 0 else "GLOBAL"
        self._symtab_variables = dict()
        self._symtab_functions = dict()
        self._function_names = dict()
        self._symtab_structs = dict()
        self._symtab_typedefs = dict()
        self._symtab_unions = dict()
        self._symtab_classes = dict()
        self._symtab_enums = dict()
        self._custom_types = dict()
        self._symtab_labels = dict()
        self._paramtab = []
        self.current_offset = 0
        self.parent = parent
        if self.parent is not None:
            self.parent.children.append(self)
        self.children = []
        self.table_number = TABLENUMBER
        TABLENUMBER += 1

        if parent is None:
            self.table_name = "GLOBAL"
        else:
            self.table_name = f"BLOCK_{self.table_number}"

    @staticmethod
    def _get_proper_name(entry: dict, kind: int = 0):
        if kind != 1:
            return entry["name"]
        else:
            # For function and its disambiguation
            return entry["name"] + "(" + ",".join(entry["parameter types"]) + ")"

    def update_value(self, name: str, value) -> None:
        entry = self.lookup(name)
        entry["value"] = value

    def insert(
        self, entry: dict, kind: int = 0, fname=None, param: bool = False
    ) -> Tuple[bool, Union[dict, List[dict]]]:
        # Variables (ID) -> {"name", "type", "value", "is_array", "dimensions", "pointer_lvl"}
        # Functions (FN) -> {"name", "return type", "parameter types"}
        # Structs (ST)   -> {"name", "alt name" (via typedef), "field names", "field types"}
        # Classes (CL)   -> {"name", ... TBD}
        # Enums (EN)     -> {"name", "field names", "field values"}
        # Unions (UN)    -> {"name", "alt name" (via typedef), "field names", "field types"}
        # Labels (LB)    -> {"name"}
        global DATATYPE2SIZE

        name = self._get_proper_name(entry, kind)
        prev_entry = self.lookup_current_table(name, False, entry.get("alt name", None), kind)
        if prev_entry is None and kind == 0 and fname is not None:
            prev_entry = self.lookup(name + ".static." + fname)
        # if entry['name'] == 'arr':
        #     print(f"Symtab {entry} {prev_entry}")
        if prev_entry is None:
            entry["kind"] = kind
            entry["pointer_lvl"] = entry.get("pointer_lvl", 0)
            if kind == 0:
                if not self.check_type(entry["type"]):
                    raise Exception(f"{entry['type']} is not a valid data type")
                t = self.lookup_type(entry["type"])
                entry["size"] = compute_storage_size(entry, t)
                entry["value"] = entry.get("value", get_default_value(entry["type"]))
                entry["offset"] = self.current_offset + entry["size"]
                self.current_offset = entry["offset"]

                if entry["is_array"]:
                    dims = entry["dimensions"]
                    ndims = []
                    for dim in dims:
                        if dim == "variable":
                            continue
                        if isinstance(dim, str):
                            _l = self.lookup(dim)
                            if _l["type"] != "int":
                                raise Exception
                            ndims.append(dim)
                        else:
                            if dim["type"] != "int":
                                raise Exception
                            ndims.append(dim["value"])
                    entry["dimensions"] = ndims

                entry["table name"] = self.table_name

                self._symtab_variables[name] = entry
                if param:
                    self._paramtab.append(name)

            elif kind == 1:
                # Function
                entry["local scope"] = None
                self._symtab_functions[name] = entry
                self._symtab_functions[name]["name resolution"] = name
                ret_type = entry["return type"]
                _s = compute_storage_size({"type": ret_type}, self.lookup_type(ret_type))
                entry["return type size"] = _s
                param_size = 0
                for p in entry["parameter types"]:
                    t = self.lookup_type(p)
                    _s = compute_storage_size({"type": p}, t)
                    param_size += _s
                entry["param_size"] = param_size
                if entry["name"] in self._function_names:
                    self._function_names[entry["name"]].append(name)
                else:
                    self._function_names[entry["name"]] = [name]

            elif kind == 2:
                # Struct
                # TODO: Handle cyclic referencing for structs
                if entry["alt name"] is None:
                    entry["alt name"] = get_tmp_label()
                # symtab_structs just stores the translated name
                if len(set(entry["field names"])) != len(entry["field names"]):
                    raise Exception("Non Unique Field Names detected")
                self._symtab_structs[name] = entry["alt name"]
                self._symtab_typedefs[entry["alt name"]] = entry
                self._custom_types[f"struct {name}"] = entry
                self._custom_types[entry["alt name"]] = entry

            elif kind == 3:
                # Class
                # TODO:
                self._symtab_classes[name] = entry
                self._custom_types[name] = entry

            elif kind == 4:
                # Enum
                entry["field2var"] = dict()
                # Insert all the fields as variables
                for i, var in enumerate(entry["field names"]):
                    entry["field2var"][var] = {}
                self._symtab_enums[name] = entry
                self._custom_types[f"enum {name}"] = entry

                for i, var in enumerate(entry["field names"]):
                    _, nentry = self.insert(
                        {
                            "name": var,
                            "type": f"enum {name}",
                            "is_array": False,
                            "dimensions": [],
                            "value": entry["field values"][i],
                        }
                    )
                    entry["field2var"][var].update(nentry)

            elif kind == 5:
                # Union
                if entry["alt name"] is None:
                    entry["alt name"] = get_tmp_label()
                if len(set(entry["field names"])) != len(entry["field names"]):
                    raise Exception("Non Unique Field Names detected")
                # symtab_structs just stores the translated name
                self._symtab_unions[name] = entry["alt name"]
                self._symtab_typedefs[entry["alt name"]] = entry
                self._custom_types[f"union {name}"] = entry
                self._custom_types[entry["alt name"]] = entry

            elif kind == 6:
                self._symtab_labels[name] = entry

            else:
                raise Exception(f"{kind} is not a valid kind of identifier")

            return True, entry
        return False, prev_entry
        # After Storage
        # Variables (ID) -> {"name", "type", "value", "is_array", "dimensions", "kind", "size", "offset", "pointer_lvl"}
        # Functions (FN) -> {"name", "return type", "parameter types", "kind", "local scope"}

    def _check_type_in_current_table(self, typename: str) -> bool:
        global DATATYPE2SIZE
        is_basic_type = typename.upper() in DATATYPE2SIZE if not isinstance(typename, (list, tuple)) else False
        return typename in self._custom_types if not is_basic_type else is_basic_type

    def check_type(self, typename: str) -> bool:
        is_type = self._check_type_in_current_table(typename)
        return self.parent.check_type(typename) if self.parent is not None and not is_type else is_type

    def _translate_type(self, typename: str) -> Union[None, str]:
        if typename.startswith("struct"):
            return self._symtab_structs.get(typename[7:], None)
        if typename.startswith("union"):
            return self._symtab_unions.get(typename[6:], None)
        return None

    def translate_type(self, typename: str) -> Union[None, str]:
        # Takes struct ___ / union ___ and converts it to a proper label
        tname = self._translate_type(typename)
        return self.parent.translate_type(typename) if self.parent is not None and tname is None else tname

    def _search_for_label(self, symname: str) -> Union[None, dict]:
        return self._symtab_labels.get(symname, None)

    def _search_for_variable(self, symname: str) -> Union[None, dict]:
        return self._symtab_variables.get(symname, None)

    def _search_for_function(self, symname: str) -> Union[None, List[dict], dict]:
        if "(" in symname:
            return self._symtab_functions.get(symname, None)
        else:
            # If we match with a function base name return list of all
            # the available functions
            funcs = self._function_names.get(symname, None)
            return [self._symtab_functions[func] for func in funcs] if funcs is not None else None

    def _search_for_struct(self, symname: str, alt_name: Union[str, None]) -> Union[None, dict]:
        if f"struct {symname}" in self._symtab_structs:
            return self._symtab_typedefs[self._symtab_structs[f"struct {symname}"]]
        if symname in self._symtab_typedefs:
            return self._symtab_typedefs[symname]
        if alt_name in self._symtab_typedefs:
            return self._symtab_typedefs[alt_name]
        return None

    def _search_for_class(self, symname: str) -> Union[None, dict]:
        return self._symtab_classes.get(symname, None)

    def _search_for_enum(self, symname: str) -> Union[None, dict]:
        return self._symtab_enums.get(symname, None)

    def _search_for_union(self, symname: str, alt_name: Union[str, None]) -> Union[None, dict]:
        if f"union {symname}" in self._symtab_unions:
            return self._symtab_typedefs[self._symtab_unions[f"union {symname}"]]
        if symname in self._symtab_typedefs:
            return self._symtab.typedefs[symname]
        if alt_name in self._symtab_typedefs:
            return self._symtab.typedefs[alt_name]
        return None

    def lookup_current_table(
        self,
        symname: str,
        paramtab_check: bool = True,
        alt_name: Union[str, None] = None,
        kind: int = -1,
    ) -> Union[None, list, dict]:
        res = self._search_for_variable(symname) if kind <= 0 else None
        res = self._search_for_function(symname) if res is None and kind <= 1 else res
        res = self._search_for_struct(symname, alt_name) if res is None and kind <= 2 else res
        res = self._search_for_class(symname) if res is None and kind <= 3 else res
        res = self._search_for_enum(symname) if res is None and kind <= 4 else res
        res = self._search_for_union(symname, alt_name) if res is None and kind <= 5 else res
        res = self._search_for_label(symname) if res is None and kind <= 6 else res
        return self.lookup_parameter(symname) if res is None and paramtab_check else res

    def lookup_parameter(self, paramname: str) -> Union[None, list, dict]:
        res = None
        # for table in self._paramtab:
        # res = table._search_for_variable(paramname)
        # if res is not None:
        # break
        return res

    def _lookup_type(self, typename: str) -> Union[dict, None]:
        return self._custom_types.get(typename, None)

    def lookup_type(self, typename: str) -> Union[dict, None]:
        t = self._lookup_type(typename)
        return self.parent.lookup_type(typename) if self.parent is not None and t is None else t

    def lookup(self, symname: str, idx: int = -1, alt_name: Union[str, None] = None) -> Union[None, list, dict]:
        # Check in the current list of symbols
        res = self.lookup_current_table(symname, paramtab_check=(idx == -1), alt_name=alt_name)
        # Check if present in the parent recursively till root node is reached
        res = self.parent.lookup(symname, idx=0, alt_name=alt_name) if res is None and self.parent else res
        # Finally check in the current parameter table
        return self.lookup_parameter(symname) if res is None else res

    def add_function_scope(self, funcname: str, table) -> None:
        if "(" not in funcname:
            raise Exception(f"Supply the disambiguated function name for {funcname}")
        self._symtab_functions[funcname] = SymbolTable

    def display(self) -> None:
        # Simple Pretty Printer
        global num_display_invocations
        print("-" * 100)
        print(f"SYMBOL TABLE: {self.table_name}, TABLE NUMBER: {self.table_number}, FUNCTION SCOPE: {self.func_scope}")
        print("-" * 51)
        print(" " * 20 + " Variables " + " " * 20)
        print("-" * 51)
        for k, v in self._symtab_variables.items():
            if v["name"][: min(2, len(k))] == "__":
                continue
            print(
                f"Name: {k}, Type: {v['type'] + '*' * v['pointer_lvl']}, Size: {v['size']}, Offset: {v['offset']}"
                + ("" if not v["is_array"] else f", Dimensions: {v['dimensions']}")
            )
        print("-" * 51)
        print(" " * 20 + " Functions " + " " * 20)
        print("-" * 51)
        for k, v in self._symtab_functions.items():
            if v["name"][: min(1, len(k))] == "__" or not v["name"][0].isalpha():
                continue
            print(
                f"Name: {v['name']}, Return: {v['return type']}, Parameters: {v['parameter types']}, Name Resolution: {k}"
            )
        print("-" * 100)
        print()

        # printing symbol tables in csv
        if num_display_invocations == 0:
            if os.path.isfile("symtables.csv"):
                os.remove("symtables.csv")

        with open("symtables.csv", mode="a+") as sym_file:
            sym_writer = csv.writer(
                sym_file,
                delimiter=",",
                quotechar='"',
                quoting=csv.QUOTE_MINIMAL,
            )
            if num_display_invocations == 0:
                sym_writer.writerow(
                    [
                        "SYMBOL TABLE",
                        "FUNCTION SCOPE",
                        "VARIABLE/FUNCTION",
                        "NAME",
                        "TYPE",
                        "SIZE",
                        "OFFSET",
                        "DIMENSIONS",
                        "RETURN TYPE",
                        "PARAMETERS",
                        "NAME RESOLUTION",
                    ]
                )
                num_display_invocations += 1
            for k, v in self._symtab_variables.items():
                if v["name"][: min(2, len(k))] == "__":
                    continue

                if not v["is_array"]:
                    sym_writer.writerow(
                        [
                            f"{self.table_name}",
                            f"{self.func_scope}",
                            "Variable",
                            f"{k}",
                            f"{v['type'] + '*' * v['pointer_lvl']}",
                            f"{v['size']}",
                            f"{v['offset']}",
                            "",
                            "",
                            "",
                            "",
                        ]
                    )
                else:
                    sym_writer.writerow(
                        [
                            f"{self.table_name}",
                            f"{self.func_scope}",
                            "Variable",
                            f"{k}",
                            f"{v['type'] + '*' * v['pointer_lvl']}",
                            f"{v['size']}",
                            f"{v['offset']}",
                            f"{v['dimensions']}",
                            "",
                            "",
                            "",
                        ]
                    )

            for k, v in self._symtab_functions.items():
                if v["name"][: min(1, len(k))] == "__" or not v["name"][0].isalpha():
                    continue
                sym_writer.writerow(
                    [
                        f"{self.table_name}",
                        f"{self.func_scope}",
                        "Function",
                        f"{v['name']}",
                        "",
                        "",
                        "",
                        "",
                        f"{v['return type']}",
                        f"{v['parameter types']}",
                        f"{k}",
                    ]
                )


SYMBOL_TABLES = []
GLOBAL_SYMBOL_TABLE = None
SYMTAB_NAME_TO_TABLE = {}
STATIC_VARIABLE_MAPS = {}


def pop_scope() -> SymbolTable:
    global SYMBOL_TABLES
    s = SYMBOL_TABLES.pop()
    # if s.table_name != "GLOBAL":
    # s.display()
    # print(
    #     "[DEBUG INFO]  POP SYMBOL TABLE: ",
    #     s.table_number,
    #     s.table_name,
    # )
    return s


def push_scope(s: SymbolTable) -> None:
    global SYMBOL_TABLES, GLOBAL_SYMBOL_TABLE, SYMTAB_NAME_TO_TABLE
    if len(SYMBOL_TABLES) == 0:
        GLOBAL_SYMBOL_TABLE = s
    SYMBOL_TABLES.append(s)
    SYMTAB_NAME_TO_TABLE[s.table_name] = s
    # print("[DEBUG INFO] PUSH SYMBOL TABLE: ", s.table_number, s.table_name)


def get_tabname_mapping():
    global SYMTAB_NAME_TO_TABLE
    return SYMTAB_NAME_TO_TABLE


def new_scope(parent=None, function_scope=None) -> SymbolTable:
    return SymbolTable(parent, function_scope)


def get_current_symtab() -> Union[None, SymbolTable]:
    global SYMBOL_TABLES
    return None if len(SYMBOL_TABLES) == 0 else SYMBOL_TABLES[-1]


def get_global_symtab():
    global GLOBAL_SYMBOL_TABLE
    return GLOBAL_SYMBOL_TABLE


def compute_offset_size(dsize: int, is_array: bool, dimensions: List[int], entry, typeentry) -> int:
    if not is_array:
        return dsize
    else:
        offset = [DATATYPE2SIZE[entry["type"].upper()]]
        for i, d in enumerate(reversed(entry["dimensions"])):
            if i is not len(entry["dimensions"]) - 1:
                offset.append(offset[i] * int(d["value"]))
        return offset[::-1]


def compute_storage_size(entry, typeentry) -> int:
    _c = entry["type"].count("*")
    if _c > 0:
        t = "".join(filter(lambda x: x != "*", entry["type"])).strip()
        return compute_storage_size({"type": t, "pointer_lvl": _c}, get_current_symtab().lookup_type(t))
    # if "[" in entry["type"]:
    #     # FIXME
    #     t = entry["type"][:entry["type"].index("[")]
    #     return compute_storage_size({"type":t, "pointer_lvl": 1}, get_current_symtab().lookup_type(t))
    global DATATYPE2SIZE
    if entry.get("is_array", False):
        prod = DATATYPE2SIZE[entry["type"].upper()]
        for d in entry["dimensions"]:
            if d == "variable":
                return "var"
            prod *= int(d["value"])
        return prod
    if entry.get("pointer_lvl", 0) > 0:
        return 8
    if entry["type"].startswith("enum "):
        return 4
    if entry["type"].startswith("struct "):
        size = 0
        symTab = get_current_symtab()
        temp = "".join(filter(lambda x: x != "*", entry["type"])).strip()
        typeentry = symTab.lookup_type(temp)
        for t in typeentry["field types"]:
            size += compute_storage_size({"type": t}, symTab.lookup_type(t))
        return size
    if entry["type"].startswith("union "):
        size = 0
        symTab = get_current_symtab()
        temp = "".join(filter(lambda x: x != "*", entry["type"])).strip()
        typeentry = symTab.lookup_type(temp)
        for t in typeentry["field types"]:
            size = max(size, compute_storage_size({"type": t}, symTab.lookup_type(t)))
        return size
    if typeentry is None:
        s = DATATYPE2SIZE[entry["type"].upper()]
        return s
    else:
        raise NotImplementedError
    return 0


TMP_VAR_COUNTER = 0
TMP_LABEL_COUNTER = 0
TMP_CLOSURE_COUNTER = 0


def get_tmp_var(vartype=None) -> str:
    global TMP_VAR_COUNTER
    TMP_VAR_COUNTER += 1
    vname = f"__tmp_var_{TMP_VAR_COUNTER}"
    if vartype is not None:
        symTab = get_current_symtab()
        symTab.insert(
            {
                "name": vname,
                "type": vartype,
                "is_array": False,
                "dimensions": [],
            }
        )
    return vname


def get_tmp_closure(rettype: str, argtypes: list = []) -> str:
    global TMP_CLOSURE_COUNTER
    TMP_CLOSURE_COUNTER += 1
    vname = f"__tmp_closure_{TMP_VAR_COUNTER}"
    symTab = get_current_symtab()
    symTab.insert(
        {"name": vname, "return type": rettype, "parameter types": argtypes},
        kind=1,
    )
    return vname


def get_tmp_label() -> str:
    global TMP_LABEL_COUNTER
    TMP_LABEL_COUNTER += 1
    return f"__tmp_label_{TMP_LABEL_COUNTER}"


def get_default_value(type: str):
    if type.upper() in INTEGER_TYPES:
        return 0
    elif type.upper() in FLOATING_POINT_TYPES:
        return 0.0
    elif type.upper() in CHARACTER_TYPES:
        return ""
    elif type[-1] == "*":
        return "NULL"
    else:
        return None


STDLIB_CODES = dict()


def get_stdlib_codes():
    global STDLIB_CODES
    return STDLIB_CODES
