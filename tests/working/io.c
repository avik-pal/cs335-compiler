@include "stdlib/io/console_output.c"
@include "stdlib/io/console_input.c"

int main() {
    float f = read_float();
    int i = read_int();
    char c = read_char();
    print_float(f);
    print_char('\n');
    print_int(i);
    print_char('\n');
    print_char(c);
    print_char('\n');
    return 1;
}