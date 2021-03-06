#include "../header/vector.h"
#include "../header/y.tab.h"
#include "../header/node.h"
#include <stdlib.h>
#include <stdarg.h>

extern void yyerror(char *);

int getNodeId() {
    static int id = 0;
    return id++;
}

terminal *alloc_terminal_node() {
    terminal *t = (terminal *) malloc(sizeof(terminal));
    return t;
}

terminal *i_constant(dataType dType, long long int value) {
    terminal *tnode = alloc_terminal_node();

    tnode->cType = N_CONSTANT;
    tnode->dType = dType;
    tnode->iVal = value;

    return tnode;
}

terminal *f_constant(dataType dType, long double value) {
    terminal *tnode = alloc_terminal_node();

    tnode->cType = N_CONSTANT;
    tnode->dType = dType;
    tnode->fVal = value;

    return tnode;
}

terminal *identifier(char *name, long long int symIdx) {
    terminal *tnode = alloc_terminal_node();

    tnode->cType = N_IDENTIFIER;
    tnode->name = name;
    tnode->symIdx = symIdx;

    return tnode;
}

terminal *string_literal(char *str) {
    terminal *tnode = alloc_terminal_node();

    tnode->cType = N_STRING;
    tnode->str = str;

    return tnode;
}

terminal *otherterminal(char *str) {
    terminal *tnode = alloc_terminal_node();

    tnode->cType = N_OTHER;
    tnode->str = str;

    return tnode;
}

nonTerminal *alloc_nonterminal_node() {
    nonTerminal *t = (nonTerminal *) malloc(sizeof(nonTerminal));
    return t;
}

nonTerminal *nonterminal(char *name, int nops, ...) {
    // Example usage:
    // logical_or_expression : logical_or_expression OR_OP logical_and_expression
    // nonterminal("logical_or_expression", 3, 1, 0, 1, $1, $2, $3)
    va_list args;
    nonTerminal *ntnode = alloc_nonterminal_node();

    int *types = (int *)malloc(nops * sizeof(int));
    va_start(args, nops * 2);
    for (int i = 0; i < nops; i++) {
        types[i] = va_arg(args, int);
    }
    ntnode->types = types;

    cvector_vector_type(nonTerminal) ntvec = NULL;
    cvector_vector_type(char *) strvec = NULL;

    for (int i = 0; i < nops; i++) {
        if (types[i] == 1) {
            // Terminal
        }
        else {
            // Non Terminal
        }
    }

    return ntnode;
}