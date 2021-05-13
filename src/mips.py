from copy import deepcopy
import numpy as np

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
        "&": "and",
        "|": "or",
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
    },
}

SAVE_INSTRUCTIONS = {
    "char": "sw",
    "int": "sw",
    "void": "sw",
    "long": "sw",
    "float": "s.s",
    "double": "s.d",
}

LOAD_INSTRUCTIONS = {
    "char": "lw",
    "int": "lw",
    "void": "lw",
    "long": "lw",
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
BACKPATCHES = []
BACKPATCH_OFFSET = None
BACKPATCH_INDEX = None
data_number_counter = -1
LOCAL_VAR_OFFSET = None
err_label = -1


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
    global BACKPATCH_SECTION, TEXT_SECTION, BACKPATCHES
    idx = BACKPATCH_INDEX
    TEXT_SECTION = TEXT_SECTION[:idx] + BACKPATCH_SECTION + TEXT_SECTION[idx:]
    BACKPATCH_SECTION = []
    BACKPATCHES = []


def get_mips_instr_from_binary_op(op: str, t: str, reg1: str, reg2: str, reg3: str) -> str:
    # reg3 := reg1 op reg2
    global BINARY_OPS_TO_INSTR, BINARY_REL_OPS
    if op == "%":
        div_op = BINARY_OPS_TO_INSTR[t]["/"]
        return [f"\t{div_op}\t{reg1},\t{reg2}", f"\tmfhi\t{reg3}"]
    if op in BINARY_REL_OPS and t in ("float", "double"):
        label1 = get_tmp_label()
        label2 = get_tmp_label()
        if op in (">=", ">"):
            op_mips = BINARY_OPS_TO_INSTR[t]["<" if op == ">=" else "<="]
            reg1, reg2 = reg2, reg1
        else:
            op_mips = BINARY_OPS_TO_INSTR[t][op]
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
        op_mips = BINARY_OPS_TO_INSTR[t][op]
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
    global register_loader, register_saver, global_vars, local_var_mapping, var_to_mem
    global prev_var_access
    prev_var_access = dict()
    address_descriptor = dict()
    local_var_mapping = dict()
    var_to_mem = dict()
    register_loader = dict()
    register_saver = dict()
    activation_record = []
    # We are not using a* for passing arguments so we might as well use them for operations
    integer_registers = [f"$t{i}" for i in range(10)] + [f"$s{i}" for i in range(8)]
    fp_registers = [f"$f{i}" for i in list(range(30, 2, -2))]
    free_registers = integer_registers + fp_registers
    # FIXME: Maybe not do this
    # random.shuffle(integer_registers)
    # random.shuffle(fp_registers)
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

    t1, offset = get_register(c[0], current_symbol_table, offset, no_flush=True)
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

    dump_value_to_mem(t1)

    return offset


def requires_fp_register(val, entry):
    if entry is not None:
        if entry["pointer_lvl"] >= 1 or entry["is_array"]:
            return False, "int"
        return (entry["type"] in ("float", "double", "long double"), entry["type"])
    else:
        v = eval(val)
        if isinstance(v, float):
            return True, "float"
        else:
            return False, "int"


def get_register(var, current_symbol_table, offset, return_entry=False, no_flush=False, no_load=False):
    entry = None
    if not is_number(var) and not is_char(var)[0]:
        var, entry = convert_varname(var, current_symbol_table)
    reg, offset = simple_register_allocator(var, current_symbol_table, offset, entry, no_flush, no_load)
    return (reg, offset) if not return_entry else (reg, offset, entry)


def is_tmp_var(v: str):
    if "-" in v:
        v = v.split("-")[-1]
    return v.startswith("__tmp_var_") or is_number(v) or is_char(v)[0]


def simple_register_allocator(var: str, current_symbol_table: SymbolTable, offset: int, entry, no_flush, no_load):
    global register_descriptor, address_descriptor, registers_in_block, removed_registers
    global lru_list_int, lru_list_fp, remember_to_restore, register_saver, register_loader
    global global_vars, local_var_mapping, BACKPATCH_OFFSET, LOCAL_VAR_OFFSET, BACKPATCHES
    global var_to_mem, prev_var_access

    # FIXME: Global mutation and stuff....

    # TODO: Test this a bit
    # no_load = no_flush

    req_fp, _type = requires_fp_register(var, entry)
    _s = DATATYPE2SIZE[_type.upper()] if entry is None else entry["size"]
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

    store_name = var.split("-")[-1]
    # print_text("# " + str(removed_registers))
    if var in register_descriptor.values() and not is_number(var) and not is_char(var)[0]:
        # Already has a register allocated
        register = address_descriptor[var]
    else:
        if len(free_registers) == 0:
            # No free register available
            register = lru_list.pop(0)
        else:
            # Free registers available
            register = free_registers.pop()

        no_flush = var in removed_registers or no_flush

        if register in local_var_mapping:
            if not no_flush:
                if req_fp:
                    print_text(f"\tl.s\t{register},\t__zero_data")
                else:
                    print_text(f"\tli\t{register},\t0")
        else:
            # Register is not being used rn in the current block
            # If it is a saved register we need to backpatch it

            if register.startswith("$s") or register.startswith("$f"):
                # Saved Registers. All fp registers are saved regs
                if register not in BACKPATCHES:
                    load_instr = LOAD_INSTRUCTIONS["int" if register.startswith("$s") else "float"]
                    save_instr = SAVE_INSTRUCTIONS["int" if register.startswith("$s") else "float"]
                    remember_to_restore[-1].append(f"\t{load_instr}\t{register},\t{BACKPATCH_OFFSET}($fp)")
                    print_backpatch(f"\t{save_instr}\t" + register + ",\t" + f"{BACKPATCH_OFFSET}($fp)")
                    BACKPATCH_OFFSET -= _s
                    BACKPATCHES.append(register)
                if not no_flush:
                    if req_fp:
                        print_text(f"\tl.s\t{register},\t__zero_data")
                    else:
                        print_text(f"\tli\t{register},\t0")

        # if var not in prev_var_access and not (is_number(store_name) or is_char(store_name)[0]):

        if is_global:
            load_instr = LOAD_INSTRUCTIONS[
                "int" if register.startswith("$s") or register.startswith("$t") else "float"
            ]
            print_text(f"\t{load_instr}\t{register},\t{var.split('-')[2]}")

        prev_var_access[var] = True
        address_descriptor[var] = register
        busy_registers.append(register)
        register_descriptor[register] = var
        registers_in_block[-1].append(register)

    # if not is_tmp_var(store_name):
    if not (is_number(store_name) or is_char(store_name)[0]):
        vmem = var_to_mem[store_name]
        if not no_load:
            print_text(vmem["load function"](register, vmem["memory address"], vmem["li"]))

    try:
        lru_list.remove(register)
    except:
        pass
    lru_list.append(register)

    if not register in local_var_mapping:
        local_var_mapping[register] = 1

    return register, offset


def dump_value_to_mem(reg: str, force: bool = False):
    # tmp vars will be dumped only if force is set to True
    global removed_registers, local_var_mapping, busy_registers
    varname = register_descriptor[reg]
    if varname is None:
        return
    var = varname.split("-")[-1]
    if is_number(varname) or is_char(varname)[0]:
        # if (is_number(varname) or is_char(varname)[0]) or (is_tmp_var(var) and not force):
        return
    desc = var_to_mem[var]
    print_text(desc["store function"](reg, desc["memory address"], desc["si"]))
    removed_registers[varname] = desc["load function"]
    del local_var_mapping[reg]
    register_descriptor[reg] = None
    busy_registers.remove(reg)


def store_temp_regs_in_use(offset: int) -> int:
    global busy_registers, removed_registers, register_descriptor
    for reg in busy_registers:
        if reg[1] == "t":
            # dump_value_to_mem(reg, force=True)
            name = register_descriptor[reg]
            if name is None:
                continue
            store_name = name.split("-")[-1]
            print_text("# "+ name + ", " + store_name)
            if is_number(store_name) or is_char(store_name)[0]:
                print_text("# " + store_name)
                continue
            vmem = var_to_mem[store_name]
            removed_registers[name] = vmem["load function"]
            ## Store the current value
            print_text(vmem["store function"](reg, vmem["memory address"], vmem["si"]))
            register_descriptor[reg] = None
            busy_registers.remove(reg)
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

        if reg in busy_registers:
            busy_registers.remove(reg)

    integer_registers = [f"$t{i}" for i in range(10)] + [f"$s{i}" for i in range(8)]
    fp_registers = [f"$f{i}" for i in list(range(30, 2, -2))]
    free_registers = integer_registers + fp_registers
    lru_list_fp = []
    lru_list_int = []
    registers_in_block = registers_in_block[:-1]
    remember_to_restore = remember_to_restore[:-1]


def create_new_register_block():
    global registers_in_block, remember_to_restore, local_var_mapping, var_to_mem, prev_var_access
    registers_in_block += [[]]
    remember_to_restore += [[]]
    local_var_mapping = dict()
    var_to_mem = dict()
    prev_var_access = dict()


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


# NOTE:
# It is important to initialize arrays. Default values are not guaranteed for arrays
# IMP: int main() should be present and with no other form of definition


def generate_mips_from_3ac(code):
    global STATIC_NESTING_LVL, DYNAMIC_NESTING_LVL, global_vars, BACKPATCH_OFFSET, BACKPATCH_INDEX, LOCAL_VAR_OFFSET, var_to_mem, err_label

    # print_text("## MIPS Assembly Code\n")
    # err_label = get_tmp_label();

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
    # print_text(f"{err_label}:")
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

    for part in code:
        for i, c in enumerate(part):
            # print("\n# " + " ".join(c))
            print_text("\n# " + " ".join(c))
            if len(c) == 1:
                if c[0].endswith(":"):
                    global_scope = False
                    # Label
                    print_text(c[0].replace("(", "__").replace(")", "__").replace(",", "_").replace("*", "ptr"))
                elif c[0] == "ENDFUNC":
                    # for v,e in var_to_mem.items():
                    #     print(v, e, current_symbol_table.func_scope)
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
                    LOCAL_VAR_OFFSET = offset
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
                        if entry is None:
                            raise NotImplementedError
                        elif entry["type"].startswith("struct"):
                            # custom type
                            # type_details = current_symbol_table.lookup_type(_type)
                            stack_pushables = _return_stack_custom_types(c[1], entry["type"], current_symbol_table)
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
                        d_size = DATATYPE2SIZE[entry["type"].upper()]
                        bits = int(np.log2(d_size))

                        index = c[0].split("[")[1].split("]")[0]
                        is_num, instr = is_number(index, True)
                        t1, offset = get_register(index, current_symbol_table, offset, no_flush=is_num)  # reg of x
                        if is_num:
                            print_text(instr(t1))

                        is_num, instr = is_number(c[2], True)
                        t2, offset = get_register(c[2], current_symbol_table, offset, no_flush=is_num)  # reg of y
                        if is_num:
                            print_text(instr(t2))

                        req_fp, _type = requires_fp_register(c[2], current_symbol_table.lookup(c[2]))
                        load_instr = LOAD_INSTRUCTIONS[_type]
                        save_instr = SAVE_INSTRUCTIONS[_type]

                        tmp_reg, offset = get_register("1", current_symbol_table, offset, no_flush=True)
                        tmp_reg2, offset = get_register("1", current_symbol_table, offset, no_flush=True)

                        # array out of bounds check
                        # print_text(f"\tli\t{tmp_reg2},\t{entry['dimensions'][0]}")
                        # print_text(f"\tslt\t{tmp_reg},\t{t1},\t{tmp_reg2}")
                        # print_text(f"\tbeq\t{tmp_reg},\t$0,\t{err_label}")

                        print_text(f"\tsll\t{tmp_reg},\t{t1},\t{bits}")
                        print_text(f"\tadd\t{tmp_reg},\t{t0},\t{tmp_reg}")
                        print_text(f"\t{save_instr}\t{t2},\t0({tmp_reg})")
                        dump_value_to_mem(t0)
                        continue

                    if c[0].startswith("*"):  # *ptr = x
                        t0, offset, entry = get_register(
                            c[0].split("*")[1], current_symbol_table, offset, True, no_flush=True
                        )  # reg of ptr

                        is_num, instr = is_number(c[2], True)
                        t2, offset = get_register(c[2], current_symbol_table, offset, no_flush=is_num)  # reg of x
                        if is_num:
                            print_text(instr(t2))

                        req_fp, _type = requires_fp_register(c[2], entry)
                        load_instr = LOAD_INSTRUCTIONS[_type]
                        save_instr = SAVE_INSTRUCTIONS[_type]

                        print_text(f"\t{save_instr}\t{t2},\t0({t0})")
                        dump_value_to_mem(t0)
                        continue

                    if "->" in c[0]:  # var -> field := x
                        var, field = c[0].split(" -> ")
                        t0, offset, entry = get_register(var, current_symbol_table, offset, True, no_flush=True)
                        type_entry = current_symbol_table.lookup_type(entry["type"])
                        idx = type_entry["field names"].index(field)
                        offset = 0
                        for z in range(idx):
                            offset += compute_storage_size({"type": type_entry["field types"]}, None)

                        ttemp, offset = get_register("1", current_symbol_table, offset, no_flush=True)
                        print_text(f"\taddi\t{ttemp},\t{t0},\t{offset}")

                        is_const, instr = is_number(c[2], True)
                        if not is_const:
                            is_const, instr = is_char(c[2])
                        t1, offset = get_register(c[2], current_symbol_table, offset, no_flush=is_const)
                        if is_const:
                            print_text(instr(t1))

                        print_text(f"\tsw\t{t1},\t({ttemp})")
                        dump_value_to_mem(t0)
                        continue

                    if "->" in c[2]:  # x := var -> field
                        raise NotImplementedError
                        continue

                    _, entry = convert_varname(c[0], current_symbol_table)
                    _type = entry["type"]

                    if entry["pointer_lvl"] >= 1:
                        t0, offset = get_register(c[0], current_symbol_table, offset, no_flush=True)
                        t1, offset = get_register(c[2], current_symbol_table, offset)
                        print_text(f"\tmove\t{t0},\t{t1}")
                        dump_value_to_mem(t0)
                        continue

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
                            dump_value_to_mem(reg1)
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
                                dump_value_to_mem(t1)
                        else:
                            t1, offset, entry = get_register(c[0], current_symbol_table, offset, True, no_flush=True)
                            if entry["is_array"] == True:
                                loc = var_to_mem[c[0]]["memory address"]
                                print_text(f"\tla\t{t1},\t{loc}")

                            if global_scope:
                                raise Exception("Non constant initialization in global scope")

                            if not c[2] == "NULL":
                                t2, offset = get_register(c[2], current_symbol_table, offset)
                                _type = entry["type"]
                                instr = MOVE_INSTRUCTIONS[_type]
                                print_text(f"\t{instr}\t{t1},\t{t2}")
                                dump_value_to_mem(t1)

                elif c[0] == "SYMTAB":
                    # Symbol Table
                    current_symbol_table = tabname_mapping[c[2]]
                    # var_to_mem = dict()
                    for store_name, entry in current_symbol_table._symtab_variables.items():
                        _type = entry["type"]
                        _s = entry["size"]
                        off = LOCAL_VAR_OFFSET - _s
                        if entry["pointer_lvl"] >= 1:
                            _load_instr = "lw"
                            _save_instr = SAVE_INSTRUCTIONS[_type] if _type in SAVE_INSTRUCTIONS else "sw"
                            load_func = lambda reg, loc, li: f"\t{li}\t{reg},\t{loc}"
                            store_func = lambda reg, loc, si: f"\t{si}\t{reg},\t{loc}"
                        else:
                            if entry["is_array"]:
                                _load_instr = "la"
                                _save_instr = "sw"
                            else:
                                # Terrible hack
                                _load_instr = LOAD_INSTRUCTIONS[_type] if _type in LOAD_INSTRUCTIONS else "lw"
                                _save_instr = SAVE_INSTRUCTIONS[_type] if _type in SAVE_INSTRUCTIONS else "sw"
                            load_func = lambda reg, loc, li: f"\t{li}\t{reg},\t{loc}"
                            store_func = lambda reg, loc, si: f"\t{si}\t{reg},\t{loc}"
                        var_to_mem[store_name] = {
                            "wrt_register": "$fp",
                            "offset": str(LOCAL_VAR_OFFSET),
                            "size": _s,
                            "type": _type,
                            "memory address": f"{off}($fp)",
                            "store function": store_func,
                            "load function": load_func,
                            "li": _load_instr,
                            "si": _save_instr,
                        }
                        if _type.startswith("struct") and entry["pointer_lvl"] == 0:
                            stack_pushables = _return_stack_custom_types(store_name, _type, current_symbol_table)
                            for (var, s, _t) in stack_pushables:
                                _off = LOCAL_VAR_OFFSET - int(s)
                                offstring = f"{_off}($fp)"
                                if entry["pointer_lvl"] >= 1:
                                    _load_instr = "lw"
                                    _save_instr = "sw"
                                    load_func = lambda reg, loc, li: f"\t{li}\t{reg},\t{loc}"
                                    store_func = lambda reg, loc, si: f"\t{si}\t{reg},\t{loc}"
                                else:
                                    if entry["is_array"]:
                                        _load_instr = "la"
                                    else:
                                        # Terrible hack
                                        _load_instr = LOAD_INSTRUCTIONS[_t] if _t in LOAD_INSTRUCTIONS else "lw"
                                    _save_instr = SAVE_INSTRUCTIONS[_t] if _t in SAVE_INSTRUCTIONS else "sw"
                                    load_func = lambda reg, loc, li: f"\t{li}\t{reg},\t{loc}"
                                    store_func = lambda reg, loc, si: f"\t{si}\t{reg},\t{loc}"
                                var_to_mem[var] = {
                                    "wrt_register": "$fp",
                                    "offset": str(_off),
                                    "size": int(s),
                                    "type": _t,
                                    "memory address": offstring,
                                    "store function": store_func,
                                    "load function": load_func,
                                    "li": _load_instr,
                                    "si": _save_instr,
                                }
                                LOCAL_VAR_OFFSET -= int(s)
                        else:
                            LOCAL_VAR_OFFSET -= _s

                    params = current_symbol_table._paramtab
                    off = 0
                    for p in params:
                        entry = current_symbol_table.lookup(p)
                        t, offset, entry = get_register(
                            entry["name"], current_symbol_table, offset, True, no_flush=True, no_load=True
                        )
                        # if not entry["pointer_lvl"] >= 1:
                        #     instr = LOAD_INSTRUCTIONS[entry["type"]]
                        instr = var_to_mem[p]["li"]
                        print_text(f"\t{instr}\t{t},\t{off}($fp)")
                        dump_value_to_mem(t)
                        # else:
                        #     print_text(f"\taddi\t{t},\t$fp,\t{off}")
                        #     print_text(f"\tlw\t{t},\t({t})")
                        off += entry["size"]
                else:
                    print_text(c)

            elif len(c) == 4:
                if c[1] == ":=":
                    # typecast expression
                    if c[2].startswith("("):
                        datatype = c[2].replace("(", "").replace(")", "")
                        if not datatype.endswith("*"):
                            offset = type_cast_mips(c, datatype, current_symbol_table, offset)
                        else:
                            is_num, instr = is_number(c[3], True)
                            is_ch, instr2 = is_char(c[3])

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
                                    dump_value_to_mem(t1)
                            else:
                                t1, offset, entry = get_register(
                                    c[0], current_symbol_table, offset, True, no_flush=True
                                )
                                if entry["is_array"] == True:
                                    loc = var_to_mem[c[0]]["memory address"]
                                    print_text(f"\tla\t{t1},\t{loc}")

                                if global_scope:
                                    raise Exception("Non constant initialization in global scope")

                                if not c[2] == "NULL":
                                    t2, offset = get_register(c[3], current_symbol_table, offset)
                                    _type = entry["type"]
                                    instr = MOVE_INSTRUCTIONS[_type]
                                    print_text(f"\t{instr}\t{t1},\t{t2}")
                                dump_value_to_mem(t1)

                    elif c[2].startswith("&"):  # ref
                        t1, offset, entry = get_register(c[0], current_symbol_table, offset, True, no_flush=True)
                        req_fp, _type = requires_fp_register(c[0], entry)
                        d_size = entry["size"]
                        bits = int(np.log2(d_size))

                        if c[3].endswith("]"):  # y = & arr [x]
                            arr_name = c[3].split()[0]
                            t2, offset, entry_arr = get_register(
                                arr_name, current_symbol_table, offset, True, no_flush=True
                            )

                            index = c[3].split()[1].replace("[", "").replace("]", "")
                            is_num, instr = is_number(index, True)
                            t3, offset = get_register(index, current_symbol_table, offset, no_flush=is_num)
                            if is_num:
                                print_text(instr(t3))
                            tmp_reg, offset = get_register("1", current_symbol_table, offset, no_flush=True)
                            tmp_reg2, offset = get_register("1", current_symbol_table, offset, no_flush=True)

                            # array out of bounds check
                            # print_text(f"\tli\t{tmp_reg2},\t{entry_arr['dimensions'][0]}")
                            # print_text(f"\tslt\t{tmp_reg},\t{t3},\t{tmp_reg2}")
                            # print_text(f"\tbeq\t{tmp_reg},\t$0,\t{err_label}")

                            print_text(f"\tsll\t{tmp_reg},\t{t3},\t{bits}")
                            print_text(f"\tadd\t{t1},\t{t2},\t{tmp_reg}")
                            # print_text(f"\tmove\t{t1},\t{tmp_reg}")
                            dump_value_to_mem(t1)
                        else:  # y = & var
                            # TODO: directly use name if global variable
                            t2, offset = get_register(c[3], current_symbol_table, offset, no_flush=True)
                            addr = var_to_mem[c[3]]["memory address"]
                            off = int(addr.split("(")[0])
                            bp = addr.split("(")[1].split(")")[0]
                            print_text(f"\taddi\t{t1},\t{bp},\t{off}")
                            dump_value_to_mem(t1)

                    elif c[2].startswith("*"):  # deref
                        t1, offset, entry = get_register(c[0], current_symbol_table, offset, True)
                        req_fp, _type = requires_fp_register(c[0], entry)
                        load_instr = LOAD_INSTRUCTIONS[_type]
                        save_instr = SAVE_INSTRUCTIONS[_type]

                        t2, offset = get_register(c[3], current_symbol_table, offset)
                        print_text(f"\t{load_instr}\t{t1},\t0({t2})")
                        dump_value_to_mem(t1)

                    elif c[3].startswith("["):  # array indexing
                        t0, offset, entry = get_register(c[0], current_symbol_table, offset, True, no_flush=True)
                        req_fp, _type = requires_fp_register(c[0], entry)
                        load_instr = LOAD_INSTRUCTIONS[_type]
                        save_instr = SAVE_INSTRUCTIONS[_type]
                        d_size = DATATYPE2SIZE[entry["type"].upper()]
                        bits = int(np.log2(d_size))

                        t1, offset, entry_arr = get_register(c[2], current_symbol_table, offset, True)

                        ind = c[3].replace("[", "").replace("]", "")
                        is_num, instr = is_number(ind, True)
                        t2, offset = get_register(ind, current_symbol_table, offset, no_flush=is_num)
                        if is_num:
                            print_text(instr(t2))
                        tmp_reg, offset = get_register("1", current_symbol_table, offset, no_flush=True)
                        tmp_reg2, offset = get_register("1", current_symbol_table, offset, no_flush=True)

                        # array out of bounds check
                        # print_text(f"\tli\t{tmp_reg2},\t{entry_arr['dimensions'][0]}")
                        # print_text(f"\tslt\t{tmp_reg},\t{t2},\t{tmp_reg2}")
                        # print_text(f"\tbeq\t{tmp_reg},\t$0,\t{err_label}")

                        print_text(f"\tsll\t{tmp_reg},\t{t2},\t{bits}")
                        print_text(f"\tadd\t{tmp_reg},\t{t1},\t{tmp_reg}")
                        print_text(f"\t{load_instr}\t{t0},\t({tmp_reg})")
                        dump_value_to_mem(t0)

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
                        dump_value_to_mem(t0)

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
                        dump_value_to_mem(t0)

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
                        print_text(
                            f"\tjal\t{c[3].replace('(', '__').replace(')', '__').replace(',', '_').replace('*', 'ptr')}"
                        )
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
                        dump_value_to_mem(t1)

                    elif c[3] == "->":
                        raise NotImplementedError

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

                        if op == "&&":
                            instrs = []
                            t4, offset, entry4 = get_register(
                                "1", current_symbol_table, offset, True, no_flush=is_const
                            )
                            t5, offset, entry5 = get_register(
                                "1", current_symbol_table, offset, True, no_flush=is_const
                            )
                            _type4 = entry4["type"] if entry4 is not None else (entry2["type"])
                            _type5 = entry5["type"] if entry4 is not None else (entry3["type"])
                            instrs.append(get_mips_instr_from_binary_op("!=", _type4, t2, "$0", t4)[0])
                            instrs.append(get_mips_instr_from_binary_op("!=", _type5, t3, "$0", t5)[0])
                            instrs.append(get_mips_instr_from_binary_op("&", _type, t4, t5, t1)[0])

                        elif op == "||":
                            instrs = []
                            t4, offset, entry4 = get_register(
                                "1", current_symbol_table, offset, True, no_flush=is_const
                            )
                            t5, offset, entry5 = get_register(
                                "1", current_symbol_table, offset, True, no_flush=is_const
                            )
                            _type4 = entry4["type"] if entry4 is not None else (entry2["type"])
                            _type5 = entry5["type"] if entry4 is not None else (entry3["type"])
                            instrs.append(get_mips_instr_from_binary_op("!=", _type4, t2, "$0", t4)[0])
                            instrs.append(get_mips_instr_from_binary_op("!=", _type5, t3, "$0", t5)[0])
                            instrs.append(get_mips_instr_from_binary_op("|", _type, t4, t5, t1)[0])

                        else:
                            instrs = get_mips_instr_from_binary_op(op, _type, t2, t3, t1)

                        for instr in instrs:
                            print_text(instr)
                        dump_value_to_mem(t1)

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
