@include "stdlib/mem/malloc.c"
@include "stdlib/io/console_output.c"

int main()
{
    int *ptr;
    ptr = malloc(sizeof(int)*4);
    
    *ptr = 3;
    print_int(*ptr);

    return 0;
}