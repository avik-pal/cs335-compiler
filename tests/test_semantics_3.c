//Recursion + static
int fact(int n)
{
    if (n==0)
        return 1;
    else
        return n*fact(n-1);
}
 
// Driver Code
int main()
{
    // static int k;
    // static int n;
    // k = 1 == 1 ? 1 : 2 * 5;
    return fact(10);
    // return 0;
}