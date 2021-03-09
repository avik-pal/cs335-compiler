from graphviz import Digraph


def generate_graph_from_ast(ast, filename="AST"):
    num = 0
    graph = Digraph(format="dot")

    # Create the root node
    ## Should be a string but just for safety
    graph.node(str(num), str(ast[0]))

    _generate_graph_from_ast(graph, ast, num, num + 1)

    graph.render(filename=filename)


def _generate_graph_from_ast(graph, ast, parentTknId, childTknId):
    if not isinstance(ast, tuple):
        # Recursion Base Case
        graph.node(str(childTknId), str(ast))
        graph.edge(str(parentTknId), str(childTknId))
        return childTknId + 1
    else:
        nChildren = len(ast)
        for i in range(1, nChildren):
            childTknId_copy = childTknId
            childTknId += 1
            if isinstance(ast[i], tuple):
                childTknId = _generate_graph_from_ast(
                    graph, ast[i], childTknId_copy, childTknId
                )
                graph.node(str(childTknId_copy), str(ast[i][0]))
                graph.edge(str(parentTknId), str(childTknId_copy))
            else:
                graph.node(str(childTknId_copy), str(ast[i]))
                graph.edge(str(parentTknId), str(childTknId_copy))
        return childTknId


if __name__ == "__main__":
    result = ("-", ("-", ("NUM", 2.4), ("NUM", 4)), ("NUM", 21.0))
    generate_graph_from_ast(result)
