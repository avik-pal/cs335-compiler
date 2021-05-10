void print_int(int x) {
    __asm_direc "lw $a0, 0($fp)";
    __asm_direc "li $v0, 1";
    __asm_direc "syscall";
}

void print_float(float x) {
    __asm_direc "s.s $f12, 0($sp)";
    __asm_direc "la $sp, -4($sp)";
    __asm_direc "l.s $f12, 0($fp)";
    __asm_direc "li $v0, 2";
    __asm_direc "syscall";
    __asm_direc "la $sp, 4($sp)";
    __asm_direc "l.s $f12, 0($sp)";
}

void print_char(char x) {
    __asm_direc "lw $a0, 0($fp)";
    __asm_direc "li $v0, 11";
    __asm_direc "syscall";
}