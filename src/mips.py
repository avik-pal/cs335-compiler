from symtab import (
    SymbolTable,
    get_current_symtab,
    get_global_symtab,
    get_tabname_mapping,
)

IF_LABEL = -1
STATIC_NESTING_LVL = -1
DYNAMIC_NESTING_LVL = -1
declared_variables = []

numeric_ops = {"+": "add", "-": "sub", "*": "mul", "/": "div"}
rel_ops = {
    "<=": "sle",
    "<": "slt",
    "!=": "sne",
    "==": "seq",
    ">": "sge",
    ">=": "sgt",
}


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
    # return entry["name"]
    name = "VAR-" + entry["table name"] + "-" + entry["name"]
    return name


def reset_registers():
    global address_descriptor, activation_record, register_descriptor, free_registers, remember_to_restore
    global parameter_descriptor, busy_registers, lru_list, registers_in_block, removed_registers
    address_descriptor = dict()
    activation_record = []
    free_registers = [f"$s{i}" for i in range(8)] + [f"$t{i}" for i in range(10)]
    register_descriptor = {reg: None for reg in free_registers}
    removed_registers = dict()
    registers_in_block = []
    parameter_descriptor = {"$a1": None, "$a2": None, "$a3": None}
    busy_registers = []
    lru_list = []
    remember_to_restore = []


def access_dynamic_link(reg: str):
    print(f"\tlw\t{reg},\t-4($fp)")  # loads pointer to parent AR inside reg


#  TODO: relevant for nested procedures
# def access_static_link(reg: str, n_level: int): # n_level = level_curr_fxn - level_callee
#     print(f"\tlw\t{reg},\t-4($fp)")

#     if n_level > -1:
#         for i in range(0, n_level +1):
#             print(f"\tlw\t{reg},\t-4({reg})")  # backtrace n_level + 1 times

#     elif n_level < -1:
#         # callee is nested deeper


def type_cast_mips(c, dtype, current_symbol_table):  # reg1 := (dtype)reg2

    if c[0].startswith("__tmp"):
        t1 = get_register(c[0], current_symbol_table)
    else:
        t1 = get_register(convert_varname(c[0], current_symbol_table), current_symbol_table)

    if is_number(c[3]):
        # load into t1
        if dtype == "int":
            print(f"\tli\t{t1},\t{c[3]}")
        elif dtype == "float":
            print(f"\tli.s\t{t1},\t{c[3]}")
        elif dtype == "double":
            print(f"\tli.d\t{t1},\t{c[3]}")

    elif c[3].startswith("__tmp"):
        t2 = get_register(c[3], current_symbol_table)

        # load into new reg
        if dtype == "int":
            print(f"\tlw\t{t1},\t{t2}")
        elif dtype == "float":
            print(f"\tl.s\t{t1},\t{t2}")
        elif dtype == "double":
            print(f"\tl.d\t{t1},\t{t2}")

    else:
        t2 = get_register(convert_varname(c[3], current_symbol_table), current_symbol_table)
        # load into new reg
        if dtype == "int":
            print(f"\tlw\t{t1},\t{t2}")
        elif dtype == "float":
            print(f"\tl.s\t{t1},\t{t2}")
        elif dtype == "double":
            print(f"\tl.d\t{t1},\t{t2}")


# def get_register(var, current_symbol_table):
#     # FIXME ....
#     global address_descriptor, activation_record, register_descriptor, free_registers, parameter_descriptor, busy_registers, lru_list, declared_variables, registers_in_block
#     register = ""
#     if var in register_descriptor.values():
#         register = address_descriptor[var]
#     else:
#         if len(free_registers) == 0:
#             for x in lru_list:
#                 onhold_reg = x  # assigned register
#                 assigned_var = register_descriptor[onhold_reg]  # checked the previously alloted variable
#                 c_var = assigned_var.split("_")  # c code name of the variable
#                 name = c_var[-1]
#                 # TODO: Match semantics here
#                 if not name.isdigit():  # if it is not a label
#                     print("\tsw\t" + onhold_reg + ",\t" + assigned_var)  # store the register value in the memory
#                     register_descriptor[onhold_reg] = var  # assign the register to the alloted variable
#                     tmp_var = address_descriptor.pop(
#                         assigned_var, None
#                     )  # delete the entry from the address_descriptor
#                     address_descriptor[var] = onhold_reg  # add entry to the address descriptor
#                     break
#             register = onhold_reg
#             if register in lru_list:
#                 lru_list.remove(register)
#         else:
#             register = free_registers.pop()
#             address_descriptor[var] = register
#             busy_registers.append(register)
#             register_descriptor[register] = var
#             if var in declared_variables:
#                 print("\tlw\t" + register + ",\t" + var)
#     lru_list.append(register)
#     return register


def get_register(var, current_symbol_table, offset):
    if var != "-":
        var = convert_varname(var, current_symbol_table)
    return simple_register_allocator(var, current_symbol_table, offset)


def simple_register_allocator(var: str, current_symbol_table: SymbolTable, offset: int):
    global register_descriptor, address_descriptor, registers_in_block, removed_registers, lru_list, remember_to_restore
    # GLOBALs wont work for now
    if var in register_descriptor.values():
        # Already has a register allocated
        register = address_descriptor[var]
    else:
        if len(free_registers) == 0:
            # No free register available
            register = lru_list[0]
            if register[1] == "s":
                remember_to_restore[-1].append(f"\tlw\t{register},\t{offset}($fp)")
            removed_registers[register_descriptor[register]] = f"{offset}($fp)"
            offset -= 4
            ## Store the current value
            print("\tsw\t" + register + ",\t" + removed_registers[register_descriptor[register]])
            print("\tls\t$sp,\t-4($sp)")
            lru_list = lru_list[1:]
        else:
            # Free registers available
            register = free_registers.pop()
            if var in removed_registers:
                print("\tlw\t" + register + ",\t" + removed_registers[var])
                del removed_registers[var]
        address_descriptor[var] = register
        busy_registers.append(register)
        register_descriptor[register] = var
        registers_in_block[-1].append(register)
    lru_list.append(register)
    return register, offset


def store_temp_regs_in_use(offset: int) -> int:
    global busy_registers, removed_registers, register_descriptor
    saves = 0
    for reg in busy_registers:
        if reg[1] == "t":
            removed_registers[register_descriptor[reg]] = f"{offset}($fp)"
            offset -= 4
            saves += 1
            ## Store the current value
            print("\tsw\t" + reg + ",\t" + removed_registers[register_descriptor[reg]])
            register_descriptor[reg] = None
    if saves >= 1:
        print(f"\tla\t$sp,\t-{4 * saves}($sp)")
    return offset


def free_registers_in_block():
    global registers_in_block, register_descriptor, address_descriptor, remember_to_restore
    for reg in registers_in_block[-1]:
        var = register_descriptor[reg]
        register_descriptor[reg] = None
        busy_registers.remove(reg)
        # del address_descriptor[var]
    registers_in_block = registers_in_block[:-1]
    remember_to_restore = remember_to_restore[:-1]


def create_new_register_block():
    global registers_in_block, remember_to_restore
    registers_in_block += [[]]
    remember_to_restore += [[]]


def store_registers_on_function_call() -> int:
    global removed_registers, busy_registers, register_descriptor
    off = -12  # already stored fp and ra
    return off


def load_registers_on_function_return(p_stack: str):
    global stored_registers, remember_to_restore
    for l in remember_to_restore[-1]:
        print(l)


# NOTE:
# 3. Handle data type sizes properly. All instructions wont be lw
# 4. IMP: int main() should be present and with no other form of definition


def generate_mips_from_3ac(code):
    global numeric_ops, rel_ops, STATIC_NESTING_LVL, DYNAMIC_NESTING_LVL

    print("## MIPS Assembly Code\n")

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

    first_pushparam = True
    offset = 0

    for part in code:
        for i, c in enumerate(part):
            print("\n#", c)
            if len(c) == 1:
                if c[0].endswith(":"):
                    # Label
                    print(c[0].replace("(", "__").replace(")", "__"))
                elif c[0] == "ENDFUNC":
                    print("\tla\t$sp,\t0($fp)")
                    print("\tlw\t$ra,\t-8($sp)")
                    print("\tlw\t$fp,\t-4($sp)")
                    load_registers_on_function_return("sp")
                    print("\tjr\t$ra")  # return
                    free_registers_in_block()
                    # STATIC_NESTING_LVL -= 1

                elif c[0] == "RETURN":
                    DYNAMIC_NESTING_LVL -= 1
                    print("\tla\t$sp,\t0($fp)")
                    print("\tlw\t$ra,\t-8($sp)")
                    print("\tlw\t$fp,\t-4($sp)")
                    load_registers_on_function_return("sp")
                    print("\tjr\t$ra")  # return

                else:
                    print(c)

            elif len(c) == 2:
                if c[0] == "SYMTAB":
                    # Pop Symbol Table
                    current_symbol_table = current_symbol_table.parent

                elif c[0] == "BEGINFUNC":
                    # STATIC_NESTING_LVL += 1
                    # Has the overall size for the function
                    print("\tsw\t$fp,\t-4($sp)")  # dynamic link (old fp)
                    print("\tsw\t$ra,\t-8($sp)")
                    print("\tla\t$fp,\t0($sp)")
                    offset = store_registers_on_function_call()  #  - int(c[1])
                    print(f"\tla\t$sp,\t{offset}($sp)")
                    create_new_register_block()

                elif c[0] == "RETURN":
                    DYNAMIC_NESTING_LVL -= 1
                    if is_number(c[1]):
                        # FIXME: Might be Floating Point
                        t, offset = get_register("-", current_symbol_table, offset)
                        print(f"\tli\t{t},\t{c[1]}")
                    else:
                        t, offset = get_register(c[1], current_symbol_table, offset)
                    print(f"\tmove\t$v0,\t{t}")
                    print("\tla\t$sp,\t0($fp)")
                    print("\tlw\t$ra,\t-8($sp)")
                    print("\tlw\t$fp,\t-4($sp)")
                    load_registers_on_function_return("sp")
                    print("\tjr\t$ra")

                elif c[0] == "PUSHPARAM":
                    if first_pushparam:
                        first_pushparam = False
                        offset = store_temp_regs_in_use(offset)
                    # We should ideally be using the a0..a2 registers, but for ease of use we will
                    # push everything into the stack
                    if is_number(c[1]):
                        # TODO: Might be of type float
                        t, offset = get_register("-", current_symbol_table, offset)
                        print(f"\tli\t{t},\t{c[1]}")
                    else:
                        t, offset = get_register(c[1], current_symbol_table, offset)
                    # FIXME: size might be different from 4
                    print(f"\tsw\t{t},\t-4($sp)")
                    print(f"\tla\t$sp,\t-4($sp)")

                elif c[0] == "POPPARAMS":
                    first_pushparam = True

                elif c[0] == "GOTO":
                    print(f"\tj\t{c[1]}")
                else:
                    print(c)

            elif len(c) == 3:
                if c[1] == ":=":
                    # Assignment
                    t1, offset = get_register(c[0], current_symbol_table, offset)

                    if is_number(c[2]):
                        # Assignment with a constant
                        print(f"\tli\t{t1},\t{c[2]}")
                    else:
                        t2, offset = get_register(c[2], current_symbol_table, offset)
                        print(f"\tmove\t{t1},\t{t2}")

                elif c[0] == "SYMTAB":
                    # Symbol Table
                    current_symbol_table = tabname_mapping[c[2]]
                    params = current_symbol_table._paramtab
                    off = 0
                    for p in reversed(params):
                        entry = current_symbol_table.lookup(p)
                        t, offset = get_register(entry["name"], current_symbol_table, offset)
                        # FIXME: Sizes
                        print(f"\tlw\t{t},\t{off}($fp)")
                        off += entry["size"]
                else:
                    print(c)

            elif len(c) == 4:
                if c[1] == ":=":
                    # typecast expression
                    if c[2].startswith("("):
                        datatype = c[2].replace("(", "").replace(")", "")
                        # print("--convert--to-",datatype, "---")
                        type_cast_mips(c, datatype, current_symbol_table)

                else:
                    print(c)

            elif len(c) == 5:
                if c[1] == ":=":
                    if c[2] == "CALL":
                        # Function Call
                        DYNAMIC_NESTING_LVL += 1
                        t1, offset = get_register(c[0], current_symbol_table, offset)
                        if first_pushparam:
                            offset = store_temp_regs_in_use(offset)
                        print(f"\tjal\t{c[3].replace('(', '__').replace(')', '__')}")
                        # caller pops the arguments
                        print(f"\tla\t$sp,\t{c[4]}($sp)")
                        print(f"\tmove\t{t1},\t$v0")  # store return value to LHS of assignment
                        first_pushparam = True

                    else:
                        # Assignment + An op
                        op = c[3]
                        instr = numeric_ops[op] if op in numeric_ops else rel_ops[op]
                        t1, offset = get_register(c[0], current_symbol_table, offset)

                        if is_number(c[2]):
                            t2, offset = get_register("-", current_symbol_table, offset)
                            print(f"\tli\t{t2},\t{c[2]}")
                        else:
                            t2, offset = get_register(c[2], current_symbol_table, offset)

                        if is_number(c[4]):
                            t3, offset = get_register("-", current_symbol_table, offset)
                            print(f"\tli\t{t3},\t{c[4]}")
                        else:
                            t3, offset = get_register(c[4], current_symbol_table, offset)

                        print(f"\t{instr}\t{t1},\t{t2},\t{t3}")

            elif len(c) == 6:
                if c[0] == "IF" and c[4] == "GOTO":
                    op = c[2]
                    instr = rel_ops[op]

                    if not is_number(c[1]):
                        t1, offset = get_register(c[1], current_symbol_table, offset)
                    else:
                        t1, offset = get_register("-", current_symbol_table, offset)
                        print(f"\tli\t{t1},\t{c[1]}")

                    if not is_number(c[3]):
                        t2, offset = get_register(c[3], current_symbol_table, offset)
                    else:
                        t2, offset = get_register("-", current_symbol_table, offset)
                        print(f"\tli\t{t2},\t{c[3]}")

                    # store in another reg
                    t3, offset = get_register("-", current_symbol_table, offset)

                    global IF_LABEL
                    IF_LABEL += 1

                    print(f"\t{instr}\t{t3},\t{t1},\t{t2}")
                    print(f"\tbeq\t{t3},\t$0,\tIFBRANCH_{IF_LABEL}")
                    print(f"\tj\t{c[5]}")
                    print(f"IFBRANCH_{IF_LABEL}:")

            else:
                print(c)

    print()
    print("main:")
    print("\tsw\t$fp,\t-4($sp)")
    print("\tsw\t$ra,\t-8($sp)")
    print("\tla\t$fp,\t0($sp)")
    print("\tla\t$sp,\t-4($sp)")
    # Function Call
    print("\tjal\tmain____")
    print("\tmove\t$a0,\t$v0")
    print("\tli\t$v0,\t1")
    print("\tsyscall")
    print("\tli\t$v0,\t10")
    print("\tsyscall")


reset_registers()
