#ifndef TOKENINFO_H_
#define TOKENINFO_H_

typedef struct TokenInfo {
    int token_number;
    char *token;
    char *lexeme;
    int line_number;
    int column_number;
} TokenInfo;

#endif