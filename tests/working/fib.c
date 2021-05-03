int main() {
    int a = 0, b = 1, c, i;
    for(i = 2; i < 10; i++) {
        c = a + b;
        a = b;
        b = c;
    }
    return c;
}