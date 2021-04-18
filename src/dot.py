from typing import Mapping
from graphviz import Digraph
import networkx as nx
import matplotlib.pyplot as plt
from networkx.drawing.nx_pydot import graphviz_layout, write_dot
from symtab import get_tmp_label, get_global_symtab


def generate_graph_from_ast(ast, filename="AST"):
    num = 0
    graph = Digraph(format="dot")

    # Create the root node
    ## Should be a string but just for safety
    graph.node(str(num), str(ast[0]))

    _generate_graph_from_ast(graph, ast, num, num + 1)

    graph.render(filename=filename, cleanup=True)

    return graph


def _generate_graph_from_ast(graph, ast, parentTknId, childTknId):
    if not isinstance(ast, (tuple, list)):
        # Recursion Base Case
        graph.node(str(childTknId), str(ast))
        graph.edge(str(parentTknId), str(childTknId))
        return childTknId + 1
    else:
        nChildren = len(ast) - 1
        for i in range(1, nChildren + 1):
            childTknId_copy = childTknId
            childTknId += 1
            if isinstance(ast[i], (tuple, list)):
                childTknId = _generate_graph_from_ast(graph, ast[i], childTknId_copy, childTknId)
                graph.node(str(childTknId_copy), str(ast[i][0]))
                graph.edge(str(parentTknId), str(childTknId_copy))
            else:
                graph.node(str(childTknId_copy), str(ast[i]))
                graph.edge(str(parentTknId), str(childTknId_copy))
        return childTknId


def reduce_ast(ast):
    current_ast = []
    if isinstance(ast, (tuple, list)):
        nChildren = len(ast) - 1
        current_ast.append(ast[0])
        for child in ast[1:]:
            reduced_child = reduce_ast(child)
            if reduced_child[0] == ast[0]:
                current_ast.extend(reduced_child[1:])
            else:
                current_ast.append(reduced_child)
        if nChildren == 1:
            # if isinstance(current_ast[1], (tuple, list)):
            #     return current_ast[1]
            # else:
            #     return current_ast
            return current_ast[1]
    else:
        current_ast = ast
    return current_ast


NODE_COUNTER = 0
NODE_MAPPING = {}


def _add_new_node(G, label):
    global NODE_COUNTER, NODE_MAPPING
    NODE_MAPPING[NODE_COUNTER] = label
    v = f"({NODE_COUNTER}) {label}"
    NODE_COUNTER += 1
    return v  # NODE_COUNTER - 1


in_function = 1


def _resolve_fcall_graph(G, scopes, args):
    for arg in args:
        if isinstance(arg, str):
            arg = {"value": arg}
        if arg.get("code", []) != []:
            v = _add_new_node(G, arg["value"])
            G.add_edge(scopes[-1], v)
            # _internal_code_parser(G, scopes, arg["code"])
        else:
            v = _add_new_node(G, arg["value"])
            G.add_edge(scopes[-1], v)


def _resolve_fcall_graph_names(args):
    new_args = []
    for arg in args:
        if isinstance(arg, str):
            new_args.append(arg)
        else:
            new_args.append(str(arg["value"]))
    return new_args


def _internal_code_parser(G, scopes, code):
    global in_function
    for line in code:
        _f = line[0]
        print(line)
        if _f == "BEGINFUNCTION":
            in_function += 1
            v = _add_new_node(G, line[-1])
            G.add_edge(scopes[-1], v)
            scopes.append(v)
        elif _f == "ENDFUNCTION":
            scopes.pop()
            in_function -= 1
        elif _f == "FUNCTION CALL":
            if line[2].startswith("__store") and "index" in line[3][0]:
                v1 = _add_new_node(G, "=")
                v2 = _add_new_node(G, line[-1])
                v3 = _add_new_node(G, line[2])
                v4 = _add_new_node(G, line[3][0]["value"] + f"{line[3][0]['index']}")
                if isinstance(line[3][1]["value"], dict):
                    v5 = line[3][1]["value"]["value"]
                else:
                    v5 = line[3][1]["value"]
                G.add_edge(scopes[-1], v1)
                G.add_edge(v1, v2)
                G.add_edge(v1, v3)
                G.add_edge(v3, v4)
                G.add_edge(v3, v5)
            else:
                v1 = _add_new_node(G, "=")
                v2 = _add_new_node(G, line[-1])
                v3 = _add_new_node(G, line[2])
                G.add_edge(scopes[-1], v1)
                G.add_edge(v1, v2)
                G.add_edge(v1, v3)
                scopes.append(v3)
                _resolve_fcall_graph(G, scopes, line[3])
                scopes.pop()
        elif _f == "IF":
            v1 = _add_new_node(G, "IF")
            v2 = _add_new_node(G, f"{line[1]} = 0")
            v3 = _add_new_node(G, f"GOTO")
            v4 = _add_new_node(G, line[-1])
            G.add_edge(scopes[-1], v1)
            G.add_edge(v1, v2)
            G.add_edge(v1, v3)
            G.add_edge(v3, v4)
        elif _f == "GOTO":
            v1 = _add_new_node(G, "GOTO")
            v2 = _add_new_node(G, line[-1])
            G.add_edge(scopes[-1], v1)
            G.add_edge(v1, v2)
        # elif _f == "LABEL":
        #     v1 = _add_new_node(G, "LABEL")
        #     v2 = _add_new_node(G, line[-1])
        #     G.add_edge(scopes[-1], v1)
        #     G.add_edge(v1, v2)
        elif _f == "BEGINSWITCH":
            v = _add_new_node(G, f"SWITCH {line[-1]}")
            G.add_edge(scopes[-1], v)
            scopes.append(v)
        elif _f == "ENDSWITCH":
            scopes.pop()
        elif _f == "RETURN":
            v = _add_new_node(G, f"RETURN" + ("" if len(line) == 1 else f" {line[-1]['value']}"))
            G.add_edge(scopes[-1], v)
        else:
            G.add_edge(scopes[-1], " ".join(line))


def _rewrite_code(code, sizes):
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
            new_code.append(["BEGINFUNC", str(sizes[c[2]])])
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
            new_code.append(["IF", switch_var[-1], "!=", c[1], "GOTO", _nlabel_case])
            if nlabel_case[-1] is not None:
                indent_arr.append(cur_indent)
                new_code.append([nlabel_case[-1] + ":"])
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

            if c[2].startswith("__store"):
                new_code.append([upcode[3][0], "=", upcode[3][1]])
            else:
                # TODO: size
                # TODO: Push Parameters to call stack (Check MIPS Specification)
                f = get_global_symtab().lookup(upcode[2])
                for arg in reversed(upcode[3]):
                    indent_arr.append(cur_indent)
                    new_code.append(["PUSHPARAM", arg])
                indent_arr.append(cur_indent)
                new_code.append([upcode[4], "=", "CALL", upcode[2]])
                if f["param_size"] > 0:
                    new_code.append(["POPPARAMS", str(f["param_size"])])
                
                # new_code.append(upcode)
        elif c[0] == "RETURN":
            new_code.append(["RETURN"] + ([] if len(c) == 1 else [c[1]["value"]]))
        else:
            new_code.append(c)
        if not already_app:
            indent_arr.append(cur_indent)
        already_app = False
    return new_code, indent_arr


def size_of_child(symtab):
    s = symtab.current_offset
    for child in symtab.children:
        s += size_of_child(child)
    return s


def parse_code(tree, output_file):
    # global NODE_COUNTER, NODE_MAPPING
    # G = nx.DiGraph()

    # v = _add_new_node(G, "global")

    # parent_scope = [v]

    if tree is None:
        return

    gtab = get_global_symtab()
    sizes = {}
    for child in gtab.children:
        sizes[child.func_scope] = size_of_child(child)

    for t in tree:
        if len(t["code"]) == 0:
            continue

        code = t["code"]
        print()
        code, indents = _rewrite_code(code, sizes)
        for c, idt in zip(code, indents):
            _z = " ".join(c)
            if _z[-1] == ":":
                idt -= 16
            else:
                _z = _z + ";"
            print(" " * idt + _z)
        # _internal_code_parser(G, parent_scope, code)
        print()

    # pos = graphviz_layout(G, prog="dot")
    # nx.draw(G, pos, with_labels = True, node_color="white")
    # write_dot(G, output_file+".dot")
    # plt.show()
