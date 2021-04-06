from typing import Union, List


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


NUMERIC_TYPES = [
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
    "FLOAT",
    "DOUBLE",
    "LONG DOUBLE",
]


TABLENUMBER = 0


class SymbolTable:
    # kind = 0 for ID
    #        1 for FN
    #        2 for ST
    #        3 for CL
    #        4 for EN
    #        5 for UN
    def __init__(self, parent=None) -> None:
        global TABLENUMBER
        self._symtab_variables = dict()
        self._symtab_functions = dict()
        self._function_names = dict()
        self._symtab_structs = dict()
        self._symtab_typedefs = dict()
        self._symtab_unions = dict()
        self._symtab_classes = dict()
        self._symtab_enums = dict()
        self._custom_types = dict()
        self._paramtab = []
        self.parent = parent
        self.table_number = TABLENUMBER
        TABLENUMBER += 1

        if parent is None:
            self.table_name = "GLOBAL"
        else:
            self.table_name = f"BLOCK {self.table_number}"

    @staticmethod
    def _get_proper_name(entry: dict, kind: int = 0):
        if kind != 1:
            return entry["name"]
        else:
            # For function and its disambiguation
            return (
                entry["name"] + "(" + ",".join(entry["parameter types"]) + ")"
            )

    def insert(self, entry: dict, kind: int = 0) -> Union[bool, dict]:
        # Variables (ID) -> {"name", "type", "value", "is_array", "dimensions"}
        # Functions (FN) -> {"name", "return type", "parameter types"}
        # Structs (ST)   -> {"name", "alt name" (via typedef), "field names", "field types"}
        # Classes (CL)   -> {"name", ... TBD}
        # Enums (EN)     -> {"name", "field names", "field values"}
        # Unions (UN)    -> {"name", "alt name" (via typedef), "field names", "field types"}
        global DATATYPE2SIZE

        name = self._get_proper_name(entry, kind)
        if (
            self.lookup_current_table(name, kind, entry.get("alt name", None))
            is None
        ):
            entry["kind"] = kind

            if kind == 0:
                # Variable Identifier
                try:
                    entry["size"] = DATATYPE2SIZE[entry["type"].upper()]
                except KeyError:
                    # TODO: Proper error message with line number and such
                    raise Exception(
                        f"{entry['type']} is not a valid data type"
                    )
                entry["offset"] = compute_offset_size(
                    entry["size"], entry["is_array"], entry["dimensions"]
                )
                self._symtab_variables[name] = entry

            elif kind == 1:
                # Function
                entry["local scope"] = None
                self._symtab_functions[name] = entry
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
                for var in entry["field names"]:
                    nentry = self.insert(
                        {
                            "name": var,
                            "type": "int",
                            "is_array": False,
                            "dimensions": [],
                        }
                    )
                    entry["field2var"][var] = nentry
                self._symtab_enums[name] = entry
                self._custom_types[f"enum {name}"] = entry

            elif kind == 5:
                # Union
                if entry["alt name"] is None:
                    entry["alt name"] = get_tmp_label()
                # symtab_structs just stores the translated name
                self._symtab_unions[name] = entry["alt name"]
                self._symtab_typedefs[entry["alt name"]] = entry
                self._custom_types[f"union {name}"] = entry
                self._custom_types[entry["alt name"]] = entry

            else:
                raise Exception(f"{kind} is not a valid kind of identifier")

            return entry
        return False
        # After Storage
        # Variables (ID) -> {"name", "type", "value", "is_array", "dimensions", "kind", "size", "offset"}
        # Functions (FN) -> {"name", "return type", "parameter types", "kind", "local scope"}

    def _check_type_in_current_table(self, typename: str) -> bool:
        global DATATYPE2SIZE

        is_basic_type = typename.upper() in DATATYPE2SIZE
        return (
            typename in self._custom_types
            if not is_basic_type
            else is_basic_type
        )

    def check_type(self, typename: str) -> bool:
        is_type = self._check_type_in_current_table(typename)
        return (
            self.parent.check_type(typename)
            if self.parent is not None and not is_type
            else is_type
        )

    def _translate_type(self, typename: str) -> Union[None, str]:
        if typename[: max(6, len(typename))] == "struct":
            return self._symtab_structs.get(typename, None)
        if typename[: max(5, len(typename))] == "union":
            return self._symtab_unions.get(typename, None)
        return None

    def translate_type(self, typename: str) -> Union[None, str]:
        # Takes struct ___ / union ___ and converts it to a proper label
        tname = self._translate_type(typename)
        return (
            self.parent.translate_type(typename)
            if self.parent is not None and not tname
            else tname
        )

    def _search_for_variable(self, symname: str) -> Union[None, dict]:
        return self._symtab_variables.get(symname, None)

    def _search_for_function(
        self, symname: str
    ) -> Union[None, List[dict], dict]:
        if "(" in symname:
            return self._symtab_functions.get(symname, None)
        else:
            # If we match with a function base name return list of all
            # the available functions
            funcs = self._function_names.get(symname, None)
            return (
                [self._symtab_functions[func] for func in funcs]
                if funcs is not None
                else None
            )

    def _search_for_struct(
        self, symname: str, alt_name: Union[str, None]
    ) -> Union[None, dict]:
        if f"struct {symname}" in self._symtab_structs:
            return self._symtab_typedefs[
                self._symtab_structs[f"struct {symname}"]
            ]
        if symname in self._symtab_typedefs:
            return self._symtab.typedefs[symname]
        if alt_name in self._symtab_typedefs:
            return self._symtab.typedefs[alt_name]
        return None

    def _search_for_class(self, symname: str) -> Union[None, dict]:
        return self._symtab_classes.get(symname, None)
    
    def _search_for_enum(self, symname: str) -> Union[None, dict]:
        return self._symtab_enums.get(symname, None)
    
    def _search_for_union(
        self, symname: str, alt_name: Union[str, None]
    ) -> Union[None, dict]:
        if f"union {symname}" in self._symtab_unions:
            return self._symtab_typedefs[
                self._symtab_unions[f"union {symname}"]
            ]
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
    ) -> Union[None, list, dict]:
        res = self._search_for_variable(symname)
        res = self._search_for_function(symname) if res is None else res
        res = self._search_for_struct(symname, alt_name) if res is None else res
        res = self._search_for_class(symname) if res is None else res
        res = self._search_for_enum(symname) if res is None else res
        res = self._search_for_union(symname, alt_name) if res is None else res
        return (
            self.lookup_parameter(symname)
            if res is None and paramtab_check
            else res
        )

    def lookup_parameter(self, paramname: str) -> Union[None, list, dict]:
        res = None
        for table in self._paramtab:
            res = table._search_for_variable(paramname)
            if res is not None:
                break
        return res

    def lookup(
        self, symname: str, idx: int = -1, alt_name: Union[str, None] = None
    ) -> Union[None, list, dict]:
        # Check in the current list of symbols
        res = self.lookup_current_table(
            symname, paramtab_check=(idx == -1), alt_name=alt_name
        )
        # Check if present in the parent recursively till root node is reached
        res = (
            self.parent.lookup(symname, idx=0, alt_name=alt_name)
            if res is None and self.parent
            else res
        )
        # Finally check in the current parameter table
        return self.lookup_parameter(symname) if res is None else res

    def add_function_scope(self, funcname: str, table) -> None:
        if "(" not in funcname:
            raise Exception(
                f"Supply the disambiguated function name for {funcname}"
            )
        self._symtab_functions[funcname] = SymbolTable

    def display(self) -> None:
        # Simple Pretty Printer
        print()
        print("-" * 100)
        print(
            f"SYMBOL TABLE: {self.table_name}, TABLE NUMBER: {self.table_number}"
        )
        print("-" * 51)
        print(" " * 20 + " Variables " + " " * 20)
        print("-" * 51)
        for k, v in self._symtab_variables.items():
            print(
                f"Name: {k}, Type: {v['type']}, Size: {v['size']}"
                + (
                    ""
                    if not v["is_array"]
                    else f"Dimensions: {v['dimensions']}"
                )
            )
        print("-" * 51)
        print(" " * 20 + " Functions " + " " * 20)
        print("-" * 51)
        for k, v in self._symtab_functions.items():
            print(
                f"Name: {v['name']}, Return: {v['return type']}, Parameters: {v['parameter types']}, Name Resolution: {k}"
            )
        print("-" * 100)
        print()


SYMBOL_TABLES = []


def pop_scope() -> SymbolTable:
    global SYMBOL_TABLES
    s = SYMBOL_TABLES.pop()
    s.display()
    print(
        "[DEBUG INFO]  POP SYMBOL TABLE: ",
        s.table_number,
        s.table_name,
    )
    return s


def push_scope(s: SymbolTable) -> None:
    global SYMBOL_TABLES
    SYMBOL_TABLES.append(s)
    print("[DEBUG INFO] PUSH SYMBOL TABLE: ", s.table_number, s.table_name)


def new_scope(parent=None) -> SymbolTable:
    return SymbolTable(parent)


def get_current_symtab() -> Union[None, SymbolTable]:
    global SYMBOL_TABLES
    return None if len(SYMBOL_TABLES) == 0 else SYMBOL_TABLES[-1]


def compute_offset_size(
    dsize: int, is_array: bool, dimensions: List[int]
) -> int:
    # TODO: Implement
    return -1


TMP_VAR_COUNTER = 0
TMP_LABEL_COUNTER = 0


def get_tmp_var() -> str:
    global TMP_VAR_COUNTER
    TMP_VAR_COUNTER += 1
    return f"__tmp_var_{TMP_VAR_COUNTER}"


def get_tmp_label() -> str:
    global TMP_LABEL_COUNTER
    TMP_LABEL_COUNTER += 1
    return f"__tmp_label_{TMP_LABEL_COUNTER}"
