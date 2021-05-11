from copy import deepcopy

from symtab import (
    SymbolTable,
    compute_offset_size,
    compute_storage_size,
    get_current_symtab,
    get_global_symtab,
    get_tabname_mapping,
    get_tmp_label,
    get_default_value,
    DATATYPE2SIZE,
)

import random

# STATIC_NESTING_LVL = -1
DYNAMIC_NESTING_LVL = -1
declared_variables = []

BINARY_REL_OPS = ["==", ">", "<", ">=", "<=", "!="]

UNARY_OPS_TO_INSTR = {"int": {"-": "neg"}, "char": {"-": "neg"}, "float": {"-": "neg.s"}, "double": {"-": "neg.d"}}

BINARY_OPS_TO_INSTR = {
    "char": {
        "+": "add",
        "-": "sub",
        "*": "mul",
        "/": "div",
        "<=": "sle",
        "<": "slt",
        "!=": "sne",
        "==": "seq",
        ">": "sgt",
        ">=": "sge",
    },
    "int": {
        "+": "add",
        "-": "sub",
        "*": "mul",
        "/": "div",
        "<=": "sle",
        "<": "slt",
        "!=": "sne",
        "==": "seq",
        ">": "sgt",
        ">=": "sge",
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
        ">": "c.gt.s",
        ">=": "c.ge.s",
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
        ">": "c.gt.d",
        ">=": "c.ge.d",
    },
}

SAVE_INSTRUCTIONS = {
    "char": "sw",
    "int": "sw",
    "void": "sw",
    "long": "sd",
    "float": "s.s",
    "double": "s.d",
}

LOAD_INSTRUCTIONS = {
    "char": "lw",
    "int": "lw",
    "void": "lw",
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
    "void": "move",
    "long": "move",
    "float": "mov.s",
    "double": "mov.d",
}


DATA_SECTION = []
TEXT_SECTION = []
BACKPATCH_SECTION = []
BACKPATCH_OFFSET = -1
BACKPATCH_INDEX = -1
data_number_counter = -1


def get_tmp_data():
    global data_number_counter
    data_number_counter += 1
    return f"__tmp_data_{data_number_counter}"


DATA_TO_LABEL = {}


def print_data(*s):
    s = " ".join(s)
    global DATA_SECTION, DATA_TO_LABEL
    try:
        seq = s.split(" ")
        DATA_TO_LABEL[seq[2]] = seq[0][:-1]
    except:
        pass
    DATA_SECTION.append(s)


def print_text(*s):
    s = " ".join(s)
    global TEXT_SECTION
    TEXT_SECTION.append(s)


def print_backpatch(*s):
    s = " ".join(s)
    global BACKPATCH_SECTION
    BACKPATCH_SECTION.append(s)


def dump_backpatch():
    global BACKPATCH_SECTION, TEXT_SECTION
    idx = BACKPATCH_INDEX
    TEXT_SECTION = TEXT_SECTION[:idx] + BACKPATCH_SECTION + TEXT_SECTION[idx:]
    BACKPATCH_SECTION = []


def get_mips_instr_from_binary_op(op: str, t: str, reg1: str, reg2: str, reg3: str) -> str:
    # reg3 := reg1 op reg2
    global BINARY_OPS_TO_INSTR, BINARY_REL_OPS
    if op == "%":
        div_op = BINARY_OPS_TO_INSTR[t]["/"]
        return [f"\t{div_op}\t{reg1},\t{reg2}", f"\tmfhi\t{reg3}"]
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
                if str(s) in DATA_TO_LABEL:
                    var = DATA_TO_LABEL[str(s)]
                else:
                    var = get_tmp_data()
                    print_data(f"{var}: .float {s}")
                return True, lambda reg: "\tl.s\t" + reg + ",\t" + var
            else:
                return True
        else:
            if s == "0":
                return (
                    True if not return_instr else (True, lambda reg: "" if reg == "$0" else "\tmove\t" + reg + ",\t$0")
                )
            return True if not return_instr else (True, lambda reg: "\tli\t" + reg + ",\t" + s)
    except ValueError:
        return False if not return_instr else (False, lambda reg: "")


def is_char(s: str):
    if s[0] == "'" and s[-1] == "'":
        return True, lambda reg: "\tli\t" + reg + ",\t" + s
    return False, None


def reset_registers():
    global address_descriptor, activation_record, register_descriptor, free_registers, remember_to_restore
    global parameter_descriptor, busy_registers, lru_list_fp, lru_list_int, registers_in_block, removed_registers
    global integer_registers, fp_registers, free_registers_int
    global register_loader, register_saver, global_vars, count_which_reg_used
    address_descriptor = dict()
    count_which_reg_used = dict()
    register_loader = dict()
    register_saver = dict()
    activation_record = []
    # We are not using a* for passing arguments so we might as well use them for operations
    integer_registers = [f"$t{i}" for i in range(10)] + [f"$s{i}" for i in range(8)]
    fp_registers = [f"$f{i}" for i in list(range(30, 2, -2))]
    free_registers = integer_registers + fp_registers
    # FIXME: Maybe not do this
    random.shuffle(integer_registers)
    random.shuffle(fp_registers)
    register_descriptor = {reg: None for reg in free_registers}
    removed_registers = dict()
    registers_in_block = [[]]
    parameter_descriptor = {"$a1": None, "$a2": None, "$a3": None}
    busy_registers = []
    lru_list_fp = []
    lru_list_int = []
    remember_to_restore = [[]]
    global_vars = dict()  # varname -> tmp_data_id


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
        elif t1 == "char":
            return ["move"]
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
    elif t2 == "char":
        if t1 == "int":
            return ["move"]
        elif t1 == "float":
            return ["cvt.w.s", "mfc1"]
        elif t1 == "double":
            return ["cvt.w.d", "mfc1.d"]
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
    elif len(instrs) == 1:
        print_text(f"\t{instrs[0]}\t{t1},\t{t2}")

    return offset


def requires_fp_register(val, entry):
    if entry is not None:
        return (entry["type"] in ("float", "double", "long double"), entry["type"])
    else:
        v = eval(val)
        if isinstance(v, float):
            return True, "float"
        else:
            return False, "int"


def get_register(var, current_symbol_table, offset, return_entry=False, no_flush=False):
    entry = None
    if not is_number(var) and not is_char(var)[0]:
        var, entry = convert_varname(var, current_symbol_table)
    reg, offset = simple_register_allocator(var, current_symbol_table, offset, entry, no_flush)
    return (reg, offset) if not return_entry else (reg, offset, entry)


def simple_register_allocator(var: str, current_symbol_table: SymbolTable, offset: int, entry, no_flush):
    global register_descriptor, address_descriptor, registers_in_block, removed_registers
    global lru_list_int, lru_list_fp, remember_to_restore, register_saver, register_loader
    global global_vars, count_which_reg_used, BACKPATCH_OFFSET

    # FIXME: Global mutation and stuff....

    req_fp, _type = requires_fp_register(var, entry)
    _s = DATATYPE2SIZE[_type.upper()]
    if req_fp:
        lru_list = lru_list_fp
        free_registers = fp_registers
    else:
        lru_list = lru_list_int
        free_registers = integer_registers
        if entry is None and eval(var) == 0:
            return "$0", offset

    sp = var.split("-")
    is_global = sp[1] == "GLOBAL" if len(sp) == 3 else False

    if var in register_descriptor.values():
        # Already has a register allocated
        register = address_descriptor[var]
    else:
        if len(free_registers) == 0:
            # No free register available
            register = lru_list.pop(0)
            load_instr = register_loader[register]
            save_instr = register_saver[register]
        else:
            # Free registers available
            register = free_registers.pop()
            load_instr = LOAD_INSTRUCTIONS[_type]
            save_instr = SAVE_INSTRUCTIONS[_type]

        no_flush = var in removed_registers or no_flush

        if register in count_which_reg_used:
            # Register in use in the current block
            removed_registers[register_descriptor[register]] = (load_instr, f"{offset}($fp)")
            print_text(f"\t{save_instr}\t" + register + ",\t" + f"{offset}($fp)")
            print_text(f"\tla\t$sp,\t-{_s}($sp)")
            offset -= _s
            if not no_flush:
                if req_fp:
                    print_text(f"\t{load_instr}\t{register},\t__zero_data")
                else:
                    print_text(f"\tli\t{register},\t0")
        else:
            # Register is not being used rn in the current block
            # If it is a saved register we need to backpatch it
            if register.startswith("$s") or register.startswith("$f"):
                # Saved Registers. All fp registers are saved regs
                remember_to_restore[-1].append(f"\t{load_instr}\t{register},\t{BACKPATCH_OFFSET}($fp)")
                print_backpatch(f"\t{save_instr}\t" + register + ",\t" + f"{BACKPATCH_OFFSET}($fp)")
                # print_backpatch(f"\tla\t$sp,\t-{_s}($sp)")
                BACKPATCH_OFFSET -= _s
                if not no_flush:
                    if req_fp:
                        print_text(f"\t{load_instr}\t{register},\t__zero_data")
                    else:
                        print_text(f"\tli\t{register},\t0")

        if is_global:
            print_text(f"\t{load_instr}\t{register},\t{var.split('-')[2]}")

        if var in removed_registers:
            instr, loc = removed_registers[var]
            print_text("\t" + instr + "\t" + register + ",\t" + loc)
            if removed_registers.get(var, None):
                del removed_registers[var]

        address_descriptor[var] = register
        busy_registers.append(register)
        register_descriptor[register] = var
        registers_in_block[-1].append(register)
        register_loader[register] = LOAD_INSTRUCTIONS[_type]
        register_saver[register] = SAVE_INSTRUCTIONS[_type]

    try:
        lru_list.remove(register)
    except:
        pass
    lru_list.append(register)

    if register in count_which_reg_used:
        count_which_reg_used[register] += 1
    else:
        count_which_reg_used[register] = 1

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
    global register_loader, register_saver, lru_list_fp, lru_list_int, integer_registers, fp_registers
    for reg in registers_in_block[-1]:
        var = register_descriptor[reg]
        register_descriptor[reg] = None
        if register_saver.get(reg, None):
            del register_saver[reg]
        if register_loader.get(reg, None):
            del register_loader[reg]
        busy_registers.remove(reg)

        if reg.startswith("$f"):
            lru_list = lru_list_fp
            fp_registers.append(reg)
        else:
            lru_list = lru_list_int
            integer_registers.append(reg)

        try:
            lru_list.remove(reg)
        except ValueError:
            continue

    registers_in_block = registers_in_block[:-1]
    remember_to_restore = remember_to_restore[:-1]


def create_new_register_block():
    global registers_in_block, remember_to_restore, count_which_reg_used
    registers_in_block += [[]]
    remember_to_restore += [[]]
    count_which_reg_used = dict()


def store_registers_on_function_call() -> int:
    global removed_registers, busy_registers, register_descriptor
    off = -12  # already stored fp and ra
    return off


def load_registers_on_function_return(p_stack: str):
    global stored_registers, remember_to_restore
    for l in remember_to_restore[-1]:
        print_text(l)


def size_to_mips_standard(s: int, fp: bool) -> str:
    if not fp:
        if s == 1:
            return "byte"
        elif s == 2:
            return "half"
        elif s == 4:
            return "word"
    else:
        if s == 4:
            return "float"
        elif s == 8:
            return "double"
    raise Exception(f"No corresponding standard for size = {s}")


###############################################  File IO functions ###################################################################
def read_from_file(fd_reg, buf, len):
    print_text("li\t$v0,\t14")  # syscall number to read
    print_text(f"move\t$a0,\t{fd_reg}")  # register for file descriptor
    print_text(f"la\t$a1,\t{buf}")  # address of buffer to which to read
    print_text(f"li\t$a2,\t{len}")  # buffer length
    print_text("syscall")


def write_to_file(fd_reg, buf, len):
    print_text("li\t$v0,\t15")  # syscall number to read
    print_text(f"move\t$a0,\t{fd_reg}")  # register for file descriptor
    print_text(f"la\t$a1,\t{buf}")  # buffer address
    print_text(f"li\t$a2,\t{len}")  # buffer length
    print_text("syscall")


def open_file(fil_nm, fd_reg, mode):  # mode: 0->read, 1->write
    print_text("li\t$v0,\t13")  # syscall number to open
    print_text(f"la\t$a0,\t{fil_nm}")
    print_text(f"li\t$a1,\t{mode}")
    print_text("li\t$a2,\t0")
    print_text("syscall")  # file descriptor returned in $v0
    print_text(f"move\t{fd_reg},\t$v0")  # save the file descriptor


def close_file(fd_reg):
    print_text("li\t$v0,\t16")
    print_text(f"move\t$a0,\t{fd_reg}")
    print_text("syscall")


#########################################################################################################################################

# NOTE:
# It is important to initialize arrays. Default values are not guaranteed for arrays
# IMP: int main() should be present and with no other form of definition


def generate_mips_from_3ac(code):
    global STATIC_NESTING_LVL, DYNAMIC_NESTING_LVL, global_vars, BACKPATCH_OFFSET, BACKPATCH_INDEX

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

    print_data("__zero_data: .float 0.0")
    # Generate the data part for the global variables
    # print_text(".data")
    for var, entry in gtab._symtab_variables.items():
        # TODO: Might need to deal with alignment issues
        # TODO: intialized global arrays
        # if entry["is_array"] == True:
        #     if entry["type"] == "int":
        #         print_data(f"\t{var}:\t.word\t{}")
        #     elif if entry["type"] == "char":
        #         print_data(f"\t{var}:\t.byte\t{}")

        # print_data(f"\t{var}:\t.space\t{entry['size']}")
        pass

    # print_text()

    # Generate the text part
    # print_text(".text")
    current_symbol_table = gtab

    first_pushparam = True
    all_pushparams = []
    offset = 0
    global_scope = True
    backpatching_offset = -1

    for part in code:
        for i, c in enumerate(part):
            # print("\n# " + " ".join(c))
            print_text("\n# " + " ".join(c))
            if len(c) == 1:
                if c[0].endswith(":"):
                    global_scope = False
                    # Label
                    print_text(c[0].replace("(", "__").replace(")", "__").replace(",", "_"))
                elif c[0] == "ENDFUNC":
                    dump_backpatch()
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
                    sp = c[1].split(",")
                    offset = store_registers_on_function_call() - int(sp[1])
                    BACKPATCH_OFFSET = offset
                    offset -= int(sp[0])
                    print_text(f"\tla\t$sp,\t{offset}($sp)")
                    BACKPATCH_INDEX = len(TEXT_SECTION)
                    create_new_register_block()

                elif c[0] == "RETURN":
                    DYNAMIC_NESTING_LVL -= 1
                    is_num, instr = is_number(c[1], True)
                    is_ch, instr2 = is_char(c[1])
                    if is_num:
                        _type = type_of_number(c[1])
                        reg = RETURN_REGISTERS[_type]
                        print_text(instr(reg))
                    elif is_ch:
                        reg = RETURN_REGISTERS["char"]
                        print_text(instr(reg))
                    else:
                        entry = current_symbol_table.lookup(c[1])
                        _type = entry["type"]
                        if entry["type"].startswith("struct"):
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
                            t, offset, entry = get_register(c[1], current_symbol_table, offset, True)
                            _type = entry["type"]
                            reg = RETURN_REGISTERS[_type]
                            instr = MOVE_INSTRUCTIONS[_type]
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
                    is_num, instr1 = is_number(c[1], True)
                    is_ch, instr2 = is_char(c[1])
                    t, offset, entry = get_register(
                        c[1], current_symbol_table, offset, True, no_flush=(is_num or is_ch)
                    )
                    if is_num:
                        _type = type_of_number(c[1])
                        print_text(instr1(t))
                    elif is_ch:
                        _type = "char"
                        print_text(instr2(t))
                    else:
                        _type = entry["type"]
                    instr = SAVE_INSTRUCTIONS[_type]
                    s = 4  # wont work for double
                    all_pushparams.extend([f"\t{instr}\t{t},\t-{s}($sp)", f"\tla\t$sp,\t-{s}($sp)"])

                elif c[0] == "POPPARAMS":
                    first_pushparam = True

                elif c[0] == "GOTO":
                    print_text(f"\tj\t{c[1]}")

                elif c[0] == "ASSEMBLY_DIRECTIVE":
                    instr = "\t".join(c[1][1:-1].split(" "))
                    print_text("\t" + instr)

                else:
                    print_text(c)

            elif len(c) == 3:
                if c[1] == ":=":
                    # Assignment
                    if c[0].endswith("]"):  # arr[x] := y
                        t0, offset, entry = get_register(
                            c[0].split("[")[0], current_symbol_table, offset, True, no_flush=True
                        )  # reg of arr

                        index = c[0].split("[")[1].split("]")[0]
                        is_num, instr = is_number(index, True)
                        t1, offset = get_register(index, current_symbol_table, offset)  # reg of x
                        print_text(instr(t1))

                        is_num, instr = is_number(c[2], True)
                        t2, offset = get_register(c[2], current_symbol_table, offset)  # reg of y
                        print_text(instr(t2))

                        req_fp, _type = requires_fp_register(c[2], entry)
                        load_instr = LOAD_INSTRUCTIONS[_type]
                        save_instr = SAVE_INSTRUCTIONS[_type]

                        print_text(f"\tsll\t{t1},\t{t1},\t2")
                        print_text(f"\tadd\t{t0},\t{t0},\t{t1}")
                        print_text(f"\t{save_instr}\t{t2},\t0({t0})")
                        continue

                    if c[0].startswith("*"):  # *ptr = x
                        t0, offset, entry = get_register(
                            c[0].split("*")[1], current_symbol_table, offset, True, no_flush=True
                        )  # reg of ptr

                        is_num, instr = is_number(c[2], True)
                        t2, offset = get_register(c[2], current_symbol_table, offset)  # reg of x
                        print_text(instr(t2))

                        req_fp, _type = requires_fp_register(c[2], entry)
                        load_instr = LOAD_INSTRUCTIONS[_type]
                        save_instr = SAVE_INSTRUCTIONS[_type]

                        print_text(f"\t{save_instr}\t{t2},\t0({t0})")
                        continue

                    _, entry = convert_varname(c[0], current_symbol_table)
                    _type = entry["type"]
                    if _type.startswith("struct"):
                        if global_scope:
                            raise Exception("Only native datatypes can be directly assigned in global scope")
                        # Struct
                        all_fields_lhs = _return_stack_custom_types(c[0], entry["type"], current_symbol_table)
                        all_fields_rhs = _return_stack_custom_types(c[2], entry["type"], current_symbol_table)
                        for ((l, _, t1), (r, _, t2)) in zip(all_fields_lhs, all_fields_rhs):
                            assert t1 == t2, AssertionError(f"Something went wrong {t1} != {t2}")
                            reg1, offset = get_register(l, current_symbol_table, offset, no_flush=True)
                            reg2, offset = get_register(r, current_symbol_table, offset)
                            instr = MOVE_INSTRUCTIONS[t1]
                            # print_text(f"# {reg1} -> {l}, {reg2} -> {r}")
                            print_text(f"\t{instr}\t{reg1},\t{reg2}")
                    else:
                        is_num, instr = is_number(c[2], True)
                        is_ch, instr2 = is_char(c[2])

                        if is_num or is_ch:
                            # Assignment with a constant
                            instr = instr if is_num else instr2
                            if global_scope:
                                entry = current_symbol_table.lookup(c[0])
                                fp = requires_fp_register(entry["value"], entry)[0]
                                print_data(f"{c[0]}: .{size_to_mips_standard(entry['size'], fp)} {entry['value']}")
                            else:
                                t1, offset, entry = get_register(
                                    c[0], current_symbol_table, offset, True, no_flush=True
                                )
                                print_text(instr(t1))
                        else:
                            t1, offset, entry = get_register(c[0], current_symbol_table, offset, True, no_flush=True)
                            if entry["is_array"] == True:
                                print_text(f"\tla\t{t1},\t0($sp)")
                                print_text(f"\tla\t$sp,\t-{entry['size']}($sp)")

                            if global_scope:
                                raise Exception("Non constant initialization in global scope")

                            if not c[2] == "NULL":
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
                        t, offset, entry = get_register(
                            entry["name"], current_symbol_table, offset, True, no_flush=True
                        )
                        instr = LOAD_INSTRUCTIONS[entry["type"]]
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

                    elif c[2].startswith("&"):  # ref
                        t1, offset, entry = get_register(c[0], current_symbol_table, offset, True)
                        req_fp, _type = requires_fp_register(c[0], entry)
                        load_instr = LOAD_INSTRUCTIONS[_type]
                        save_instr = SAVE_INSTRUCTIONS[_type]

                        if c[3].endswith("]"):  # & arr [x]
                            arr_name = c[3].split()[0]
                            t2, offset = get_register(arr_name, current_symbol_table, offset)

                            index = c[3].split()[1].replace("[", "").replace("]", "")
                            is_num, instr = is_number(index, True)
                            t3, offset = get_register(index, current_symbol_table, offset)
                            print_text(instr(t3))
                            print_text(f"\tsll\t{t3},\t{t3},\t2")
                            print_text(f"\tadd\t{t2},\t{t2},\t{t3}")
                            print_text(f"\t{load_instr}\t{t1},\t0({t2})")
                        else:
                            # doesn't work yet
                            t3, offset = get_register(c[3], current_symbol_table, offset)
                            print_text(f"\t{load_instr}\t{t1},\t{t3}")

                    elif c[2].startswith("*"):  # deref
                        t1, offset, entry = get_register(c[0], current_symbol_table, offset, True)
                        req_fp, _type = requires_fp_register(c[0], entry)
                        load_instr = LOAD_INSTRUCTIONS[_type]
                        save_instr = SAVE_INSTRUCTIONS[_type]

                        t2, offset = get_register(c[3], current_symbol_table, offset)
                        print_text(f"\t{load_instr}\t{t1},\t0({t2})")

                    elif c[3].startswith("["):  # array indexing
                        t0, offset, entry = get_register(c[0], current_symbol_table, offset, True)
                        req_fp, _type = requires_fp_register(c[0], entry)
                        load_instr = LOAD_INSTRUCTIONS[_type]
                        save_instr = SAVE_INSTRUCTIONS[_type]

                        t1, offset, entry_arr = get_register(c[2], current_symbol_table, offset, True)

                        ind = c[3].replace("[", "").replace("]", "")
                        is_num, instr = is_number(ind, True)
                        t2, offset = get_register(ind, current_symbol_table, offset)

                        print_text(instr(t2))
                        print_text(f"\tsll\t{t2},\t{t2},\t2")
                        print_text(f"\tadd\t{t1},\t{t1},\t{t2}")
                        print_text(f"\t{load_instr}\t{t0},\t({t1})")

                    elif c[2] == "-":
                        t0, offset, entry = get_register(c[0], current_symbol_table, offset, True, no_flush=True)
                        neg_instr = UNARY_OPS_TO_INSTR[entry["type"]][c[2]]
                        is_const, instr = is_number(c[3], True)
                        if not is_const:
                            is_const, instr = is_char(c[3])
                        t1, offset = get_register(c[3], current_symbol_table, offset)
                        if is_const:
                            print_text(instr(t1))
                        print_text(f"\t{neg_instr}\t{t0},\t{t1}")

                    elif c[2] == "+":
                        t0, offset, entry = get_register(c[0], current_symbol_table, offset, True, no_flush=True)
                        pos_instr = MOVE_INSTRUCTIONS[entry["type"]]
                        is_const, instr = is_number(c[3], True)
                        if not is_const:
                            is_const, instr = is_char(c[3])
                        t1, offset = get_register(c[3], current_symbol_table, offset, no_flush=is_const)
                        if is_const:
                            print_text(instr(t1))
                        print_text(f"\t{pos_instr}\t{t0},\t{t1}")

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
                        entry = current_symbol_table.lookup(c[0])
                        _type = entry["type"]

                        reg = RETURN_REGISTERS.get(_type, None)
                        if reg is None and _type != "void":
                            stack_pushables = _return_stack_custom_types(c[0], _type, current_symbol_table)
                            _o = -12
                            for (var, s, _t) in stack_pushables:
                                reg, offset = get_register(var, current_symbol_table, offset, no_flush=True)
                                load_instr = LOAD_INSTRUCTIONS[_t]
                                print_text(f"\t{load_instr}\t{reg},\t{_o}($sp)")
                                _o -= int(s)
                        elif _type != "void":
                            t1, offset, entry = get_register(c[0], current_symbol_table, offset, True, no_flush=True)
                            instr = MOVE_INSTRUCTIONS[_type]
                            print_text(f"\t{instr}\t{t1},\t{reg}")
                        print_text(f"\tla\t$sp,\t{c[4]}($sp)")
                        first_pushparam = True

                    else:
                        # Assignment + An op
                        op = c[3]
                        t1, offset, entry3 = get_register(c[0], current_symbol_table, offset, True, no_flush=True)

                        is_const, instr = is_number(c[2], True)
                        if not is_const:
                            is_const, instr = is_char(c[2])
                        t2, offset, entry1 = get_register(c[2], current_symbol_table, offset, True, no_flush=is_const)
                        if is_const:
                            print_text(instr(t2))

                        is_const, instr = is_number(c[4], True)
                        if not is_const:
                            is_const, instr = is_char(c[4])
                        t3, offset, entry2 = get_register(c[4], current_symbol_table, offset, True, no_flush=is_const)
                        if is_const:
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

                    is_const, instrs = is_number(c[1], True)
                    _type = None
                    if not is_const:
                        is_const, instrs = is_char(c[1])
                        if is_const:
                            _type = "char"
                    else:
                        _type = type_of_number(c[1])
                    t1, offset, entry = get_register(c[1], current_symbol_table, offset, True)
                    if _type is None:
                        _type = entry["type"]
                    if is_const:
                        print_text(instrs(t1))

                    is_const, instrs = is_number(c[3], True)
                    if not is_const:
                        is_const, instrs = is_char(c[3])
                    t2, offset = get_register(c[3], current_symbol_table, offset)
                    if is_const:
                        print_text(instrs(t2))

                    instr = BINARY_OPS_TO_INSTR[_type][op]
                    instr = "b" + instr[1:]
                    print_text(f"\t{instr}\t{t1},\t{t2},\t{c[5]}")

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
