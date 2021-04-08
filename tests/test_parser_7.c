//#include<stdio.h>

// union Data{
//     int i;
//     char c;
// };

int main(){
    // union Data data;
    int temp;

    struct Data {
        int i;
        char c;
    };

    struct Data data;

    data.i = 3;
    temp = data.i;
    data.c = 'a';
    //printf("%d %c", data.i, data.c);
    return 0;
}