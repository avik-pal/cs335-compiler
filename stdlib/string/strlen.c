//returns length of a string that ends with '\0'
//Note: standard c strings end with '\0'
int strlen (char *str) {
    int len = 0;
    int i = 0;
    while (str[i] != '\0') {
        i++;
        len++;
    }
    return len;
}