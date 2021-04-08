from typing import Mapping
from graphviz import Digraph
import networkx as nx
import matplotlib.pyplot as plt
import pydot
from networkx.drawing.nx_pydot import graphviz_layout


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
    v = f"{NODE_COUNTER} {label}"
    G.add_node(NODE_COUNTER)
    NODE_COUNTER += 1
    return v  # NODE_COUNTER - 1


def _resolve_fcall_graph(G, scopes, args):
    print(args)


def parse_code(tree):
    # global NODE_COUNTER, NODE_MAPPING
    # G = nx.DiGraph()

    # v = _add_new_node(G, "global")

    # in_function = 0
    # parent_scope = [v]

    # for t in tree:
    #     if len(t["code"]) == 0:
    #         continue

    #     code = t["code"]
    #     for line in code:
    #         if line[0] == "BEGINFUNCTION":
    #             in_function += 1
    #             v = _add_new_node(G, line[-1])
    #             G.add_edge(parent_scope[-1], v)
    #             parent_scope.append(v)
    #         elif line[0] == "ENDFUNCTION":
    #             parent_scope = parent_scope[:-1]
    #             in_function -= 1
    #         elif line[0] == "FUNCTION CALL":
    #             v1 = _add_new_node(G, "=")
    #             v2 = _add_new_node(G, line[-1])
    #             v3 = _add_new_node(G, line[2])
    #             G.add_edge(parent_scope[-1], v1)
    #             G.add_edge(v1, v2)
    #             G.add_edge(v1, v3)
    #             # G.add_edge(fname)
    #     # if code[0][0] == "BEGINFUNCTION":
    #     #     G.add_node(code[0][-1])
    #     #     G.add_edge("GLOBAL", code[0][-1])
    #     # else:
    #     #     # TODO
    #     #     raise Exception("Not handled parsing")
    # # G = nx.relabel_nodes(G, NODE_MAPPING)
    # pos = graphviz_layout(G, prog="dot")
    # nx.draw(G, pos, with_labels = True)
    # plt.show()
    pass
