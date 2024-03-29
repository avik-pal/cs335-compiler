/* Function to sort an array using insertion sort*/
int insertionSort(int n, int arr[])
{
   int i, key, j;
   for (i = 1; i < n; i++)
   {
       key = arr[i];
       j = i-1;
 
       /* Move elements of arr[0..i-1], that are
          greater than key, to one position ahead
          of their current position */
       while (j >= 0 && arr[j] > key)
       {
           arr[j+1] = arr[j];
           j = j-1;
       }
       arr[j+1] = key;
   }
    return arr[0];
}

// A utility function ot print an array of size n
// void printArray(int arr[], int n)
// {
//    int i;
//    for (i=0; i < n; i++);
// }

/* Driver program to test insertion sort */
int main()
{
    int arr[5] = {12 + 4, 11, 13, 5, 6};
 
    int t = insertionSort(5, arr);
    // printArray(arr, n);
 
    return t;
}