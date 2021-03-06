#ifndef OPNODE_H_
#define OPNODE_H_

// How to handle keywords? Can they be treated simply as operators?

typedef enum {
    typeCon,  // Constant
    typeId,   // Identifier
    typeOpr,  // Operator
} nodeEnum;

typedef struct {
    int value;  // Constant Value
} conNodeType;

typedef struct {
    int oper;
    int nops;
    nodeType *ops[1];
} oprNodeType;

typedef struct {
    int i;  // Index to the symbol table
} idNodeType;

typedef struct {
    nodeEnum type;

    union {
        conNodeType con;
        idNodeType id;
        oprNodeType opr;
    };
} nodeType;

extern int sym[26];

#endif