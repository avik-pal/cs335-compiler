//gives a pointer to the lst occurence of a character in a string
char* strchr(char* str, char ch){
    char* temp = 0;//NULL
    int i=0;
    while(str[i]!='\0'){
        if(str[i]==ch){
            temp = str+i;
        }
        i++;
    }
    return temp;
}