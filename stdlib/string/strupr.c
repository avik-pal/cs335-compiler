//convert a string to uppercase
void strupr(char *str){
    int i=0;
    while(str[i]!='\0'){
        if (str[i]>='a' && str[i]<='z'){
            str[i] += 'A'-'a';
        }
        i++;
    }
    return;
}
