int main()
{
    int arr[] = {10, 7, 8, 9, 1, 5};
    int new_arr[5];
    int a = 2;
    int *ptr;
    new_arr[0] = 100; 
    ptr = &new_arr[2];
    ptr++; 
    a = *ptr;

    return 0;
}