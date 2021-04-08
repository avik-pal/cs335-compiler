int foo(int c, int d)
{
    return c+d;
}
int foo(char c)
{
    return (int) c;
}
int foo(double c)
{
    return (int)c;
}

int main(){

	int a,b,c;
	int x = 5;
	char y = 'y';
	double z = 9.57; 
	a = foo(x,x);
	b = foo(z);
	c = foo(y);

	return 0; 
}