struct point
{
   int x;
   int y;
};

// Driver Code
int main()
{
    struct point s;
    struct point *ptr = &s;
    ptr->x = 2;
    ptr->y = 3;
    return 0;
}