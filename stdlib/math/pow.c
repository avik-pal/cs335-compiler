int pow(int x, int n) {
    int val = x, i = 2;
    for ( ; i <= n; i++)
    {
        val *= x;
    }
    return val;
}