float sqrt(float square){

    int i;
    float root;
    root = square/3.0;

    if (square <= 0.0){
        return 0.0;
    }

    for (i=0; i<32; i++){
        root = (root + (square / root)) / 2.0;
    }
        
    return root;
}