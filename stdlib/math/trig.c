int fac(int x)
{
	int i,fac=1;
	for(i=1;i<=x;i++)
		fac=fac*i;
	return fac;
}

float sin(float x)
{
	float sum=0;
	int i,j=1,limit = 5;

	for(i=1;i<=limit;i++)
	{
		if(i%2!=0)
		{
			sum=sum+pow(x,j)/fac(j);
		}
		else
			sum=sum-pow(x,j)/fac(j);

		j=j+2;
	}

	return sum;
}