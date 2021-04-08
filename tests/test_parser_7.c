//#include<stdio.h>

union Data{
    int i;
    char c;
};

int main(){
    union Data data;
    int temp;

    data.i = 3;
    temp = data.i;
    data.c = 'a';
    //printf("%d %c", data.i, data.c);
}