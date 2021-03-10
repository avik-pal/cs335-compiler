tokens = lex.tokens
flag_for_error = 0

start = "translation_unit"

def p_error(p):
    global flag_for_error
    flag_for_error = 1

    if p is not None:
        print("error at line no:  %s :: %s" % ((p.lineno), (p.value)))
        parser.errok()
    else:
        print("Unexpected end of input")


parser = yacc.yacc()

def getArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=str, default=None, help='Input file')
    parser.add_argument('-o', '--output', type=str, default='AST', help='Output file')
    parser.add_argument('-t', '--trim', action='store_true', help='Trimmed ast')
    return parser

if __name__ == "__main__":
    args = getArgs().parse_args()
    if args.input == None:
        print("No input file specified")    
    else:
        with open(str(args.input), "r+") as file:
            data = file.read()
            tree = yacc.parse(data)
            if args.output[-4:]==".dot":
                args.output = args.output[:-4]
            if args.trim:
                generate_graph_from_ast(reduce_ast(tree), args.output)
            else:
                generate_graph_from_ast(tree,args.output)

