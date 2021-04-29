// Copy Propagation

int x = 4;

int main() {
    int a, b, c, d, e, f, g;
    a = x * x;
    b = 3;
    c = x;
    d = c * c;
    e = b * 2;
    f = a + d;
    g = e * f;

    for (x = 1; x < 10; x++) {
        a++;
    }

    return f * g + a;
}