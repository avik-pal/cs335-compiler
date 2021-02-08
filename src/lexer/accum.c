#include "../header/vector.h"
#include "../header/token.h"
#include <stdio.h>
#include <string.h>
#include "../header/y.tab.h"
#include <stdlib.h>
#include <unistd.h>
#include<fcntl.h> 
// Allocate more than being used by the vector.
#define CVECTOR_LOGARITHMIC_GROWTH
#define ANSI_COLOR_RED_BG     "\x1b[41m"
#define ANSI_COLOR_RESET   "\x1b[0m"
#define ANSI_COLOR_GREEN   "\x1b[32m"
#define ANSI_COLOR_WHITE_BG   "\x1b[7m"
extern int line;
extern int column_start;
extern char* token_name();
extern char* yytext;
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
    // extern FILE* out_file = NULL;
    int out_fd = 0;

    int inp_arg = 1;
    
    for (int i = 1; i < argc; i++)
        if (strcmp(argv[i], "-o") == 0){
            out_fd = open(argv[i+1], O_RDWR | O_CREAT, 0644);
            if (i==1){
                inp_arg = 3;
            }
            else if (i==2){
                inp_arg = 1;
            }
            break;
        }
            
    if (out_fd){
        dup2(out_fd, 1);
    }

    /* yyin points to the file input.txt and opens it in read mode*/
    yyin = fopen(argv[inp_arg], "r");
    if (!yyin){
        fprintf(stderr, ANSI_COLOR_RED_BG "[Error]" ANSI_COLOR_RESET " Can not open file " ANSI_COLOR_GREEN "%s" ANSI_COLOR_RESET "\n", argv[inp_arg]);
        exit(-1); 
    }
    else{
        fseek (yyin, 0, SEEK_END);
        int size = ftell(yyin);

        if (0 == size) {
            fprintf(stderr, ANSI_COLOR_RED_BG "[Error]" ANSI_COLOR_RESET " File " ANSI_COLOR_GREEN "%s" ANSI_COLOR_RESET " is empty!\n", argv[inp_arg]); 
            exit(-1);
        }
        else{
            fseek(yyin, 0, SEEK_SET);
        }
    }

    cvector_vector_type(TokenInfo) vec = accumulate();

    
    if (vec) {
        TokenInfo *it;
        size_t i;
        
        printf(" ___________________________________________________________\n");
        printf("|%15s|%20s|%10s|%10s|\n","Token","Lexeme","Line #","Column #");
        printf("|==========================================================|\n");
        
        for (it = cvector_begin(vec); it != cvector_end(vec); ++it) {
            char *pretty_lexeme = it->lexeme;
            if (strlen(pretty_lexeme) > 20) {
                pretty_lexeme[16] = '.';
                pretty_lexeme[17] = '.';
                pretty_lexeme[18] = '.';
                pretty_lexeme[19] = '"';
                pretty_lexeme[20] = '\0';
            }

            printf("|%15s|%20s|%10d|%10d|\n", it->token, pretty_lexeme, it->line_number, it->column_number);
        }
        
        printf("|_______________|____________________|__________|__________|\n");
    }
    if(out_fd)
        close(out_fd);
    return 1;
}