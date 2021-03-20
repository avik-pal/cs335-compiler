# CS335 IITK Compiler Project

## Description
This project aims to develop a compiler for C language as a part of the course CS335 Compiler Design.

NOTE: To run the code for the respective Milestone, please checkout the tags. Future versions are not supposed to be backwards compatible.

#### Milestone 1

**TAG: lexer**

We develop a scanner using lex and yacc, which takes as input any C program and generates a table of tokens along with the corresponding lexeme, line no and column no of the token as output. We use the specifications for scanner and parser as mentioned in the problem statement.

We test it using the testcases present in the `tests/` sub-directory. The procedure to build and run the program is as follows:
```bash
$ mkdir bin
$ cd src 
$ make 
$ cd ..
$ ./bin/lexer tests/test_lexer_1.c -o out_file
# Any of the files having name test_lexer_*.c can be used
# -o flag redirects the output to the out_file
```

#### Milestone 2

**TAG: parser**

We implemented the parser for an (extended) ANSI C version which outputs a dot file which can then be visualized using any standing dot file viewer. We expect `ply` and `graphviz` to be installed (can be setup using `pip install -r requirements.txt`).

We test it using the testcases present in the `tests/` sub-directory. The procedure to run the program is as follows:
```bash
$ python src/parser/parser.py tests/test_parser_1.c --trim -o ast.dot
# --trim produces a smaller AST meant for humans (though it preserves all the important information needed)
# -o is used to redirect output to a file
# Both are optional
```

How to visualize the AST:
```bash
$ dot -Tps AST.dot -o AST.ps
$ xdg-open AST.ps
```

## Miscellaneous

#### How to move from C yacc -> Python PLY yacc in < 1 mins?

It is pretty simple actually :o. Use the helper `src/parser/yacc_to_ply.py` file, which converts the `c_yacc.y` file present in that directory to the corresponding ply format. Finally, if visual aesthetics is important for you, run `black -l 79 ./src/parser/ply_file.py`.

#### Design Details

* Column and Line Numbers start from 1

* Features supported by the lexer in addition to the standard C specifications:
    * Inheritance
        * `public`, `protected`, `private` have been added as keywords.
        * `<-` is used to define inheritance. `class Car <- public Vehicle` is equivalent to the `C++` declaration of `class Car : public Vehicle`.
        * To declare variables as `public`, `protected`, `private` they need to be enclosed in `{}` instead of the traditional `:` notation in `C++`.
