//Recursion + static
int fact(int n)
{
    if (n < 2)
        return 1;
    else
        return n*fact(n-1);
}
 
// Driver Code
int main()
{
    return fact(5);
}