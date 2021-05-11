float exp(float x){
	float sum = 1.0; // initialize sum of series
    int i = 30;
    for (; i > 0; i=i-1 )
        sum = 1 + x * sum / i;
 
    return sum;
}


float log(float n)
{
    float num = (n - 1) / (n + 1);
    float cal;
    float sum = 0;
    int mul;
    int i = 1;
    for (; i <= 1000; i=i+1) {
        mul = 2*i - 1;
        cal = pow(num, mul);
        cal = cal / mul;
        sum = sum + cal;
    }
    sum = 2 * sum;
    return sum;
}
  

float log10(float x)
{
    return log(x)/2.303;
}
