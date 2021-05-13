@include "stdlib/io/console_input.c"

int main() {
    int a, b, c, d, e, f, g, x;
    x = read_int();
    a = x * x;
    b = 3;
    c = x;
    d = c * c;
    e = b * 2;
    f = a + d;
    g = e * f;
    return f * g + a;
}