//convert a string to lowercase
void strlwr(char *str){
    int i=0;
    while(str[i]!='\0'){
        if (str[i]>='A' && str[i]<='Z'){
            str[i] += 'a'-'A';
        }
        i++;
    }
    return;
}