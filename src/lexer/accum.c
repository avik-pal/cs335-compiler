#include "../header/vector.h"
#include "../header/token.h"
#include "../header/utils.h"
#include <stdio.h>

// Allocate more than being used by the vector.
#define CVECTOR_LOGARITHMIC_GROWTH

int counter = 0;

int get_token_info(int *token_number, char **token, char **lexeme, int *line_number, int *column_number) {
    *token_number = counter;
    if(counter % 2 == 0) {
        *token = "ADWD";
        *lexeme = "sadsd";
    }
    else {
        *token = "2A12DWD";
        *lexeme = "sad1212sd";
    }
    *line_number = counter * 3;
    *column_number = counter * 9;

    ++counter;

    // Returning 0 means no token
    if (counter == 2)
        return 0;
    else
        return 1;
}


/*
    Get the list of TokenInfo by querying the parser/scanner
*/
cvector_vector_type(TokenInfo) accumulate() {
    cvector_vector_type(TokenInfo) vec = NULL;

    char *token_orig, *lexeme_orig, *token, *lexeme;
    int token_number, line_number, column_number;

    int more_tokens;

    while(1)
    {
        more_tokens = get_token_info(&token_number, &token_orig, &lexeme_orig, &line_number, &column_number);

        if(more_tokens == 0) {
            break;
        }

        // Copy the TOKEN and LEXEMEs for safety
        token = strcpy_alloc(token_orig);
        lexeme = strcpy_alloc(lexeme_orig);
            
        // Create a new struct and append to the vector
        TokenInfo tkn_info = {token_number, token, lexeme, line_number, column_number};
        cvector_push_back(vec, tkn_info);
    }

    return vec;
}

int main(int argc, char **argv) {
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