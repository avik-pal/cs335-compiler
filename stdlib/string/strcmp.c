// compares 2 strings character wise. returns 0 if both strings are same
int strcmp(char* str1, char*str2){
    int i=0;
    while(str1[i]!='0' || str2[i]!='0'){
        if(str1[i]!=str2[i]) return (str1[i] - str2[i]); 
        if(str1[i]=='\0') return 0;
        i++;
    }

    return 0;
}