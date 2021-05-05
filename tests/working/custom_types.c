struct indemo {
    int k;
    float kk;
};

struct demo {
    struct indemo g;
    int a;
    float b;
};

struct demo str_return() {
    struct demo s;
    s.a = 1;
    s.b = 2.0;
    s.g.k = 3;
    s.g.kk = 5.0;
    return s;
}

int main() {
    struct demo d = str_return();
    return d.a + (int) d.b + d.g.k + (int) d.g.kk;
}