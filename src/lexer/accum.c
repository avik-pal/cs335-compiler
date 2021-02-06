#include "../header/vector.h"
#include "../header/token.h"
#include <stdio.h>
#include <string.h>
#include "../../y.tab.h"

// Allocate more than being used by the vector.
#define CVECTOR_LOGARITHMIC_GROWTH

extern int line;
extern int column_start;
extern char* token_name();
extern char* yytext;
extern int yyleng;
extern int yyparse();
extern int yylex();

/*
    Get the list of TokenInfo by querying the parser/scanner
*/
cvector_vector_type(TokenInfo) accumulate() {
    cvector_vector_type(TokenInfo) vec = NULL;

    char *token_orig, *lexeme_orig, *token, *lexeme;
    int token_number, line_number, column_number;

    int flag = 1;
    while ((token_number = yylex()) > 0) {
        // Copy the TOKEN and LEXEMEs for safety
        token = strdup(token_name(token_number));
        lexeme = strdup(yytext);
        line_number = line;
        column_number = column_start;

        // Create a new struct and append to the vector
        TokenInfo tkn_info = {token_number, token, lexeme, line_number, column_number};
        cvector_push_back(vec, tkn_info);
    }

    return vec;
}

int main(int argc, char **argv) {
    extern FILE *yyin, *yyout; 
  
    /* yyin points to the file input.txt  and opens it in read mode*/
    yyin = fopen(argv[1], "r");
    /* yyout points to the file output.txt  and opens it in write mode*/
    // yyout = fopen("Output.txt", "w");

    cvector_vector_type(TokenInfo) vec = accumulate();

    if (vec) {
        TokenInfo *it;
        size_t i;
        
        printf(" _____________________________________________________________________\n");
        printf("|%15s|%10s|%20s|%10s|%10s|\n","Token","Token #","Lexeme","Line #","Column #");
        printf("|=====================================================================|\n");
        
        for (it = cvector_begin(vec); it != cvector_end(vec); ++it) {
            printf("|%15s|%10d|%20s|%10d|%10d|\n", it->token, it->token_number, it->lexeme, it->line_number, it->column_number);
        }
        
        printf("|_______________|__________|____________________|__________|__________|\n");
    }
    return 1;
}