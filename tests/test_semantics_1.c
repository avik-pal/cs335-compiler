// Custom Types

enum Week {
    Working = 1
};

struct Point {
    int x, y;
    double o;
    char p;
    int* l;
};

union MyPoint {
    struct Point* d;
};

int main() {
    struct Point pt;
    union MyPoint pt2;
    int c = 0;
    int d = 5 + 6 * 9;

    for(c = 1; c < 10; c ++) {
        d -= 1;
        ++d;
    }
    return 0;
}