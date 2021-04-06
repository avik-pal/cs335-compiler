from graphviz import Digraph


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
