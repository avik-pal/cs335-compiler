float sin_cos_taylor(float x, int j) {
	float sum=0;
	int i, limit = 5;
	float fac_cached = 1.0;

	for(i=1;i<=limit;i++)
	{
		if(i%2!=0)
		{
			sum=sum+pow(x,j) / fac_cached;
		}
		else
			sum=sum-pow(x,j) / fac_cached;

		j = j + 2;
		fac_cached *= j * (j - 1);
	}

	return sum;
}

float sin(float x) {
	return sin_cos_taylor(x, 1);
}

float cos(float x) {
	return sin_cos_taylor(x, 0);
}

float tan(float x) {
	float sinx = sin(x);
	float cosx = cos(x);
	float tanx = sinx/cosx;
	return tanx;
}