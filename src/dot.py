from typing import Mapping
from graphviz import Digraph
import networkx as nx
import matplotlib.pyplot as plt
import pydot
from networkx.drawing.nx_pydot import graphviz_layout, write_dot


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


def _internal_code_parser(G, scopes, code):
    global in_function
    for line in code:
        print(line)
        _f = line[0]
        if _f == "BEGINFUNCTION":
            in_function += 1
            v = _add_new_node(G, line[-1])
            G.add_edge(scopes[-1], v)
            scopes.append(v)
        elif _f == "ENDFUNCTION":
            scopes = scopes[:-1]
            in_function -= 1
        elif _f == "FUNCTION CALL":
            v1 = _add_new_node(G, "=")
            v2 = _add_new_node(G, line[-1])
            v3 = _add_new_node(G, line[2])
            G.add_edge(scopes[-1], v1)
            G.add_edge(v1, v2)
            G.add_edge(v1, v3)
            scopes.append(v3)
            _resolve_fcall_graph(G, scopes, line[3])
            scopes = scopes[:-1]
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
        elif _f == "LABEL":
            v1 = _add_new_node(G, "LABEL")
            v2 = _add_new_node(G, line[-1])
            G.add_edge(scopes[-1], v1)
            G.add_edge(v1, v2)
            
        


def parse_code(tree):
    global NODE_COUNTER, NODE_MAPPING
    G = nx.DiGraph()

    v = _add_new_node(G, "global")

    parent_scope = [v]

    if tree is None:
        return

    for t in tree:
        if len(t["code"]) == 0:
            continue

        code = t["code"]
        print()
        _internal_code_parser(G, parent_scope, code)
        print()

    pos = graphviz_layout(G, prog="dot")
    # nx.draw(G, pos, with_labels = True, node_color="white")
    write_dot(G, "AST.dot")
    # plt.show()
