int foo(int c, int d)
{
    return c+d;
}
char foo(char c)
{
    return c;
}
double foo(double c)
{
    return c;
}

int main(){

	int a;
	char b;
	double c;
	int x = 5;
	char y = 'y';
	double z = 9.57; 
	a = foo(x,x);
	b = foo(y);
	c = foo(z);

	return 0; 
}