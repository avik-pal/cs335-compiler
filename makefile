all: a.out

a.out: lex.yy.c y.tab.c y.tab.h	accum.o src/utils.c
	@echo "Compiling the final executable ..."
	gcc accum.o lex.yy.c y.tab.c y.tab.h src/utils.c

lex.yy.c: src/lexer/c_lex.l
	@echo "Generating lex.yy.c ..."
	flex $^

y.tab.h: src/lexer/c_yacc.y
	@echo "Generating y.tab.h and y.tab.c"
	yacc -d $^

y.tab.c: src/lexer/c_yacc.y
	@echo "Generating y.tab.h and y.tab.c"
	yacc -d $^

accum.o: src/lexer/accum.c
	@echo "Generating accum.o"
	gcc -c $^


.PHONY: clean

clean:
	rm lex.yy.c y.tab.c y.tab.h accum.o a.out y.tab.h.gch