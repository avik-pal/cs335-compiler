from typing import Union


DATATYPE2SIZE = {
    "VOID": 0,
    "SHORT": 2,
    "INT": 4,
    "LONG": 8,
    "CHAR": 1,
    "FLOAT": 4,
    "DOUBLE": 8,
}

TABLENUMBER = 0


class SymbolTable:
    def __init__(self, parent=-1) -> None:
        global TABLENUMBER
        self._symtab = dict()  # Stores SymbolName -> (Type, Scope, Attributes)
        self._paramtab = []  # List of SymbolTable
        self.parent = None if parent == -1 else parent
        self.table_number = TABLENUMBER
        TABLENUMBER += 1

        if parent == -1:
            self.table_name = "GLOBAL"
        else:
            self.table_name = f"BLOCK {self.table_number}"

    def insert(self, entry: dict) -> bool:
        if not self.lookup_current_table(entry[0]):
            # Make the entry
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
