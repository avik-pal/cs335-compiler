float pow(float a, int n) {
    int i = 1;
    float val = 1;
    for(; i <= n; i++) {
        val *= a;
    }
    return val;
}


int main() {
    float c = pow(2.0, 4);
    return (int) c;
}