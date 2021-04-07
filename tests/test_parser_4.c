// testing loops

int main()
{
    int i = 0;
    int n = 10;
    int sum = 0;
    signed int d = 2;
    for (i = 0; i< n; i++)
    {
        sum += i;
    }

    while (i>0)
    {
        i--;
        sum -= i;
    }

    return 0;
}