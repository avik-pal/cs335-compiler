@include "stdlib/io/console_output.c"
@include "stdlib/math/pow.c"
@include "stdlib/math/exp_log.c"

int main(){
    float a = exp(0.0);
    float b = exp(1.0);
    float c = log(a);
    float d = log(b);
    float e = log10(10.0);
    float f = log10(100.0);
    print_float(a);
    print_char('\n');
    print_float(b);
    print_char('\n');
    print_float(c);
    print_char('\n');
    print_float(d);
    print_char('\n');
    print_float(e);
    print_char('\n');
    print_float(f);
    print_char('\n');
    return 0;
}
