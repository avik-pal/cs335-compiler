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
    return fact(10);
}