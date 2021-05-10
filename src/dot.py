from typing import Mapping
from graphviz import Digraph
import networkx as nx
import matplotlib.pyplot as plt
from networkx.drawing.nx_pydot import graphviz_layout, write_dot
from mips import print_data
from symtab import (
    get_stdlib_codes,
    get_tmp_label,
    get_tmp_var,
    get_global_symtab,
    get_default_value,
    get_tabname_mapping,
)


NODE_COUNTER = 0
NODE_MAPPING = {}
in_function = 1


def _resolve_fcall_graph_names(args):
    new_args = []
    for arg in args:
        if isinstance(arg, str):
            new_args.append(arg)
        else:
            new_args.append(str(arg["value"]))
    return new_args


def _rewrite_code(code, sizes, ret_sizes):
    tabname_mapping = get_tabname_mapping()
    new_code = []
    switch_depth = 0
    loop_depth = 0
    switch_label = []
    loop_labels = []
    switch_var = []
    ordering = []
    nlabel_case = [None]
    indent_arr = []
    already_app = False
    cur_indent = 0

    if not code[0][0].endswith(":"):
        for v, entry in tabname_mapping["GLOBAL"]._symtab_variables.items():
            if not entry.get("is_parameter", False) and entry["value"] is not None:
                new_code.append([v, ":=", str(entry["value"])])
                indent_arr.append(cur_indent)
    for c in code:
        if c[0] == "BEGINSWITCH":
            ordering.append(0)
            switch_depth += 1
            switch_label.append(get_tmp_label())
            switch_var.append(c[1])
            nlabel_case.append(None)
        elif c[0] == "ENDSWITCH":
            assert switch_depth >= 1
            new_code.append([switch_label.pop() + ":"])
            switch_depth -= 1
            switch_var.pop()
            nlabel_case.pop()
            ordering.pop()
        elif c[0] == "BEGINFUNCTION":
            new_code.append([c[2] + ":"])
            indent_arr.append(cur_indent)
            already_app = True
            cur_indent += 20
            new_code.append(["BEGINFUNC", str(sizes[c[2]]) + "," + str(ret_sizes[c[2]])])
            indent_arr.append(cur_indent)
        elif c[0] == "ENDFUNCTION":
            indent_arr.append(cur_indent)
            already_app = True
            cur_indent -= 20
            new_code.append(["ENDFUNC"])
        elif c[0] == "LOOPBEGIN":
            ordering.append(1)
            loop_depth += 1
            loop_labels.append((c[1], c[2]))
        elif c[0] == "ENDLOOP":
            assert loop_depth >= 1
            loop_depth -= 1
            loop_labels.pop()
            ordering.pop()
        elif c[0] == "BREAK":
            if ordering[-1] == 0:
                new_code.append(["GOTO", switch_label[-1]])
            elif ordering[-1] == 1:
                new_code.append(["GOTO", loop_labels[-1][1]])
            else:
                raise NotImplementedError
        elif c[0] == "CONTINUE":
            assert loop_depth > 0, Exception("Continue Used Outside Loop")
            new_code.append(["GOTO", loop_labels[-1][0]])
        elif c[0] == "CASE":
            _nlabel_case = get_tmp_label()
            if nlabel_case[-1] is not None:
                indent_arr.append(cur_indent)
                new_code.append([nlabel_case[-1] + ":"])
            new_code.append(["IF", switch_var[-1], "!=", c[1], "GOTO", _nlabel_case])
            nlabel_case[-1] = _nlabel_case
        elif c[0] == "DEFAULT":
            new_code.append([nlabel_case[-1] + ":"])
            nlabel_case[-1] = None
        elif c[0] == "FUNCTION CALL":
            if c[2].startswith("__store") and "index" in c[3][0]:
                a1 = c[3][0]["value"] + f"{c[3][0]['index']}"
                if isinstance(c[3][1]["value"], dict):
                    a2 = c[3][1]["value"]["value"]
                else:
                    a2 = c[3][1]["value"]
                upcode = [c[0], c[1], c[2], [a1, a2], c[4]]
            else:
                new_args = _resolve_fcall_graph_names(c[3])
                upcode = [c[0], c[1], c[2], new_args, c[4]]
                # print(upcode)

            if c[2].startswith("__store"):
                rhs = upcode[3][1]
                if isinstance(rhs, str) and rhs[0] == "'" and rhs[-1] == "'":
                    new_code.append([upcode[3][0], ":=", str(ord(eval(rhs)))])
                else:
                    new_code.append([upcode[3][0], ":=", rhs])
            elif c[2].startswith("__convert"):
                t = c[2].split(",")[-1].split(")")[0]
                new_code.append([upcode[4], ":=", "(" + t + ")", upcode[3][0]])

            elif c[2].startswith("__get_array_element"):
                new_code.append([upcode[4], ":=", upcode[3][0] , "[" + upcode[3][1] + "]"])

            elif c[2].startswith("__ref"):
                new_code.append([upcode[4], ":=",  "&", upcode[3][0]])

            elif c[2].startswith("__deref"):
                new_code.append([upcode[4], ":=",  "*" , upcode[3][0]])

            else:
                # TODO: Push Parameters to call stack (Check MIPS Specification)
                f = get_global_symtab().lookup(upcode[2])
                for arg in reversed(upcode[3]):
                    indent_arr.append(cur_indent)
                    new_code.append(["PUSHPARAM", arg])
                indent_arr.append(cur_indent)
                new_code.append([upcode[4], ":=", "CALL", upcode[2], str(f["param_size"])])
                if f["param_size"] > 0:
                    new_code.append(["POPPARAMS", str(f["param_size"])])

                # new_code.append(upcode)
        elif c[0] == "RETURN":
            new_code.append(["RETURN"] + ([] if len(c) == 1 else [c[1]["value"]]))
        elif c[0] == "SYMTAB" and c[1] == "PUSH":
            new_code.append(c)
            for v, entry in tabname_mapping[c[2]]._symtab_variables.items():
                if not entry.get("is_parameter", False):
                    if entry["value"] is None:
                        codes = _resolve_initialization(v, entry["type"], tabname_mapping[c[2]])
                        new_code += codes
                        indent_arr.extend([cur_indent] * len(codes))
                    else:
                        new_code.append([v, ":=", str(entry["value"])])
                        indent_arr.append(cur_indent)
        else:
            new_code.append(c)
        if not already_app:
            indent_arr.append(cur_indent)
        already_app = False
    return new_code, indent_arr


def _resolve_initialization(v, vtype, symtab):
    entry_type = symtab.lookup_type(vtype)
    codes = []
    for f, t in zip(entry_type["field names"], entry_type["field types"]):
        d = get_default_value(t)
        if d is not None:
            codes += [[f"{v}.{f}", ":=", f"{d}"]]
        else:
            _c = _resolve_initialization(f"{v}.{f}", t, symtab)
            codes += _c
    return codes


def size_of_child(symtab):
    s = symtab.current_offset
    for child in symtab.children:
        s += size_of_child(child)
    return s


def is_number(s: str) -> bool:
    try:
        if not s.isnumeric():
            float(s)
            return True
        else:
            return True
    except ValueError:
        return False


def get_lhs_rhs_variables(expr):
    # For function call send empty lhs since we dont want to remove that line

    tag = expr[0]
    if tag == "PUSHPARAM":
        return [], [] if is_number(expr[1]) else [expr[1]], False
    elif tag == "IF":
        return [], [expr[1]], False
    elif "CALL" in expr:
        return [expr[0]], [], True
    elif "RETURN" in expr:
        return (
            [],
            [] if len(expr) == 1 or is_number(expr[1]) else [expr[1]],
            False,
        )
    elif len(expr) == 4 and expr[2][0] == "(" and expr[2][-1] == ")":
        return [expr[0]], [expr[-1]], True
    elif len(expr) >= 2 and expr[1] == ":=":
        lhs = [expr[0]]
        if len(expr) == 3:
            rhs = [] if is_number(expr[2]) else [expr[2]]
            return lhs, rhs, True
        elif len(expr) == 5:
            rhs = [] if is_number(expr[2]) else [expr[2]]
            rhs += [] if is_number(expr[4]) else [expr[4]]
            return lhs, rhs, True
    return [], [], False


def compiler_optimization_algebraic_simplication(line):
    # Operates on a line by line basis
    if len(line) != 5 or (len(line) >= 2 and line[1] != ":="):
        return line, True
    try:
        no_change = True
        if is_number(line[2]):
            if is_number(line[4]):
                if line[3] == "&&":
                    line[3] = "and"
                elif line[3] == "||":
                    line[3] = "or"
                res = eval(" ".join(line[2:]))
                res = int(res) if isinstance(res, bool) else res
                line = [line[0], ":=", str(res)]
                no_change = False
            else:
                n = eval(line[2])
                if n == 0:
                    if line[3] in ("+", "-"):
                        line = [line[0], ":=", line[4]]
                        no_change = False
                    elif line[3] in ("/", "*"):
                        line = [line[0], ":=", "0"]
                        no_change = False
                elif n == 1:
                    if line[3] == "*":
                        line = [line[0], ":=", line[4]]
                        no_change = False
        elif is_number(line[4]):
            n = eval(line[4])
            if n == 0:
                if line[3] in ("+", "-"):
                    line = [line[0], ":=", line[2]]
                    no_change = False
                elif line[3] == "*":
                    line = [line[0], ":=", "0"]
                    no_change = False
            elif n == 1:
                if line[3] in ("*", "/"):
                    line = [line[0], ":=", line[2]]
                    no_change = False
        return line, no_change
    except:
        return line, True


def compiler_optimization_copy_propagation(line, replace_var):
    if len(line) not in (3, 5) or (len(line) >= 2 and line[1] != ":="):
        return line, True
    try:
        if len(line) == 3:
            rep = replace_var.get(line[2], line[2])
            return [line[0], ":=", rep], rep == line[2]
        else:
            rep1 = replace_var.get(line[2], line[2])
            rep2 = replace_var.get(line[4], line[4])
            return [line[0], ":=", rep1, line[3], rep2], rep1 == line[2] and rep2 == line[4]
    except:
        return line, True


def optimize_ir(code, indents, depth=5):
    new_code = []
    new_indents = []
    no_change = True
    replace_var = dict()
    var_lhs = dict()
    var_rhs = dict()
    encounter_label = False
    first_label = float("inf")
    for i, (c, idt) in enumerate(zip(code, indents)):
        # Apply Algebraic Simplification
        c, nc = compiler_optimization_algebraic_simplication(c)
        no_change = no_change and nc

        if not encounter_label:
            encounter_label = i > 0 and len(c) == 1 and c[0].endswith(":") or c[0] == "IF"
            if encounter_label:
                first_label = i

        if not encounter_label:
            # Apply Copy Propagation
            c, nc = compiler_optimization_copy_propagation(c, replace_var)
            no_change = no_change and nc

        lhs, rhs, is_arth_expr = get_lhs_rhs_variables(c)
        for l in lhs:
            if l not in var_lhs:
                var_lhs[l] = [i]
            else:
                var_lhs[l].append(i)
        for r in rhs:
            if r not in var_rhs:
                var_rhs[r] = [i]
            else:
                var_rhs[r].append(i)

        if is_arth_expr:
            if len(rhs) <= 1 and len(c) == 3:
                replace_var[lhs[0]] = c[2]
            elif lhs[0] in replace_var:
                del replace_var[lhs[0]]

        new_code.append(c)
        new_indents.append(idt)

    # Dead Code Elimination
    if code[0][0][-1] == ":":
        for var, lidx in var_lhs.items():
            ridx = var_rhs.get(var, [])
            if len(ridx) == 0:
                removals = lidx
            else:
                _r = 0
                _l = 0
                removals = []
                for (l1, l2) in zip(lidx[:-1], lidx[1:]):
                    while _r < len(ridx) and ridx[_r] < l1:
                        _r += 1
                    if not (ridx[_r] > l1 and ridx[_r] <= l2):
                        removals.append(l1)
            for r in removals:
                if r >= first_label:
                    break
                no_change = False
                new_code[r] = []
                new_indents[r] = []

        new_code = list(filter(lambda x: x != [], new_code))
        new_indents = list(filter(lambda x: x != [], new_indents))

    return (new_code, new_indents) if depth == 1 or no_change else optimize_ir(new_code, new_indents, depth - 1)


def parse_code(tree, output_file, optimize, print_code):
    # global NODE_COUNTER, NODE_MAPPING
    # G = nx.DiGraph()

    # v = _add_new_node(G, "global")

    # parent_scope = [v]

    if tree is None:
        return

    gtab = get_global_symtab()
    sizes = {}
    ret_sizes = {}
    for child in gtab.children:
        sizes[child.func_scope] = size_of_child(child)
        ret_sizes[child.func_scope] = gtab.lookup(child.func_scope)["return type size"]

    codes = []

    for i, t in enumerate(tree):
        if len(t["code"]) == 0:
            continue

        code = t["code"]
        code, indents = _rewrite_code(code, sizes, ret_sizes)
        if print_code:
            print("Before Compiler Optimizations")
            print()
            for c, idt in zip(code, indents):
                _z = " ".join(c)
                if _z[-1] == ":":
                    idt -= 16
                else:
                    _z = _z + ";"
                print(" " * idt + _z)
            print()

        if optimize:
            code, indents = optimize_ir(code, indents)
            if print_code:
                print("After Compiler Optimizations")
                print()
                for c, idt in zip(code, indents):
                    _z = " ".join(c)
                    if _z[-1] == ":":
                        idt -= 16
                    else:
                        _z = _z + ";"
                    print(" " * idt + _z)
                print()

        codes.append(code)

    # #print(get_stdlib_codes())

    # pos = graphviz_layout(G, prog="dot")
    # nx.draw(G, pos, with_labels = True, node_color="white")
    # write_dot(G, output_file+".dot")
    # plt.show()

    return codes
