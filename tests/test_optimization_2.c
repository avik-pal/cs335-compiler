// Copy Propagation

int main() {
    int x, y;
    int c = 2 + 4;
    int d = 1 || 0;
    y = 10;
    x = y + 3 + c;
    x = x * 1;
    x = x - 0;
    x = x / 1 + d;
    return 0;
}