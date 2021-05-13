@include "stdlib/io/file_io.c"

int main()
{
    char arr[]= {'f','i','l','e','.','t','x','t','\0'};
<<<<<<< Updated upstream
    // char arr2[]= {'f','i','l','e','2','.','t','x','t','\0'};
    char dat[]= {'H','e','l','l','o','\0'};
    int fd1;  // ,fd2;
    fd1 = fopen(arr, 1);
=======
    int arr3[] = {102, 105, 108, 101, 46, 116, 120, 116, 0};
    char arr2[]= {'f','i','l','e','2','.','t','x','t','\0'};
    char dat[]= {'H','e','l','l','o','\n'};
    int fd1,fd2;
    fd1 = fopen(arr3,1);
>>>>>>> Stashed changes

    fwrite(fd1, dat, 6);

    fclose(fd1);

<<<<<<< Updated upstream
    return 1;
=======
    //fd2 = fopen(arr2, 1);
>>>>>>> Stashed changes

    // fd2 = fopen(arr2, 1);

    // return fd2;
}