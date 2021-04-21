from symtab import SymbolTable, get_current_symtab, get_global_symtab, get_tabname_mapping


declared_variables = []

numeric_ops = {"+": "add", "-": "sub", "*": "mul", "/": "div"}
rel_ops = {"<=": "sle", "<": "slt", "!=": "sne", "==": "seq", ">": "sge", ">=": "sgt"}


def is_number(s: str) -> bool:
    try:
        if not s.isnumeric():
            float(s)
            return True
        else:
            return True
    except ValueError:
        return False


def convert_varname(var: str, cur_symtab: SymbolTable) -> str:
    entry = cur_symtab.lookup(var)
    if entry is None and cur_symtab.func_scope is not None:
        entry = cur_symtab.lookup(var + ".static." + cur_symtab.func_scope)
    return "VAR_" + cur_symtab.table_name + "_" + entry["name"]


def reset_registers():
    global address_descriptor, activation_record, register_descriptor, free_registers, parameter_descriptor, busy_registers, lru_list
    address_descriptor = dict()
    activation_record = []
    register_descriptor = {
        "$t0": None,
        "$t1": None,
        "$t2": None,
        "$t3": None,
        "$t4": None,
        "$t5": None,
        "$t6": None,
        "$t7": None,
        "$t8": None,
        "$t9": None,
        "$s0": None,
        "$s1": None,
        "$s2": None,
        "$s3": None,
        "$s4": None,
    }
    free_registers = [
        "$s4",
        "$s3",
        "$s2",
        "$s1",
        "$s0",
        "$t9",
        "$t8",
        "$t7",
        "$t6",
        "$t5",
        "$t4",
        "$t3",
        "$t2",
        "$t1",
        "$t0",
    ]
    parameter_descriptor = {"$a1": None, "$a2": None, "$a3": None}
    busy_registers = []
    lru_list = []


def get_register(var, current_symbol_table):
    global address_descriptor, activation_record, register_descriptor, free_registers, parameter_descriptor, busy_registers, lru_list, declared_variables
    register = ""
    if var.split("_")[1] == "GLOBAL":
        off = current_symbol_table.lookup(var.split("_")[-1])["offset"]
        if len(free_registers):
            register = free_registers.pop()
        # FIXME: Do we need these?
        # print("\taddi\t" + register + ", \t$zero, \t" + str(off))
        # print("\tlw\t" + register + ", \tVAR_global" + "(" + register + ")")
    # TODO: Parameter lookup support in symtab.py
    # elif current_symbol_table.lookupCurrentParameter(var.split("_")[-1]) != False:
    #     reg = "$a" + str(funlist[currentSymbolTable.tableName].index(var.split("_")[-1]) + 1)
    #     return reg
    elif var in register_descriptor.values():
        register = address_descriptor[var]
    else:
        if len(free_registers) == 0:
            for x in lru_list:
                onhold_reg = x  # assigned register
                assigned_var = register_descriptor[onhold_reg]  # checked the previously alloted variable
                c_var = assigned_var.split("_")  # c code name of the variable
                name = c_var[-1]
                # TODO: Match semantics here
                if not name.isdigit():  # if it is not a label
                    print("\tsw\t" + onhold_reg + ",\t" + assigned_var)  # store the register value in the memory
                    register_descriptor[onhold_reg] = var  # assign the register to the alloted variable
                    tmp_var = address_descriptor.pop(assigned_var, None)  # delete the entry from the address_descriptor
                    address_descriptor[var] = onhold_reg  # add entry to the address descriptor
                    break
            register = onhold_reg
            if register in lru_list:
                lru_list.remove(register)
        else:
            register = free_registers.pop()
            address_descriptor[var] = register
            busy_registers.append(register)
            register_descriptor[register] = var
            if var in declared_variables:
                print("\tlw\t" + register + ",\t" + var)
    lru_list.append(register)
    return register


def generate_mips_from_3ac(code):
    global numeric_ops, rel_ops

    print("MIPS Assembly Code\n")

    tabname_mapping = get_tabname_mapping()
    gtab = get_global_symtab()

    # Generate the data part for the global variables
    print(".data")
    for var, entry in gtab._symtab_variables.items():
        # TODO: Might need to deal with alignment issues
        print(f"\t{var}:\t.space\t{entry['size']}")
    print()

    # Generate the text part
    print(".text")
    current_symbol_table = gtab

    for part in code:
        for c in part:
            if len(c) == 1:
                if c[0].endswith(":"):
                    # Label
                    print(c[0])
                elif c[0] == "ENDFUNC":
                    # FIXME: Ignoring atm; Restore callee saved registers
                    continue
                elif c[0] == "RETURN":
                    print("\tla\t$sp,\t0($fp)")
                    print("\tlw\t$ra,\t-8($sp)")
                    print("\tlw\t$fp,\t-4($sp)")
                    print("\tjr\t$ra")
                else:
                    print(c)
            elif len(c) == 2:
                if c[0] == "SYMTAB":
                    # Symbol Table
                    current_symbol_table = current_symbol_table.parent
                elif c[0] == "BEGINFUNC":
                    # Has the overall size for the function
                    print("\tsw\t$fp,\t-4($sp)")
                    print("\tsw\t$ra,\t-8($sp)")
                    print("\tla\t$fp,\t0($sp)")
                    print(f"\tla\t$sp,\t-{c[1]}($sp)")
                elif c[0] == "RETURN":
                    t = get_register(convert_varname(c[1], current_symbol_table), current_symbol_table)
                    print(f"\tadd\t$v0,\t{t},\t$0")
                    print("\tla\t$sp,\t0($fp)")
                    print("\tlw\t$ra,\t-8($sp)")
                    print("\tlw\t$fp,\t-4($sp)")
                    print("\tjr\t$ra")
                else:
                    print(c)
            elif len(c) == 3:
                if c[1] == ":=":
                    # Assignment
                    if is_number(c[2]):
                        # Assignment with a constant
                        t1 = get_register(convert_varname(c[0], current_symbol_table), current_symbol_table)
                        print(f"\tli\t{t1},\t{c[2]}")
                    else:
                        t1 = get_register(convert_varname(c[0], current_symbol_table), current_symbol_table)
                        t2 = get_register(convert_varname(c[2], current_symbol_table), current_symbol_table)
                        print(f"\tadd\t{t1},\t{t2},\t$0")
                elif c[0] == "SYMTAB":
                    # Symbol Table
                    current_symbol_table = tabname_mapping[c[2]]
                else:
                    print(c)
            elif len(c) == 4:
                print(c)
            elif len(c) == 5:
                if c[1] == ":=":
                    if c[2] == "CALL":
                        # Function Call
                        print(c)
                    else:
                        # Assignment + An op 
                        op = c[3]
                        instr = numeric_ops[op] if op in numeric_ops else rel_ops[op]
                        t1 = get_register(convert_varname(c[0], current_symbol_table), current_symbol_table)
                        t2 = get_register(convert_varname(c[2], current_symbol_table), current_symbol_table)
                        t3 = get_register(convert_varname(c[4], current_symbol_table), current_symbol_table)
                        print(f"\t{instr}\t{t1},\t{t2},\t{t3}")
                else:
                    print(c)


reset_registers()
