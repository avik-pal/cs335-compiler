#include "../header/vector.h"
#include "../header/token.h"
#include "../header/utils.h"
#include <stdio.h>
#include <string.h>
#include "../../y.tab.h"
// Allocate more than being used by the vector.
#define CVECTOR_LOGARITHMIC_GROWTH

int counter = 0;

extern int line;
extern int column;
extern char* token_name();
extern char yytext[];
extern int yylex();
/*
    Get the list of TokenInfo by querying the parser/scanner
*/
cvector_vector_type(TokenInfo) accumulate() {
    cvector_vector_type(TokenInfo) vec = NULL;

    char *token_orig, *lexeme_orig, *token, *lexeme;
    int token_number, line_number, column_number;

    int flag = 1;
    while ( (token_number = yylex()) > 0 ) {
        // printf("%d %s",token_number,token_name(token_number));
        // yytext[strlen(yytext)-2] = '\0';
        printf("%s", yytext );
        // Copy the TOKEN and LEXEMEs for safety
        token = strcpy_alloc(token_name(token_number));
        lexeme = strcpy_alloc(yytext);
        line_number = line;
        column_number = column;
        // Create a new struct and append to the vector
        TokenInfo tkn_info = {token_number, token, lexeme, line_number, column_number};
        cvector_push_back(vec, tkn_info);
    }

    return vec;
}

int main(int argc, char **argv) {
    extern FILE *yyin, *yyout; 
  
    /* yyin points to the file input.txt 
    and opens it in read mode*/
    yyin = fopen(argv[1], "r"); 
    printf("%s",argv[1]);
    /* yyout points to the file output.txt 
    and opens it in write mode*/
    // yyout = fopen("Output.txt", "w"); 
    printf("here");
    cvector_vector_type(TokenInfo) vec = accumulate();
    if (vec) {
        TokenInfo *it;
        size_t i;
        for (it = cvector_begin(vec); it != cvector_end(vec); ++it) {
            printf("TOKEN INFO: Token - %s | Token Number - %d | Lexeme - %s | Line No - %d | Column No - %d\n", it->token, it->token_number, it->lexeme, it->line_number, it->column_number);
        }
    }
    return 1;
}