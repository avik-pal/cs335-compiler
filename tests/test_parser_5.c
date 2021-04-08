// Struct Test
struct Mystruct {
    int a;
    int b;
    double c;
};

int main(int argc, char **argv) {
    struct Mystruct z = {2, 3, 10.0};
    int a = z.a;
    int b = z.b;
    double c = z.c;
    return 1;
}