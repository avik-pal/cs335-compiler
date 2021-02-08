# CS335 IITK Compiler Project

## Description
This project aims to develop a compiler for C language as a part of the course CS335-Compiler Design.

#### Milestone 1
We develop a scanner using lex and yacc, which takes as input any C program and generates a table of tokens along with the corresponding lexeme, line no and column no of the token as output. We use the specifications for scanner and parser as mentioned in the problem statement.

We then test it using the testcases present in the `tests/` sub-directory. The procedure to build and run the program is as follows:
```
mkdir bin
cd src 
make 
cd ..
./bin/lexer tests/test_lexer_1.c # Any of the files having name test_lexer_*.c can be used
```
