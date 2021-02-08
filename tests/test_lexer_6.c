// Example modified from https://www.w3schools.com/cpp/cpp_classes.asp
class Vehicle {
    public {
        char *type;
    }
}

class Car <- public Vehicle {
    public {
        char *brand;
        char *model;
        int year;
    };
    private {
        int internal_part1;
        long internal_part2;
        short internal_part3;
    }
};

int main(int argc, char **argv) {
    Car newcar;
    printf("Testing inherrrrrriiiiiiitttttteeeeeencccceeeeee");
    return 1;
}