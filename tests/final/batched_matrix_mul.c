@include "stdlib/io/console_output.c"

int main(){
    float c[5][3][3], b[5][2][3];
    int a[5][3][2];
    int i, j, k, l;

    for(l = 0; l < 5; l++ ) {
        for(i = 0; i < 3; i++) {
            a[l][i][0] = l + i + 1;
            a[l][i][1] = l + i + 1;
        }
    }

    for(l = 0; l < 5; l++ ) {
        for(j = 0; j < 2; j++) {
            b[l][j][0] = l + j + 1;
            b[l][j][1] = l + j + 1;
            b[l][j][2] = l + j + 1;
        }
    }

    for(l = 0; l < 5; l++ ) {
        for(i = 0; i < 3; i++) {
            for(j = 0; j < 2; j++) {
                for(k = 0; k < 3; k++) {
                    c[l][i][k] = c[l][i][k] + (float)a[l][i][j] * b[l][j][k];
                }
            }
        }
    }

    for(l = 0; l < 5; l++ ) {
        
        for(j = 0; j < 10; j++ )
            print_char('#');
        print_char('\n');

        for(i = 0; i < 3; i++) {
            for(k = 0; k < 3; k++) {
                print_float(c[l][i][k]);
                print_char(' ');
            }
            print_char('\n');
        }
    }

    return 0;
}