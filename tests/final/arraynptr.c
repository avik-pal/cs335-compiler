@include "stdlib/io/console_input.c"

int main()
{
    int new_arr[5];
    int b ;
    int arr[] = {10, 7, 8, 9, 1, 5};
    int a = 2;
    int *ptr;
    b = arr[2]*arr[3];
    new_arr[0] = 100;
    ptr = &arr[2];
    ptr++; 
    *ptr = read_int();
    a = arr[3];

    return a + b;

}