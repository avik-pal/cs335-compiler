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
./bin/lexer [-o output_file.txt] tests/test_lexer_1.c     # Any of the files having name test_lexer_*.c can be used
```

## Design Details

* Column and Line Numbers start from 1

* Features supported by the lexer in addition to the standard C specifications:
    * Inheritance
        * `public`, `protected`, `private` have been added as keywords.
        * `<-` is used to define inheritance. `class Car <- public Vehicle` is equivalent to the `C++` declaration of `class Car : public Vehicle`.
        * To declare variables as `public`, `protected`, `private` they need to be enclosed in `{}` instead of the traditional `:` notation in `C++`.