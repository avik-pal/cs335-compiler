@include "stdlib/io/console_output.c"
@include "stdlib/math/pow.c"
@include "stdlib/math/trig.c"

int main() {
	float x = cos(1.707);
	float y = sin(0.0);
	float z = tan(0.85035);
	print_float(x);
	print_char('\n');
	print_float(y);
	print_char('\n');
	print_float(z);
	print_char('\n');
    return 0;
}