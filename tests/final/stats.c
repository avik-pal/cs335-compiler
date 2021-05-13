int sum(int a[], int size) {
    int s = 0, i;
    for(i = 0; i < size; i++) {
        s += a[i];
    }
    return s;
}

int mean(int a[], int n, int m) {
    int size = n * m;
    return sum(a, size) / size;
}

float sum(float a[], int size) {
    float s = 0;
    int i;
    for(i = 0; i < size; i++) {
        s += a[i];
    }
    return s;
}

float mean(float a[], int n, int m) {
    int size = n * m;
    return sum(a, size) / size;
}

int main() {
    int arr[3][3], i, j;
    float brr[3][3];
    for(i = 0; i < 3; i++) {
        for(j = 0; j < 3; j++) {
            arr[i][j] = i * j;
            brr[i][j] = (float) (i + j);
        }
    }
    return mean(arr, 3, 3) + (int) mean(brr, 3, 3);
}