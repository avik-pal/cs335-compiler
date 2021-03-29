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
    # kind = 1 for FN and 0 for ID
    def __init__(self, parent=None) -> None:
        global TABLENUMBER
        self._symtab_variables = dict()
        self._symtab_functions = dict()
        self._function_names = dict()
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
        if kind == 0:
            return entry["name"]
        elif kind == 1:
            return (
                entry["name"] + "(" + ",".join(entry["parameter types"]) + ")"
            )

    def insert(self, entry: dict, kind: int = 0) -> bool:
        # Variables (ID) -> ["name", "type", "is_array", "dimensions"]
        # Functions (FN) -> ["name", "return type", "parameter types"]
        name = self._get_proper_name(entry, kind)
        if self.lookup_current_table(name, kind) is None:
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
                self._symtab_functions[name] = entry
                if entry["name"] in self._function_names:
                    self._function_names[entry["name"]].append(name)
                else:
                    self._function_names[entry["name"]] = [name]
            return True
        return False
        # After Storage
        # Variables (ID) -> ["name", "type", "is_array", "dimensions", "kind", "size", "offset"]
        # Functions (FN) -> ["name", "return type", "parameter types", "kind"]

    def lookup_current_table(
        self, symname: str, paramtab_check: bool = True
    ) -> Union[None, list, dict]:
        res = self._symtab_variables.get(symname, None)
        if res is None:
            # Check for matching functions
            if "(" in symname:
                res = self._symtab_functions.get(symname, None)
            else:
                # If we match with a function base name return list of all
                # the available functions
                funcs = self._function_names.get(symname, None)
                res = (
                    [self._symtab_functions[func] for func in funcs]
                    if funcs is not None
                    else None
                )
        return (
            self.lookup_parameter(symname)
            if res is None and paramtab_check
            else res
        )

    def lookup_parameter(self, paramname: str) -> Union[None, list, dict]:
        # TODO: Check if this works
        for table in self._paramtab:
            if paramname in table._symtab_variables:
                return table._symtab_variables[paramname]
        return None

    def lookup(self, symname: str, idx: int = -1) -> Union[None, list, dict]:
        # Check in the current list of symbols
        res = self.lookup_current_table(symname, paramtab_check=(idx == -1))
        # Check if present in the parent recursively till root node is reached
        res = (
            self.parent.lookup(symname, idx=0)
            if res is None and self.parent
            else res
        )
        # Finally check in the current parameter table
        return self.lookup_parameter(symname) if res is None else res

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
    return f"_tmp_var_{TMP_VAR_COUNTER}"


def get_tmp_label() -> str:
    global TMP_LABEL_COUNTER
    TMP_LABEL_COUNTER += 1
    return f"_tmp_label_{TMP_LABEL_COUNTER}"
