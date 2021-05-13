int fopen(char fname[], int write)
{    
    __asm_direc "li   $v0, 13";
    __asm_direc "la   $a0, 0($fp)";
    __asm_direc "lw   $a1, 4($fp)";
    __asm_direc "li   $a2, 0";
    __asm_direc "syscall";

    if (1) {
        __asm_direc "la $sp, 0($fp)";
        __asm_direc "lw $ra, -8($sp)";
        __asm_direc "lw $fp, -4($sp)";
        __asm_direc "jr $ra";
    }
    
    return 1;
}

void fwrite(int fd, char* buffer, int size){

    __asm_direc "li $v0, 15";
    __asm_direc "lw $a0, 0($fp)";
    __asm_direc "la $a1, 4($fp)";
    __asm_direc "lw $a2, 8($fp)";
    __asm_direc "syscall";

    if (1) {
        __asm_direc "la $sp, 0($fp)";
        __asm_direc "lw $ra, -8($sp)";
        __asm_direc "lw $fp, -4($sp)";
        __asm_direc "jr $ra";
    }

}

void fclose(int fd){
    __asm_direc "li   $v0, 16";
    __asm_direc "lw $a0, 0($fp)";
    __asm_direc "syscall";
}

/*
  # Open a File

  # system call for open file
  # output file name
  # Open for writing (flags are 0: read, 1: write)
  # mode is ignored
  # open a file (file descriptor returned in $v0)
  # save the file descriptor 
################################################################
  # Write to file just opened
  
  # system call for write to file
  # file descriptor 
  # address of buffer from which to write
  # hardcoded buffer length
  # write to file
  ###############################################################
  # Close the file 
  
  # system call for close file
  # file descriptor to close
  # close file
  ###############################################################

*/