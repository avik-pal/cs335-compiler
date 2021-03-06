#include "../header/vector.h"
#include "../header/y.tab.h"
#include "../header/node.h"
#include <stdlib.h>
#include <stdarg.h>

extern void yyerror(char *);

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