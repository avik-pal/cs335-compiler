int* malloc(int size)
{   
    __asm_direc "lw $a0, 0($fp)";
    __asm_direc "li $v0, 9";
    __asm_direc "syscall";

    if (1) {
        __asm_direc "la $sp, 0($fp)";
        __asm_direc "lw $ra, -8($sp)";
        __asm_direc "lw $fp, -4($sp)";
        __asm_direc "jr $ra";
    }
    
    return 1;
}
