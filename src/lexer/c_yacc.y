%{
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>

nodeType *operator(int oper, int nops, ...);
nodeType *identifier(int i);
nodeType *constant(int value);
void freeNode(nodeType *p);

int yylex(void);
void yyerror(char *s);
int sym[26];
%}

%token IDENTIFIER CONSTANT STRING_LITERAL SIZEOF
%token PTR_OP INC_OP DEC_OP LEFT_OP RIGHT_OP LE_OP GE_OP EQ_OP NE_OP INHERITANCE_OP
%token AND_OP OR_OP MUL_ASSIGN DIV_ASSIGN MOD_ASSIGN ADD_ASSIGN
%token SUB_ASSIGN LEFT_ASSIGN RIGHT_ASSIGN AND_ASSIGN
%token XOR_ASSIGN OR_ASSIGN TYPE_NAME

%token TYPEDEF EXTERN STATIC AUTO REGISTER
%token CHAR SHORT INT LONG SIGNED UNSIGNED FLOAT DOUBLE CONST VOLATILE VOID
// The rules for CLASS INHERITANCE_OP PUBLIC PRIVATE PROTECTED are not yet defined
%token STRUCT UNION ENUM ELLIPSIS CLASS
%token PUBLIC PRIVATE PROTECTED

%token CASE DEFAULT IF ELSE SWITCH WHILE DO FOR GOTO CONTINUE BREAK RETURN
%token-table
%start translation_unit
%%

primary_expression
	: IDENTIFIER 											{$$ = identifier($1,-1);}
	| CONSTANT 												{$$ = const($1);}
	| STRING_LITERAL										{$$ = string_literal($1);}
	| '(' expression ')'									{$$ = $2;}
	;

postfix_expression
	: primary_expression									{$$ = $1;}
	| postfix_expression '[' expression ']'					{$$ = nonTerminal("postfix_exression[expression]", 2, 0, 0, $1, $3);}
	| postfix_expression '(' ')'							{$$ = $1;}
	| postfix_expression '(' argument_expression_list ')' 	{$$ = nonTerminal("postfix_expression", 2, 0, 0, $1, $3);}
	| postfix_expression '.' IDENTIFIER						{$$ = nonTerminal("postfix_expression.IDENTIFIER",2, 0, 1, $1, identifier($3, -1));}
	| postfix_expression PTR_OP IDENTIFIER					{$$ = nonTerminal($2, 2, 0, 1, $1, identifier($3, -1));}
	| postfix_expression INC_OP 							{$$ = nonTerminal($2, 1, 0, $1);}
	| postfix_expression DEC_OP								{$$ = nonTerminal($2, 1, 0, $1);}
	;

argument_expression_list
	: assignment_expression									{$$ =$1;}
	| argument_expression_list ',' assignment_expression	{$$ = nonTerminal("argument_expression_list", 2, 0, 0, $1, $3);}
	;

unary_expression
	: postfix_expression									{$$ = $1;}
	| INC_OP unary_expression								{$$ = nonTerminal($1, 1, 0, $2);}
	| DEC_OP unary_expression								{$$ = nonTerminal($1, 1, 0, $2);}
	| unary_operator cast_expression    					{$$ = nonTerminal($1, 1, 0, $2);}
	| SIZEOF unary_expression								{$$ = nonTerminal($1, 1, 0, $2);}
	| SIZEOF '(' type_name ')'								{$$ = nonTerminal($1, 1, 0, $3);}
	;

unary_operator
	: '&'													{ $$ = otherterminal("&"); }
	| '*'													{ $$ = otherterminal("*"); }
	| '+'													{ $$ = otherterminal("+"); }
	| '-'													{ $$ = otherterminal("-"); }
	| '~'													{ $$ = otherterminal("~"); }
	| '!'													{ $$ = otherterminal("!"); }
	;

cast_expression
	: unary_expression										{$$ = $1;}
	| '(' type_name ')' cast_expression 					{$$ = nonTerminal("cast_expression", 2, 0, 0, $2, $4);}
	;

multiplicative_expression
	: cast_expression 										{$$ = $1;}
	| multiplicative_expression '*' cast_expression 		{$$ = nonTerminal($2, 2, 0, 0, $1, $3);}
	| multiplicative_expression '/' cast_expression 		{$$ = nonTerminal($2, 2, 0, 0, $1, $3);}
	| multiplicative_expression '%' cast_expression 		{$$ = nonTerminal($2, 2, 0, 0, $1, $3);}
	;

additive_expression
	: multiplicative_expression								{$$=$1;}
	| additive_expression '+' multiplicative_expression 	{$$ = nonTerminal($2, 2, 0, 0, $1, $3);}
	| additive_expression '-' multiplicative_expression 	{$$ = nonTerminal($2, 2, 0, 0, $1, $3);}
	;

shift_expression
	: additive_expression									{$$=$1;}
	| shift_expression LEFT_OP additive_expression			{$$ = nonTerminal($2, 2, 0, 0, $1, $3);}
	| shift_expression RIGHT_OP additive_expression			{$$ = nonTerminal($2, 2, 0, 0, $1, $3);}
	;

relational_expression
	: shift_expression										{$$=$1;}
	| relational_expression '<' shift_expression			{$$ = nonTerminal($2, 2, 0, 0, $1, $3);}
	| relational_expression '>' shift_expression			{$$ = nonTerminal($2, 2, 0, 0, $1, $3);}
	| relational_expression LE_OP shift_expression			{$$ = nonTerminal($2, 2, 0, 0, $1, $3);}
	| relational_expression GE_OP shift_expression			{$$ = nonTerminal($2, 2, 0, 0, $1, $3);}
	;

equality_expression
	: relational_expression									{$$=$1;}
	| equality_expression EQ_OP relational_expression		{$$ = nonTerminal($2, 2, 0, 0, $1, $3);}
	| equality_expression NE_OP relational_expression		{$$ = nonTerminal($2, 2, 0, 0, $1, $3);}
	;

and_expression
	: equality_expression 									{$$=$1;}
	| and_expression '&' equality_expression                {$$ = nonTerminal($2, 2, 0, 0, $1, $3);}
	;

exclusive_or_expression
	: and_expression 										{$$=$1;}
	| exclusive_or_expression '^' and_expression 			{$$ = nonTerminal($2, 2, 0, 0, $1, $3);}
	;

inclusive_or_expression
	: exclusive_or_expression								{$$=$1;}
	| inclusive_or_expression '|' exclusive_or_expression	{$$ = nonTerminal($2, 2, 0, 0, $1, $3);}
	;

logical_and_expression
	: inclusive_or_expression								{$$=$1;}
	| logical_and_expression AND_OP inclusive_or_expression	{$$ = nonTerminal($2, 2, 0, 0, $1, $3);}
	;

logical_or_expression
	: logical_and_expression								{$$=$1;}
	| logical_or_expression OR_OP logical_and_expression	{$$ = nonTerminal($2, 2, 0, 0, $1, $3);}
	;

conditional_expression
	: logical_or_expression 								{$$=$1;}
	| logical_or_expression '?' expression ':' conditional_expression    {$$ = nonTerminal("conditional_expression", 3, 0, 0, 0, $1, $3, $5);}
	;

assignment_expression
	: conditional_expression								{$$=$1;}
	| unary_expression assignment_operator assignment_expression	{$$ = nonTerminal($2, 2, 0, 0, $1, $3);}
	;

assignment_operator
	: '='													{$$ = otherterminal($1);}
	| MUL_ASSIGN											{$$ = otherterminal($1);} 
	| DIV_ASSIGN											{$$ = otherterminal($1);}
	| MOD_ASSIGN											{$$ = otherterminal($1);}
	| ADD_ASSIGN											{$$ = otherterminal($1);}
	| SUB_ASSIGN											{$$ = otherterminal($1);}
	| LEFT_ASSIGN											{$$ = otherterminal($1);}
	| RIGHT_ASSIGN											{$$ = otherterminal($1);}
	| AND_ASSIGN											{$$ = otherterminal($1);}
	| XOR_ASSIGN											{$$ = otherterminal($1);}
	| OR_ASSIGN												{$$ = otherterminal($1);}
	;

expression
	: assignment_expression									{$$=$1;}
	| expression ',' assignment_expression					{$$ = nonTerminal("expression", 2, 0, 0, $1, $3);}
	;

constant_expression
	: conditional_expression								{$$=$1;}
	;

declaration
    : declaration_specifiers ';'  { typeName=string(""); $$ = $1;}
    | declaration_specifiers init_declarator_list ';'  { typeName=string(""); $$ = nonterminal("declaration",2,1,1,  $1, $2);}
    | static_assert_declaration   { typeName=string("");$$ = $1;}
    ;
declaration_specifiers
	: storage_class_specifier  { $$ = $1;}
	| storage_class_specifier declaration_specifiers { $$ = nonterminal("declaration_specifiers",2,0,0,$1, $2);}
	| type_specifier { $$ = $1;}
	| type_specifier declaration_specifiers { $$ = nonterminal("declaration_specifiers",2,0,0,  $1, $2);}
	| type_qualifier { $$ = $1;}
	| type_qualifier declaration_specifiers { $$ = nonterminal("declaration_specifiers",2,0,0,  $1, $2);}
	;

init_declarator_list
	: init_declarator { $$ = $1; }
	| init_declarator_list ',' init_declarator { $$ = nonterminal("init_declarator_list",2,0,0, $1, $3);}
	;

init_declarator
	: declarator {  $$ = $1;}
	| declarator '=' initializer { 
                $$ = nonterminal("=",2,0,0, $1, $3);}
	;

storage_class_specifier
	: TYPEDEF {  $$=otherterminal($1); }
	| EXTERN {  $$=otherterminal($1); }
	| STATIC {  $$=otherterminal($1); }
	| AUTO {  $$=otherterminal($1); }
	| REGISTER {  $$=otherterminal($1); }
	;

type_specifier
	: VOID {  $$=otherterminal($1); }
	| CHAR {  $$=otherterminal($1); }
	| SHORT {  $$=otherterminal($1); }
	| INT {  $$=otherterminal($1); }
	| LONG {  $$=otherterminal($1); }
	| FLOAT {  $$=otherterminal($1); }
	| DOUBLE {  $$=otherterminal($1); }
	| SIGNED {  $$=otherterminal($1); } 
	| UNSIGNED {  $$=otherterminal($1); } 
	| struct_or_union_specifier {  $$=otherterminal($1); }
	| enum_specifier {  $$=otherterminal($1); }
	| TYPE_NAME {  $$=otherterminal($1); }
	;

struct_or_union_specifier
	: struct_or_union IDENTIFIER '{' struct_declaration_list '}' { $$ = nonterminal("struct_or_union_specifier",3 ,1, 0,0,$2 $1,$3);}
	| struct_or_union '{' struct_declaration_list '}' { $$ = nonterminal("struct_or_union_specifier",2 , 0,0, $1,$3);}
	| struct_or_union IDENTIFIER { $$ = nonterminal("struct_or_union_specifier",2,1,0,otherterminal($2),$1);}
	;

struct_or_union
	: STRUCT {  $$=otherterminal($1); }
	| UNION {  $$=otherterminal($1); }
	;

struct_declaration_list
	: struct_declaration { $$ = $1;}
	| struct_declaration_list struct_declaration {  $$=nonterminal("struct_declaration_list",2,0,0 $1,$2); }
	;

struct_declaration
	: specifier_qualifier_list struct_declarator_list ';' {  $$=nonterminal("struct_declaration_list",2,0,0 $1,$2); }
	;

specifier_qualifier_list
	: type_specifier specifier_qualifier_list {  $$=nonterminal("struct_qualifier_list",2,0,0 $1,$2); }
	| type_specifier {$$ = $1;}
	| type_qualifier specifier_qualifier_list {  $$=nonterminal("struct_qualifier_list",2,0,0 $1,$2); }
	| type_qualifier { $$ = $1;}
	;

struct_declarator_list
	: struct_declarator { $$ = $1; }
	| struct_declarator_list ',' struct_declarator {  $$=nonterminal("struct_declarator_list",2,0,0 $1,$3); }
	;

struct_declarator
	: declarator { $$ = $1;}
	| ':' constant_expression { $$ = $2 ; }
	| declarator ':' constant_expression {  $$=nonterminal("struct_declarator",2,0,0 $1,$2); }
	;

enum_specifier
	: ENUM '{' enumerator_list '}' {  $$=nonterminal("enum_specifier",2,1,0 otherterminal($1),$3); }
	| ENUM IDENTIFIER '{' enumerator_list '}' {  $$=nonterminal("enum_specifier",3,1,1,0 ,identifier($2,-1), otherterminal($1),$4); }
	| ENUM IDENTIFIER {  $$=nonterminal("enum_specifier",2,1,1 ,identifier($2,-1), otherterminal($1)); }
	;

enumerator_list
	: enumerator { $$ = $1;}
	| enumerator_list ',' enumerator { $$ = nonterminal("enumerator_list",2,0,0,$1,$3);}
	;

enumerator
	: IDENTIFIER { $$ = identifier($1,-1);}
	| IDENTIFIER '=' constant_expression { $$ = nonterminal("enumerator",2,1,0,identifier($1,-1),$3);}
	;

type_qualifier
	: CONST { $$ = otherterminal($1);}
	| VOLATILE { $$ = otherterminal($1);}
	;

declarator
	: pointer direct_declarator { $$ = nonterminal("declarator,2,0,0,$1,$2);}
	| direct_declarator {$$ = $1;}
	;

direct_declarator
	: IDENTIFIER {$$ = identifier($1,-1);}
	| '(' declarator ')' { $$ = $2; }
	| direct_declarator '[' constant_expression ']' { $$ = nonterminal("direct_declarator",2,0,0,$1,$3);}
	| direct_declarator '[' ']' { $$ = nonterminal("direct_declarator",1,0,$1);}
	| direct_declarator '(' parameter_type_list ')' { $$ = nonterminal("direct_declarator",2,0,0,$1,$3);}
	| direct_declarator '(' identifier_list ')' { $$ = nonterminal("direct_declarator",2,0,0,$1,$3);}
	| direct_declarator '(' ')' { $$ = nonterminal("direct_declarator",2,0,$1);}
	;

pointer
	: '*' {$$ = otherterminal($1);}
	| '*' type_qualifier_list { $$ = nonterminal("pointer",1,0,$2);}
	| '*' pointer { $$ = nonterminal("pointer",1,0,$2);}
	| '*' type_qualifier_list pointer { $$ = nonterminal("pointer",2,0,0,$2,$3);}
	;

type_qualifier_list
	: type_qualifier { $$ = $1;}
	| type_qualifier_list type_qualifier {$$ = nonterminal("type_qualifier_list",2,0,0,$1,$2);}
	;


parameter_type_list
	: parameter_list {$$ = $1;}
	| parameter_list ',' ELLIPSIS {$$ = nonterminal("parameter_type_list",2,0,1,$1,otherterminal($3));}
	;

parameter_list
	: parameter_declaration								{$$ = $1; }
	| parameter_list ',' parameter_declaration			{$$ = nonterminal(",", 2, 0, 0, $1, $3); }
	;

parameter_declaration
	: declaration_specifiers declarator					{$$ = nonterminal("parameter_declaration", 2, 0, 0, $1, $2); }
	| declaration_specifiers abstract_declarator		{$$ = nonterminal("parameter_declaration", 2, 0, 0, $1, $2); }
	| declaration_specifiers							{$$ = $1; }
	;

identifier_list
	: IDENTIFIER										{$$ = identifier($1, -1); }
	| identifier_list ',' IDENTIFIER					{$$ = nonterminal(",", 2, 0, 1, $1, identifier($3, -1)); }
	;

type_name
	: specifier_qualifier_list							{$$ = $1; }
	| specifier_qualifier_list abstract_declarator		{$$ = nonterminal("type_name", 2, 0, 0, $1, $2); }
	;

abstract_declarator
	: pointer											{$$ = $1; }
	| direct_abstract_declarator						{$$ = $1; }
	| pointer direct_abstract_declarator				{$$ = nonterminal("abstract_declarator", 2, 0, 0, $1, $2); }
	;

direct_abstract_declarator
	: '(' abstract_declarator ')'								{$$ = $2; }
	| '[' ']'													{$$ = otherterminal("[ ]"); }
	| '[' constant_expression ']'								{$$ = $2; }
	| direct_abstract_declarator '[' ']'						{$$ = nonterminal("direct_abstract_declarator", 2, 0, 1, $1, otherterminal("[ ]")); }
	| direct_abstract_declarator '[' constant_expression ']'	{$$ = nonterminal("direct_abstract_declarator", 2, 0, 0, $1, $3); }
	| '(' ')'													{$$ = otherterminal("( )"); }
	| '(' parameter_type_list ')'								{$$ = $2; }
	| direct_abstract_declarator '(' ')'						{$$ = nonterminal("direct_abstract_declarator", 2, 0, 1, $1, otherterminal("( )")); }
	| direct_abstract_declarator '(' parameter_type_list ')'	{$$ = nonterminal("direct_abstract_declarator", 2, 0, 0, $1, $3); }
	;

initializer
	: assignment_expression										{$$ = $1; }
	| '{' initializer_list '}'									{$$ = $2; }
	| '{' initializer_list ',' '}'								{$$ = nonterminal("initializer", 2, 0, 1, $2, otherterminal(",")); }
	;

initializer_list
	: initializer												{$$ = $1; }
	| initializer_list ',' initializer							{$$ = nonterminal("initializer_list", 2, 0, 0, $1, $3); }
	;

statement
	: labeled_statement											{$$ = $1; }
	| compound_statement										{$$ = $1; }
	| expression_statement										{$$ = $1; }
	| selection_statement										{$$ = $1; }
	| iteration_statement										{$$ = $1; }
	| jump_statement											{$$ = $1; }
	;

labeled_statement
	: IDENTIFIER ':' statement										{$$ = nonterminal("labeled_statement", 2, 1, 0, identifier($1, -1), $3); }
	| CASE constant_expression ':' statement						{$$ = nonterminal("labeled_statement", 3, 1, 0, 0, otherterminal("CASE"), $2, $4); }
	| DEFAULT ':' statement											{$$ = nonterminal("labeled_statement", 2, 1, 0, otherterminal("DEFAULT"), $3); }}
	;

compound_statement
	: '{' '}'													{$$ = otherterminal("{ }"); }
	| '{' statement_list '}'									{$$ = $2; }
	| '{' declaration_list '}'									{$$ = $2; }
	| '{' declaration_list statement_list '}'					{$$ = $2; }		
	;

declaration_list
	: declaration												{$$ = $1; }
	| declaration_list declaration								{$$ = nonterminal("declaration_list", 2, 0, 0, $1, $2); }		
	;

statement_list
	: statement													{$$ = $1; }
	| statement_list statement									{$$ = nonterminal("statement_list", 2, 0, 0, $1, $2); }		
	;

expression_statement
	: ';'													{$$ = otherterminal(";"); }
	| expression ';'										{$$ =  $1; }
	;

selection_statement
	: IF '(' expression ')' statement											{$$ = nonterminal("if-then", 2, 0, 0, $3, $5); }
	| IF '(' expression ')' statement ELSE statement							{$$ = nonterminal("if-then-else", 3, 0, 0, 0, $3, $5, $7); }
	| SWITCH '(' expression ')' statement										{$$ = nonterminal("switch", 2, 0, 0, $3, $5); }
	;

iteration_statement
	: WHILE '(' expression ')' statement																	{$$ = nonterminal("while", 2, 0, 0, $3, $5); }
	| DO statement WHILE '(' expression ')' ';'																{$$ = nonterminal("do-while", 2, 0, 0, $2, $5); }
	| FOR '(' expression_statement expression_statement ')' statement										{$$ = nonterminal("for (expr_stmt expr_stmt expr) stmt", 3, 0, 0, 0, $3, $4, $6); }
	| FOR '(' expression_statement expression_statement expression ')' statement							{$$ = nonterminal("for (expr_stmt expr_stmt expr_stmt expr) stmt", 4, 0, 0, 0, 0, $3, $4, $5, $7); }
	;

jump_statement
	: GOTO IDENTIFIER ';'										{$$ = nonterminal("jump_statement", 2, 1, 1, otherterminal("GOTO"), otherterminal("IDENTIFIER")); }
	| CONTINUE ';'										{$$ = otherterminal("CONTINUE"); }
	| BREAK ';'											{$$ = otherterminal("BREAK"); }
	| RETURN ';'										{$$ = otherterminal("RETURN"); }
	| RETURN expression ';'										{$$ = nonterminal("jump_statement", 2, 1, 0, otherterminal("RETURN"), $2); }
	;

translation_unit
	: external_declaration										 {$$ = $1; }
	| translation_unit external_declaration							{$$ = nonterminal("translation_unit", 2, 0, 0, $1, $2); }
	;

external_declaration
	: function_definition										{$$ = $1; }
	| declaration												{$$ = $1; }
	;

function_definition
	: declaration_specifiers declarator declaration_list compound_statement			{$$ = nonterminal("function_definition", 4, 0, 0, 0, 0, $1, $2, $3, $4); }
	| declaration_specifiers declarator compound_statement							{$$ = nonterminal("function_definition", 3, 0, 0, 0, $1, $2, $3); }
	| declarator declaration_list compound_statement								{$$ = nonterminal("function_definition", 3, 0, 0, 0, $1, $2, $3); }
	| declarator compound_statement													{$$ = nonterminal("function_definition", 2, 0, 0, $1, $2); }
	;

%%
#include <stdio.h>

extern char yytext[];
extern int column_end;

yyerror(s)
char *s;
{
	fflush(stdout);
	printf("\n%*s\n%*s\n", column_end, "^", column_end, s);
}

const char* token_name(int t) {
  return yytname[YYTRANSLATE(t)];
}	