//Recursion + static

int d = 5;

void f2()
{
    static int k;
    1 + 1;
}

int fact(int n)
{
    static double n;
    if (n==0)
        return 1;
    else
        return n*fact(n-1);
} 

int f1(int n)
{
    f2();
    return fact(n);
}
 
// Driver Code
int main()
{
    static int k;
    static int n;
    k = 1 == 1 ? 1 : 2 * 5;
    fact(10);
    return 0;
}