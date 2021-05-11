int pow(int x, int n) {
    int val = 1, i = 1;
    for ( ; i <= n; i++)
    {
        val *= x;
    }
    return val;
}

float pow(float x, int n){
	float val = 1.0; 
    int i;
    for (i=1; i <= n; i++)
    {
        val *= x;
    }
    return val;
}