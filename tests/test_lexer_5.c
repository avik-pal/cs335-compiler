// Struct Test
typedef struct MyStruct {
    int a;
    int b;
    double c;
} mystruct;

int main(int argc, char **argv) {
    mystruct z = {2, 3, 10.0};
    int a = z->a;
    int b = z->b;
    double c = z->c;
    return 1;
}