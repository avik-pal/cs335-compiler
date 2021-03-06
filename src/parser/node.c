#include "../header/vector.h"
#include "../header/y.tab.h"
#include "../header/node.h"
#include <stdlib.h>
#include <stdarg.h>

extern void yyerror(char *);

nodeType *constant(int value) {
    nodeType *p;

    if ((p = (nodeType *)malloc(sizeof(nodeType))) == NULL) {
        yyerror("Out of Memory!!!");
    }

    p->type = typeCon;
    p->con.value = value;

    return p;
}

nodeType *identifier(int i) {
    nodeType *p;

    if ((p = (nodeType *)malloc(sizeof(nodeType))) == NULL) {
        yyerror("Out of Memory!!!");
    }

    p->type = typeId;
    p->id.i = i;

    return p;
}

nodeType *operator(int oper, int nops, ...) {
    va_list ap;
    nodeType *p;
    int i;

    if ((p = (nodeType *)malloc(sizeof(nodeType))) == NULL) {
        yyerror("Out of Memory!!!");
    }

    p->type = typeOpr;
    p->opr.oper = oper;
    p->opr.nops = nops;

    va_start(ap, nops);
    for (i = 0; i < nops; i++) {
        p->opr.ops[i] = va_arg(ap, nodeType*);
    }
    va_end(ap);

    return p;
}

void freeNode(nodeType *p) {
    int i;
    if (!p) {
        return;
    }
    if (p->type == typeOpr) {
        for (i = 0; i < p->opr.nops; i++) {
            freeNode(p->opr.ops[i]);
        }
    }
    free (p);
}