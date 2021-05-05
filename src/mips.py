from copy import deepcopy

from symtab import (
    SymbolTable,
    compute_offset_size,
    get_current_symtab,
    get_global_symtab,
    get_tabname_mapping,
    get_tmp_label,
    get_default_value,
    DATATYPE2SIZE,
)

IF_LABEL = -1
STATIC_NESTING_LVL = -1
DYNAMIC_NESTING_LVL = -1
declared_variables = []

BINARY_REL_OPS = ["==", ">", "<", ">=", "<=", "!="]

BINARY_OPS_TO_INSTR = {
    "int": {
        "+": "add",
        "-": "sub",
        "*": "mul",
        "/": "div",
        "<=": "sle",
        "<": "slt",
        "!=": "sne",
        "==": "seq",
        ">": "sge",
        ">=": "sgt",
    },
    "float": {
        "+": "add.s",
        "-": "sub.s",
        "*": "mul.s",
        "/": "div.s",
        "<=": "c.le.s",
        "<": "c.lt.s",
        "!=": "c.ne.s",
        "==": "c.eq.s",
        ">": "c.ge.s",
        ">=": "c.gt.s",
    },
    "double": {
        "+": "add.d",
        "-": "sub.d",
        "*": "mul.d",
        "/": "div.d",
        "<=": "c.le.d",
        "<": "c.lt.d",
        "!=": "c.ne.d",
        "==": "c.eq.d",
        ">": "c.ge.d",
        ">=": "c.gt.d",
    },
}

SAVE_INSTRUCTIONS = {
    "char": "sb",
    "int": "sw",
    "long": "sd",
    "float": "s.s",
    "double": "s.d",
}

LOAD_INSTRUCTIONS = {
    "char": "lb",
    "int": "lw",
    "long": "ld",
    "float": "l.s",
    "double": "l.d",
}

RETURN_REGISTERS = {
    "char": "$v0",
    "int": "$v0",
    "long": "$v0",
    "float": "$f0",
    "double": "$f0",
}

MOVE_INSTRUCTIONS = {
    "char": "move",
    "int": "move",
    "long": "move",
    "float": "mov.s",
    "double": "mov.d",
}


DATA_SECTION = []
TEXT_SECTION = []
data_number_counter = -1


def get_tmp_data():
    global data_number_counter
    data_number_counter += 1
    return f"__tmp_data_{data_number_counter}"


def print_data(*s):
    s = " ".join(s)
    global DATA_SECTION
    DATA_SECTION.append(s)


def print_text(*s):
    s = " ".join(s)
    global TEXT_SECTION
    TEXT_SECTION.append(s)


def get_mips_instr_from_binary_op(op: str, t: str, reg1: str, reg2: str, reg3: str) -> str:
    # reg3 := reg1 op reg2
    global BINARY_OPS_TO_INSTR, BINARY_REL_OPS
    op_mips = BINARY_OPS_TO_INSTR[t][op]
    if op in BINARY_REL_OPS and t in ("float", "double"):
        label1 = get_tmp_label()
        label2 = get_tmp_label()
        return [
            f"\t{op_mips}\t{reg1},\t{reg2}",
            f"\tbc1f\t{label1}",
            f"\tli\t{reg3},\t1",
            f"\tj\t{label2}",
            f"{label1}:",
            f"\tli\t{reg3},\t0",
            f"{label2}:",
        ]
    else:
        return [f"\t{op_mips}\t{reg3},\t{reg1},\t{reg2}"]


def type_of_number(s: str):
    try:
        if not s.isnumeric():
            float(s)
            return "float"
        else:
            return "int"
    except ValueError:
        return None


def is_number(s: str, return_instr=False):
    try:
        if not s.isnumeric():
            float(s)
            if return_instr:
                var = get_tmp_data()
                print_data(f"{var}: .float {s}")
                return True, lambda reg: "\tl.s\t" + reg + ",\t" + var
            else:
                return True
        else:
            return True if not return_instr else (True, lambda reg: "\tli\t" + reg + ",\t" + s)
    except ValueError:
        return False if not return_instr else (False, lambda reg: "")


def reset_registers():
    global address_descriptor, activation_record, register_descriptor, free_registers, remember_to_restore
    global parameter_descriptor, busy_registers, lru_list_fp, lru_list_int, registers_in_block, removed_registers
    global integer_registers, fp_registers, free_registers_int
    address_descriptor = dict()
    activation_record = []
    integer_registers = [f"$t{i}" for i in range(10)] + [f"$s{i}" for i in range(8)]
    fp_registers = [f"$f{i}" for i in list(range(30, 2, -2))]
    free_registers = integer_registers + fp_registers
    register_descriptor = {reg: None for reg in free_registers}
    removed_registers = dict()
    registers_in_block = []
    parameter_descriptor = {"$a1": None, "$a2": None, "$a3": None}
    busy_registers = []
    lru_list_fp = []
    lru_list_int = []
    remember_to_restore = []


def access_dynamic_link(reg: str):
    print_text(f"\tlw\t{reg},\t-4($fp)")  # loads pointer to parent AR inside reg


def convert_varname(var: str, cur_symtab: SymbolTable):
    splits = var.split(".")
    identifier = splits[0]
    entry = cur_symtab.lookup(identifier)
    if entry is None and cur_symtab.func_scope is not None:
        entry = cur_symtab.lookup(identifier + ".static." + cur_symtab.func_scope)
    _type = entry["type"]
    for f in splits[1:]:
        type_entry = cur_symtab.lookup_type(_type)
        _type = type_entry["field types"][type_entry["field names"].index(f)]
    entry = deepcopy(entry)
    entry["type"] = _type
    name = "VAR-" + entry["table name"] + "-" + var
    return name, entry


def get_type_cast_instr(t1, t2):  # t1 -> t2
    if t2 == "int":
        if t1 == "float":
            return ["cvt.w.s", "mfc1"]
        elif t1 == "double":
            return ["cvt.w.d", "mfc1.d"]
    elif t2 == "float":
        if t1 == "int":
            return ["mtc1", "cvt.s.w"]
        elif t1 == "double":
            return ["cvt.s.d"]
    elif t2 == "double":
        if t1 == "int":
            return ["mtc1.d", "cvt.d.w"]
        elif t1 == "float":
            return ["cvt.d.s"]
    raise NotImplementedError


def type_cast_mips(c, dtype, current_symbol_table, offset):  # reg1 := (dtype) reg2

    t1, offset = get_register(c[0], current_symbol_table, offset)
    is_num, instr = is_number(c[3], True)
    t2, offset, entry = get_register(c[3], current_symbol_table, offset, True)

    if is_num:
        _type = type_of_number(c[3])
        print_text(instr(t2))
    else:
        _type = entry["type"]

    instrs = get_type_cast_instr(_type, dtype)

    if len(instrs) == 2:
        ttemp, offset = get_register("0.0", current_symbol_table, offset)
        if instrs[0].startswith("mtc1"):
            print_text(f"\t{instrs[0]}\t{t2},\t{ttemp}")
        else:
            print_text(f"\t{instrs[0]}\t{ttemp},\t{t2}")
        print_text(f"\t{instrs[1]}\t{t1},\t{ttemp}")
    else:
        print_text(f"\t{instrs[0]}\t{t1},\t{t2}")

    return offset


def requires_fp_register(val, entry):
    if entry is not None:
        return entry["type"] in ("float", "double", "long double")
    else:
        v = eval(val)
        return isinstance(v, float)


def get_register(var, current_symbol_table, offset, return_entry=False):
    entry = None
    if not is_number(var):
        var, entry = convert_varname(var, current_symbol_table)
    reg, offset = simple_register_allocator(var, current_symbol_table, offset, entry)
    return (reg, offset) if not return_entry else (reg, offset, entry)


# NOTE: We are only supporting int and float as data types


def simple_register_allocator(var: str, current_symbol_table: SymbolTable, offset: int, entry):
    global register_descriptor, address_descriptor, registers_in_block, removed_registers
    global lru_list_int, lru_list_fp, remember_to_restore
    # GLOBALs wont work for now

    if requires_fp_register(var, entry):
        lru_list = lru_list_fp
        free_registers = fp_registers
    else:
        lru_list = lru_list_int
        free_registers = integer_registers

    if var in register_descriptor.values():
        # Already has a register allocated
        register = address_descriptor[var]
    else:
        if len(free_registers) == 0:
            # No free register available
            register = lru_list.pop(0)
            if register[1] == "s":
                remember_to_restore[-1].append(f"\tlw\t{register},\t{offset}($fp)")
                removed_registers[register_descriptor[register]] = ("lw", f"{offset}($fp)")
                print_text("\tsw\t" + register + ",\t" + f"{offset}($fp)")
                offset -= 4
                print_text("\tla\t$sp,\t-4($sp)")
            elif register.startswith("$f"):
                remember_to_restore[-1].append(f"\tl.s\t{register},\t{offset}($fp)")
                removed_registers[register_descriptor[register]] = ("l.s", f"{offset}($fp)")
                print_text("\ts.s\t" + register + ",\t" + f"{offset}($fp)")
                offset -= 4
                print_text("\tla\t$sp,\t-4($sp)")
        else:
            # Free registers available
            register = free_registers.pop()

            if register[1] == "s":
                remember_to_restore[-1].append(f"\tlw\t{register},\t{offset}($fp)")
                removed_registers[register_descriptor[register]] = ("lw", f"{offset}($fp)")
                print_text("\tsw\t" + register + ",\t" + f"{offset}($fp)")
                offset -= 4
                print_text("\tla\t$sp,\t-4($sp)")
            elif register.startswith("$f"):
                remember_to_restore[-1].append(f"\tl.s\t{register},\t{offset}($fp)")
                removed_registers[register_descriptor[register]] = ("l.s", f"{offset}($fp)")
                print_text("\ts.s\t" + register + ",\t" + f"{offset}($fp)")
                offset -= 4
                print_text("\tla\t$sp,\t-4($sp)")

            if var in removed_registers:
                instr, loc = removed_registers[var]
                print_text("\t" + instr + "\t" + register + ",\t" + loc)
                del removed_registers[var]

        address_descriptor[var] = register
        busy_registers.append(register)
        register_descriptor[register] = var
        registers_in_block[-1].append(register)

    try:
        while True:
            lru_list.remove(register)
    except ValueError:
        lru_list.append(register)

    return register, offset


def store_temp_regs_in_use(offset: int) -> int:
    global busy_registers, removed_registers, register_descriptor
    saves = 0
    for reg in busy_registers:
        if reg[1] == "t":
            removed_registers[register_descriptor[reg]] = ("lw", f"{offset}($fp)")
            ## Store the current value
            print_text("\tsw\t" + reg + ",\t" + f"{offset}($fp)")
            register_descriptor[reg] = None
            offset -= 4
            saves += 1
    if saves >= 1:
        print_text(f"\tla\t$sp,\t-{4 * saves}($sp)")
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
        print_text(l)


# NOTE:
# 3. Handle data type sizes properly. All instructions wont be lw
# 4. IMP: int main() should be present and with no other form of definition


def generate_mips_from_3ac(code):
    global STATIC_NESTING_LVL, DYNAMIC_NESTING_LVL

    # print_text("## MIPS Assembly Code\n")

    print_text()
    print_text("main:")
    print_text("\tsw\t$fp,\t-4($sp)")
    print_text("\tsw\t$ra,\t-8($sp)")
    print_text("\tla\t$fp,\t0($sp)")
    print_text("\tla\t$sp,\t-4($sp)")
    # Function Call
    print_text("\tjal\tmain____")
    print_text("\tmove\t$a0,\t$v0")
    print_text("\tli\t$v0,\t1")
    print_text("\tsyscall")
    print_text("\tli\t$v0,\t10")
    print_text("\tsyscall")

    tabname_mapping = get_tabname_mapping()
    gtab = get_global_symtab()

    # Generate the data part for the global variables
    # print_text(".data")
    for var, entry in gtab._symtab_variables.items():
        # TODO: Might need to deal with alignment issues
        print_data(f"\t{var}:\t.space\t{entry['size']}")
    # print_text()

    # Generate the text part
    # print_text(".text")
    current_symbol_table = gtab

    first_pushparam = True
    all_pushparams = []
    offset = 0

    for part in code:
        for i, c in enumerate(part):
            print_text("\n# " + " ".join(c))
            if len(c) == 1:
                if c[0].endswith(":"):
                    # Label
                    print_text(c[0].replace("(", "__").replace(")", "__").replace(",", "_"))
                elif c[0] == "ENDFUNC":
                    load_registers_on_function_return("sp")
                    print_text("\tla\t$sp,\t0($fp)")
                    print_text("\tlw\t$ra,\t-8($sp)")
                    print_text("\tlw\t$fp,\t-4($sp)")
                    print_text("\tjr\t$ra")  # return
                    free_registers_in_block()
                    # STATIC_NESTING_LVL -= 1

                elif c[0] == "RETURN":
                    DYNAMIC_NESTING_LVL -= 1
                    load_registers_on_function_return("sp")
                    print_text("\tla\t$sp,\t0($fp)")
                    print_text("\tlw\t$ra,\t-8($sp)")
                    print_text("\tlw\t$fp,\t-4($sp)")
                    print_text("\tjr\t$ra")  # return

                else:
                    print_text(c)

            elif len(c) == 2:
                if c[0] == "SYMTAB":
                    # Pop Symbol Table
                    current_symbol_table = current_symbol_table.parent

                elif c[0] == "BEGINFUNC":
                    # STATIC_NESTING_LVL += 1
                    # Has the overall size for the function
                    print_text("\tsw\t$fp,\t-4($sp)")  # dynamic link (old fp)
                    print_text("\tsw\t$ra,\t-8($sp)")
                    print_text("\tla\t$fp,\t0($sp)")
                    offset = store_registers_on_function_call() - int(c[1].split(",")[1])
                    print_text(f"\tla\t$sp,\t{offset}($sp)")
                    create_new_register_block()

                elif c[0] == "RETURN":
                    DYNAMIC_NESTING_LVL -= 1
                    is_num, instr = is_number(c[1], True)

                    if is_num:
                        _type = type_of_number(c[1])
                        reg = "$f0" if _type in ("float", "double") else "$v0"
                        print_text(instr(reg))
                    else:
                        t, offset, entry = get_register(c[1], current_symbol_table, offset, True)
                        _type = entry["type"]
                        reg, instr = (
                            ("$f0", "mov.d")
                            if _type == "double"
                            else (
                                ("$f0", "mov.s")
                                if _type == "float"
                                else (("$v0", "move") if _type == "int" else (1, 1))
                            )
                        )
                        if reg == 1:
                            # custom type
                            # type_details = current_symbol_table.lookup_type(_type)
                            stack_pushables = _return_stack_custom_types(c[1], _type, current_symbol_table)
                            _o = -12
                            for (var, s, _t) in stack_pushables:
                                reg, offset = get_register(var, current_symbol_table, offset)
                                save_instr = SAVE_INSTRUCTIONS[_t]
                                print_text(f"\t{save_instr}\t{reg},\t{_o}($fp)")
                                _o -= int(s)
                        else:
                            print_text(f"\t{instr}\t{reg},\t{t}")

                    load_registers_on_function_return("sp")
                    print_text("\tla\t$sp,\t0($fp)")
                    print_text("\tlw\t$ra,\t-8($sp)")
                    print_text("\tlw\t$fp,\t-4($sp)")
                    print_text("\tjr\t$ra")

                elif c[0] == "PUSHPARAM":
                    if first_pushparam:
                        first_pushparam = False
                        offset = store_temp_regs_in_use(offset)
                    # We should ideally be using the a0..a2 registers, but for ease of use we will
                    # push everything into the stack
                    is_num, instr = is_number(c[1], True)
                    t, offset, entry = get_register(c[1], current_symbol_table, offset, True)
                    if is_num:
                        _type = type_of_number(c[1])
                        print_text(instr(t))
                    else:
                        _type = entry["type"]
                    instr, s = ("s.s", 4) if _type == "float" else (("s.d", 8) if _type == "double" else ("sw", 4))
                    all_pushparams.extend([f"\t{instr}\t{t},\t-{s}($sp)", f"\tla\t$sp,\t-{s}($sp)"])

                elif c[0] == "POPPARAMS":
                    first_pushparam = True

                elif c[0] == "GOTO":
                    print_text(f"\tj\t{c[1]}")
                else:
                    print_text(c)

            elif len(c) == 3:
                if c[1] == ":=":
                    # Assignment
                    _, entry = convert_varname(c[0], current_symbol_table)
                    if get_default_value(entry["type"]) is None:
                        all_fields_lhs = _return_stack_custom_types(c[0], entry["type"], current_symbol_table)
                        all_fields_rhs = _return_stack_custom_types(c[2], entry["type"], current_symbol_table)
                        for ((l, _, t1), (r, _, t2)) in zip(all_fields_lhs, all_fields_rhs):
                            assert t1 == t2, AssertionError(f"Something went wrong {t1} != {t2}")
                            reg1, offset = get_register(l, current_symbol_table, offset)
                            reg2, offset = get_register(r, current_symbol_table, offset)
                            instr = MOVE_INSTRUCTIONS[t1]
                            # print_text(f"# {reg1} -> {l}, {reg2} -> {r}")
                            print_text(f"\t{instr}\t{reg1},\t{reg2}")
                    else:    
                        t1, offset, entry = get_register(c[0], current_symbol_table, offset, True)

                        is_num, instr = is_number(c[2], True)

                        if is_num:
                            # Assignment with a constant
                            print_text(instr(t1))
                        else:
                            t2, offset = get_register(c[2], current_symbol_table, offset)
                            _type = entry["type"]
                            instr = MOVE_INSTRUCTIONS[_type]
                            print_text(f"\t{instr}\t{t1},\t{t2}")

                elif c[0] == "SYMTAB":
                    # Symbol Table
                    current_symbol_table = tabname_mapping[c[2]]
                    params = current_symbol_table._paramtab
                    off = 0
                    for p in params:
                        entry = current_symbol_table.lookup(p)
                        t, offset, entry = get_register(entry["name"], current_symbol_table, offset, True)
                        instr = "l.s" if entry["type"] == "float" else ("l.d" if entry["type"] == "double" else "lw")
                        print_text(f"\t{instr}\t{t},\t{off}($fp)")
                        off += entry["size"]
                else:
                    print_text(c)

            elif len(c) == 4:
                if c[1] == ":=":
                    # typecast expression
                    if c[2].startswith("("):
                        datatype = c[2].replace("(", "").replace(")", "")
                        offset = type_cast_mips(c, datatype, current_symbol_table, offset)

                else:
                    print_text(c)

            elif len(c) == 5:
                if c[1] == ":=":
                    if c[2] == "CALL":
                        # Function Call
                        DYNAMIC_NESTING_LVL += 1
                        if first_pushparam:
                            offset = store_temp_regs_in_use(offset)
                        for params in all_pushparams:
                            print_text(params)
                        all_pushparams = []
                        print_text(f"\tjal\t{c[3].replace('(', '__').replace(')', '__').replace(',', '_')}")
                        # caller pops the arguments
                        t1, offset, entry = get_register(c[0], current_symbol_table, offset, True)
                        _type = entry["type"]

                        reg = RETURN_REGISTERS.get(_type, None)
                        if reg is None:
                            stack_pushables = _return_stack_custom_types(c[0], _type, current_symbol_table)
                            _o = -12
                            for (var, s, _t) in stack_pushables:
                                reg, offset = get_register(var, current_symbol_table, offset)
                                load_instr = LOAD_INSTRUCTIONS[_t]
                                print_text(f"\t{load_instr}\t{reg},\t{_o}($sp)")
                                _o -= int(s)
                        else:
                            instr = MOVE_INSTRUCTIONS[_type]                
                            print_text(f"\t{instr}\t{t1},\t{reg}")
                        print_text(f"\tla\t$sp,\t{c[4]}($sp)")
                        first_pushparam = True

                    else:
                        # Assignment + An op
                        op = c[3]
                        t1, offset, entry3 = get_register(c[0], current_symbol_table, offset, True)

                        is_num, instr = is_number(c[2], True)
                        t2, offset, entry1 = get_register(c[2], current_symbol_table, offset, True)
                        if is_num:
                            print_text(instr(t2))

                        is_num, instr = is_number(c[4], True)
                        t3, offset, entry2 = get_register(c[4], current_symbol_table, offset, True)
                        if is_num:
                            print_text(instr(t3))

                        _type = (
                            entry1["type"]
                            if entry1 is not None
                            else (entry2["type"] if entry2 is not None else entry3["type"])
                        )

                        instrs = get_mips_instr_from_binary_op(op, _type, t2, t3, t1)
                        for instr in instrs:
                            print_text(instr)

            elif len(c) == 6:
                if c[0] == "IF" and c[4] == "GOTO":  # If reg != 0 goto label
                    op = c[2]
                    t1, offset = get_register(c[1], current_symbol_table, offset)

                    label = get_tmp_label()

                    # print_text(f"\t{instr_op}\t{t3},\t{t1},\t$0")
                    print_text(f"\tbne\t{t1},\t$0,\t{label}")
                    print_text(f"\tj\t{c[5]}")
                    print_text(f"{label}:")

            else:
                print_text(c)

    print_assembly()


def _return_stack_custom_types(v, vtype, symtab):
    entry_type = symtab.lookup_type(vtype)
    var_name_sizes = []
    for f, t in zip(entry_type["field names"], entry_type["field types"]):
        d = get_default_value(t)
        if d is not None:
            s = DATATYPE2SIZE[t.upper()]
            var_name_sizes += [[f"{v}.{f}", str(s), t]]
        else:
            var_name_sizes += _return_stack_custom_types(f"{v}.{f}", t, symtab)
    return var_name_sizes


def print_assembly():
    # Dump the Assembly
    global DATA_SECTION, TEXT_SECTION
    print(".data")
    for data in DATA_SECTION:
        print(data)
    print()
    print(".text")
    for text in TEXT_SECTION:
        print(text)


reset_registers()