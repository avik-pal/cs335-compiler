//Recursion

void f2()
{
    // printf("In f2");
    1 + 1;
} 

int f1(int n)
{
    // printf("In f1");
    f2();
    return fact(n);
}

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
    printf("%d\n",f1(2));
    return 0;
}