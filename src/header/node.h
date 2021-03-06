#ifndef OPNODE_H_
#define OPNODE_H_

#include "vector.h"

typedef enum {
    N_CHAR,
    N_SHORT,
    N_INT,
    N_LONG,
    N_SIGNED,
    N_UNSIGNED,
    N_FLOAT,
    N_DOUBLE,
    N_VOID
} dataType;

typedef enum {
    N_CONSTANT,
    N_IDENTIFIER,
    N_STRING,
} constantType;

typedef struct {
    constantType cType;

    // Constant (All types)
    dataType dType;
    union {
        long long int iVal;
        long double fVal;
    };

    // Identifiers
    char *name;
    long long int symIdx;

    // String Literal
    char *str;
} terminal;

typedef struct {
    char *name;
    int nops;
    int *types;  // Whether the current argument comes from the string array/node array
    cvector_vector_type(nonTerminal) ops;
    cvector_vector_type(char *) str_list;
} nonTerminal;

terminal *i_constant(dataType, long long int);
terminal *f_constant(dataType, long double);
terminal *identifier(char *, long long int);
terminal *string_literal(char *);

// nonTerminal function would use var arg, not sure how to use the extern definitions for
// that case

#endif