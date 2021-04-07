int main() {
    int c, a, b;
    double z;
	if(c==0) {
		c++;
        if(a==b)
            z = (1 == 1 ? a : b);
        z++;
    }
	else
		b++;

	switch(c)
    {
        case 1:
            a--;
            break;

        case 2:
            z = a+b;
            break;

        default:
            c++;
    }

    return 0;
}
