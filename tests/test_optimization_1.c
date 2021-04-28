// Copy Propagation

int main() {
    int a, x, b, c, d, e, f, g;
    a = x * x;
    b = 3;
    c = x;
    d = c * c;
    e = b * 2;
    f = a + d;
    g = e * f;
    return f * g;
}