all: ../bin/lexer

../bin/lexer: lexer/lex.yy.c lexer/y.tab.c header/y.tab.h	lexer/accum.o
	@echo "Compiling the final executable ..."
	@gcc -w lexer/accum.o lexer/lex.yy.c lexer/y.tab.c header/y.tab.h -o ../bin/lexer

lexer/lex.yy.c: lexer/c_lex.l
	@echo "Generating lex.yy.c ..."
	@flex $^ 
	@mv lex.yy.c lexer/
header/y.tab.h lexer/y.tab.c: lexer/c_yacc.y
	@echo "Generating y.tab.h and y.tab.c"
	@yacc -d $^
	@mv y.tab.h header/
	@mv y.tab.c lexer/

lexer/accum.o: lexer/accum.c
	@echo "Generating accum.o"
	@gcc -c -w $^ -o lexer/accum.o


.PHONY: clean

clean:
	@rm -f lexer/lex.yy.c lexer/y.tab.c header/y.tab.h lexer/accum.o ../bin/lexer header/*.gch