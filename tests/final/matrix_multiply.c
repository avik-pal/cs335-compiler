// @include "stdlib/io/console_output.c"

int main(){
    int a[3][2], b[2][3], c[3][3];
    int i, j, k;

    for(i = 0; i < 3; i++) {
        a[i][0] = i + 1;
        a[i][1] = i + 1;
    }

    for(j = 0; j < 2; j++) {
        b[j][0] = j + 1;
        b[j][1] = j + 1;
        b[j][2] = j + 1;
    }

    for(i = 0; i < 3; i++) {
        for(j = 0; j < 2; j++) {
            for(k = 0; k < 3; k++) {
                c[i][k] = c[i][k] + a[i][j] * b[j][k];
            }
        }
    }

    for(i = 0; i < 3; i++) {
        for(k = 0; k < 3; k++) {
            print_int(c[i][k]);
            print_char(' ');
        }
        print_char('\n');
    }

    return 1;
}