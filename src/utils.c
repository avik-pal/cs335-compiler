#include "header/utils.h"
#include <string.h>
#include <stdlib.h>

/*
    Allocate a new string and copy contents of src to it
*/
char *strcpy_alloc(char *src) {
    // NULL character is not counted in strlen
    char *dest = (char*) malloc((strlen(src) + 1) * sizeof(char));
    strcpy(dest, src);
    return dest;
}