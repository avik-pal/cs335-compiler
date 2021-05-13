@include "stdlib/io/console_output.c"
@include "stdlib/io/console_input.c"

int main(){
    int t,n;
    int i,k,j;
    float arr[100];
    
    n = read_float();
    for(i=0;i<n;i++){
        arr[i] = read_float();
    }
    for(i=0;i<n-1;i++){
        for(j=i+1;j<n;j++){
            if(arr[i]>arr[j]){
                t = arr[i];
                arr[i] = arr[j];
                arr[j] = t;
            }
        }
    }
    for(k=0;k<n;k++){
        print_float(arr[k]);
        print_char(' ');
    }
    print_char('\n');
    return 0;
}