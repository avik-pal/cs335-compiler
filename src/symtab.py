from typing import Union


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
    "LONG DOUBLE": 16
}

TABLENUMBER = 0


class SymbolTable:
    def __init__(self, parent=None) -> None:
        global TABLENUMBER
        self._symtab = dict()  # Stores SymbolName -> (Type, Scope, Attributes)
        self._paramtab = []    # List of SymbolTable
        self.parent = parent
        self.table_number = TABLENUMBER
        TABLENUMBER += 1

        if parent is None:
            self.table_name = "GLOBAL"
        else:
            self.table_name = f"BLOCK {self.table_number}"

    def insert(self, entry: dict, kind: int = 1) -> bool:
        # kind = 1 for FN and 0 for ID
        # Variables (ID) -> ["name", "type", "is_array", "dimensions"]
        # Functions (FN) -> ["name", "return type", "parameter types"]
        if self.lookup_current_table(entry["name"]) is None:
            entry["kind"] = "FN" if kind == 1 else "ID"
            if kind == 0:
                try:
                    entry["size"] = DATATYPE2SIZE[entry["type"].upper()]
                except KeyError:
                    # TODO: Proper error message with line number and such
                    raise Exception(f"{entry['type']} is not a valid data type")
                entry["offset"] = compute_offset_size(entry["size"], entry["is_array"], entry["dimensions"])
            # Variables (ID) -> ["name", "type", "is_array", "dimensions", "kind", "size", "offset"]
            # Functions (FN) -> ["name", "return type", "parameter types", "kind"]
            self._symtab[entry["name"]] = entry
            return True
        return False

    def lookup_current_table(
        self, symname: str, paramtab_check: bool = True
    ) -> Union[None, tuple]:
        res = self._symtab.get(symname, None)
        return (
            self.lookup_parameter(symname)
            if res is None and paramtab_check
            else res
        )

    def lookup_parameter(self, paramname: str) -> Union[None, tuple]:
        for table in self._paramtab:
            if paramname in table._symtab:
                return table._symtab[paramname]
        return None

    def lookup(self, symname: str, idx: int = -1) -> Union[None, tuple]:
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


SYMBOL_TABLES = []

def pop_scope() -> SymbolTable:
    global SYMBOL_TABLES
    cur_tab = get_current_symtab()
    print("[DEBUG INFO]  POP SYMBOL TABLE: ", cur_tab.table_number, cur_tab.table_name)
    return SYMBOL_TABLES.pop()

def push_scope(s: SymbolTable) -> None:
    global SYMBOL_TABLES
    SYMBOL_TABLES.append(s)
    print("[DEBUG INFO] PUSH SYMBOL TABLE: ", s.table_number, s.table_name)

def new_scope(parent=None) -> SymbolTable:
    return SymbolTable(parent)

def get_current_symtab() -> Union[None, SymbolTable]:
    global SYMBOL_TABLES
    return None if len(SYMBOL_TABLES) == 0 else SYMBOL_TABLES[-1]

def compute_offset_size(dsize, is_array, dimensions) -> int:
    # TODO: Implement
    return -1