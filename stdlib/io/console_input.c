int read_int() {
    __asm_direc "li $v0, 5";
    __asm_direc "syscall";

    if (1) {
        __asm_direc "la $sp, 0($fp)";
        __asm_direc "lw $ra, -8($sp)";
        __asm_direc "lw $fp, -4($sp)";
        __asm_direc "jr $ra";
    }
    
    return 1;
}

float read_float() {
    __asm_direc "li $v0, 6";
    __asm_direc "syscall";

    if (1) {
        __asm_direc "la $sp, 0($fp)";
        __asm_direc "lw $ra, -8($sp)";
        __asm_direc "lw $fp, -4($sp)";
        __asm_direc "jr $ra";
    }
    
    return 1.0;
}

char read_char() {
    __asm_direc "li $v0, 12";
    __asm_direc "syscall";

    if (1) {
        __asm_direc "la $sp, 0($fp)";
        __asm_direc "lw $ra, -8($sp)";
        __asm_direc "lw $fp, -4($sp)";
        __asm_direc "jr $ra";
    }
    
    return '';
}


char* read_string(char* inp_buffer, int max_len) {
    __asm_direc "la $a0, 0($fp)";
    __asm_direc "lw $a1, 4($fp)";
    __asm_direc "li $v0, 8";
    __asm_direc "syscall";

    if (1) {
        __asm_direc "la $sp, 0($fp)";
        __asm_direc "lw $ra, -8($sp)";
        __asm_direc "lw $fp, -4($sp)";
        __asm_direc "jr $ra";
    }
    
    return inp_buffer;
}