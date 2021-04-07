int main() {
    int c = 2, *a, b;
    double z;
    a = &c;
	if((*a)==0) {
		c++;
        if((*a)==b)
            z = (1 == 1 ? *a : b);
        z++;
    }
	else
		b++;

	switch(c)
    {
        case 1:
            (*a)--;
            break;

        case 2:
            z = (*a)+b;
            break;

        default:
            c++;
    }

    return 0;
}
