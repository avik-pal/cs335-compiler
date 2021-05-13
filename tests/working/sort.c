@include "stdlib/io/console_output.c"
@include "stdlib/io/console_input.c"

int main(){
    int t,b;
    int i,k,j;
    int n = 3;
    int arr[3] = {9,4,7};
    
    // n = read_int();
    // for(i=0;i<n;i++){
    //     arr[i] = read_int();
    // }
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
        print_int(arr[k]);
        print_char(' ');
    }
    print_char('\n');
    return 0;
}