%token IDENTIFIER CONSTANT STRING_LITERAL SIZEOF
%token PTR_OP INC_OP DEC_OP LEFT_OP RIGHT_OP LE_OP GE_OP EQ_OP NE_OP INHERITANCE_OP
%token AND_OP OR_OP MUL_ASSIGN DIV_ASSIGN MOD_ASSIGN ADD_ASSIGN
%token SUB_ASSIGN LEFT_ASSIGN RIGHT_ASSIGN AND_ASSIGN
%token XOR_ASSIGN OR_ASSIGN TYPE_NAME

%token TYPEDEF EXTERN STATIC AUTO REGISTER
%token CHAR SHORT INT LONG SIGNED UNSIGNED FLOAT DOUBLE CONST VOLATILE VOID
%token STRUCT UNION ENUM ELLIPSIS CLASS
%token PUBLIC PRIVATE PROTECTED

%token CASE DEFAULT IF ELSE SWITCH WHILE DO FOR GOTO CONTINUE BREAK RETURN
%token-table
%start translation_unit
%%

primary_expression
	: IDENTIFIER
	| F_CONSTANT
	| I_CONSTANT
	| STRING_LITERAL
	| LEFT_BRACKET expression RIGHT_BRACKET
	;

postfix_expression
	: primary_expression
	| postfix_expression LEFT_THIRD_BRACKET expression RIGHT_THIRD_BRACKET
	| postfix_expression LEFT_BRACKET RIGHT_BRACKET
	| postfix_expression LEFT_BRACKET argument_expression_list RIGHT_BRACKET
	| postfix_expression DOT IDENTIFIER
	| postfix_expression PTR_OP IDENTIFIER
	| postfix_expression INC_OP
	| postfix_expression DEC_OP
	;

argument_expression_list
	: assignment_expression
	| argument_expression_list COMMA assignment_expression
	;

unary_expression
	: postfix_expression
	| INC_OP unary_expression
	| DEC_OP unary_expression
	| unary_operator cast_expression
	| SIZEOF unary_expression
	| SIZEOF LEFT_BRACKET type_name RIGHT_BRACKET
	;

unary_operator
	: LOGICAL_AND
	| MULTIPLY
	| PLUS
	| MINUS
	| LOGICAL_NOT
	| NOT
	;

cast_expression
	: unary_expression
	| LEFT_BRACKET type_name RIGHT_BRACKET cast_expression
	;

multiplicative_expression
	: cast_expression
	| multiplicative_expression MULTIPLY cast_expression
	| multiplicative_expression DIVIDE cast_expression
	| multiplicative_expression MOD cast_expression
	;

additive_expression
	: multiplicative_expression
	| additive_expression PLUS multiplicative_expression
	| additive_expression MINUS multiplicative_expression
	;

shift_expression
	: additive_expression
	| shift_expression LEFT_OP additive_expression
	| shift_expression RIGHT_OP additive_expression
	;

relational_expression
	: shift_expression
	| relational_expression LESS shift_expression
	| relational_expression GREATER shift_expression
	| relational_expression LE_OP shift_expression
	| relational_expression GE_OP shift_expression
	;

equality_expression
	: relational_expression
	| equality_expression EQ_OP relational_expression
	| equality_expression NE_OP relational_expression
	;

and_expression
	: equality_expression
	| and_expression LOGICAL_AND equality_expression
	;

exclusive_or_expression
	: and_expression
	| exclusive_or_expression EXPONENT and_expression
	;

inclusive_or_expression
	: exclusive_or_expression
	| inclusive_or_expression LOGICAL_OR exclusive_or_expression
	;

logical_and_expression
	: inclusive_or_expression
	| logical_and_expression AND_OP inclusive_or_expression
	;

logical_or_expression
	: logical_and_expression
	| logical_or_expression OR_OP logical_and_expression
	;

conditional_expression
	: logical_or_expression
	| logical_or_expression QUESTION expression COLON conditional_expression
	;

assignment_expression
	: conditional_expression
	| unary_expression assignment_operator assignment_expression
	;

assignment_operator
	: EQ
	| MUL_ASSIGN
	| DIV_ASSIGN
	| MOD_ASSIGN
	| ADD_ASSIGN
	| SUB_ASSIGN
	| LEFT_ASSIGN
	| RIGHT_ASSIGN
	| AND_ASSIGN
	| XOR_ASSIGN
	| OR_ASSIGN
	;

expression
	: assignment_expression
	| expression COMMA assignment_expression
	;

constant_expression
	: conditional_expression
	;

declaration
	: declaration_specifiers SEMICOLON
	| declaration_specifiers init_declarator_list SEMICOLON
	;

declaration_specifiers
	: storage_class_specifier
	| storage_class_specifier declaration_specifiers
	| type_specifier
	| type_specifier declaration_specifiers
	| type_qualifier
	| type_qualifier declaration_specifiers
	;

init_declarator_list
	: init_declarator
	| init_declarator_list COMMA init_declarator
	;

init_declarator
	: declarator
	| declarator EQ initializer
	;

storage_class_specifier
	: TYPEDEF
	| EXTERN
	| STATIC
	| AUTO
	| REGISTER
	;

type_specifier
	: VOID
	| CHAR
	| SHORT
	| INT
	| LONG
	| FLOAT
	| DOUBLE
	| SIGNED
	| UNSIGNED
	| struct_or_union_specifier
	| class_definition
	| enum_specifier
	| TYPE_NAME
	;

inheritance_specifier
	: access_specifier IDENTIFIER
	;

inheritance_specifier_list
	: inheritance_specifier
	| inheritance_specifier_list COMMA inheritance_specifier
	;

access_specifier 
	: PRIVATE
	| PUBLIC
	| PROTECTED
	;

class
	: CLASS
	;

class_definition_head 
	: class
	| class INHERITANCE_OP inheritance_specifier_list
	| class IDENTIFIER 
	| class IDENTIFIER  INHERITANCE_OP inheritance_specifier_list
	;

class_definition 
	: class_definition_head LEFT_CURLY_BRACKET class_internal_definition_list RIGHT_CURLY_BRACKET
	| class_definition_head
	;

class_internal_definition_list
	: class_internal_definition
	| class_internal_definition_list class_internal_definition
	; 

class_internal_definition	
	: access_specifier LEFT_CURLY_BRACKET class_member_list RIGHT_CURLY_BRACKET SEMICOLON
	;

class_member_list
	: class_member
	| class_member_list class_member
	;

class_member
	: function_definition
	| declaration
	;

struct_or_union_specifier
	: struct_or_union IDENTIFIER LEFT_CURLY_BRACKET struct_declaration_list RIGHT_CURLY_BRACKET
	| struct_or_union LEFT_CURLY_BRACKET struct_declaration_list RIGHT_CURLY_BRACKET
	| struct_or_union IDENTIFIER
	;

struct_or_union
	: STRUCT
	| UNION
	;

struct_declaration_list
	: struct_declaration
	| struct_declaration_list struct_declaration
	;

struct_declaration
	: specifier_qualifier_list struct_declarator_list SEMICOLON
	;

specifier_qualifier_list
	: type_specifier specifier_qualifier_list
	| type_specifier
	| type_qualifier specifier_qualifier_list
	| type_qualifier
	;

struct_declarator_list
	: struct_declarator
	| struct_declarator_list COMMA struct_declarator
	;

struct_declarator
	: declarator
	| COLON constant_expression
	| declarator COLON constant_expression
	;

enum_specifier
	: ENUM LEFT_CURLY_BRACKET enumerator_list RIGHT_CURLY_BRACKET
	| ENUM IDENTIFIER LEFT_CURLY_BRACKET enumerator_list RIGHT_CURLY_BRACKET
	| ENUM IDENTIFIER
	;

enumerator_list
	: enumerator
	| enumerator_list COMMA enumerator
	;

enumerator
	: IDENTIFIER
	| IDENTIFIER EQ constant_expression
	;

type_qualifier
	: CONST
	| VOLATILE
	;

declarator
	: pointer direct_declarator
	| direct_declarator
	;

direct_declarator
	: IDENTIFIER
	| LEFT_BRACKET declarator RIGHT_BRACKET
	| direct_declarator LEFT_THIRD_BRACKET constant_expression RIGHT_THIRD_BRACKET
	| direct_declarator LEFT_THIRD_BRACKET RIGHT_THIRD_BRACKET
	| direct_declarator LEFT_BRACKET parameter_type_list RIGHT_BRACKET
	| direct_declarator LEFT_BRACKET identifier_list RIGHT_BRACKET
	| direct_declarator LEFT_BRACKET RIGHT_BRACKET
	;

pointer
	: MULTIPLY
	| MULTIPLY type_qualifier_list
	| MULTIPLY pointer
	| MULTIPLY type_qualifier_list pointer
	;

type_qualifier_list
	: type_qualifier
	| type_qualifier_list type_qualifier
	;


parameter_type_list
	: parameter_list
	| parameter_list COMMA ELLIPSIS
	;

parameter_list
	: parameter_declaration
	| parameter_list COMMA parameter_declaration
	;

parameter_declaration
	: declaration_specifiers declarator
	| declaration_specifiers abstract_declarator
	| declaration_specifiers
	;

identifier_list
	: IDENTIFIER
	| identifier_list COMMA IDENTIFIER
	;

type_name
	: specifier_qualifier_list
	| specifier_qualifier_list abstract_declarator
	;

abstract_declarator
	: pointer
	| direct_abstract_declarator
	| pointer direct_abstract_declarator
	;

direct_abstract_declarator
	: LEFT_BRACKET abstract_declarator RIGHT_BRACKET
	| LEFT_THIRD_BRACKET RIGHT_THIRD_BRACKET
	| LEFT_THIRD_BRACKET constant_expression RIGHT_THIRD_BRACKET
	| direct_abstract_declarator LEFT_THIRD_BRACKET RIGHT_THIRD_BRACKET
	| direct_abstract_declarator LEFT_THIRD_BRACKET constant_expression RIGHT_THIRD_BRACKET
	| LEFT_BRACKET RIGHT_BRACKET
	| LEFT_BRACKET parameter_type_list RIGHT_BRACKET
	| direct_abstract_declarator LEFT_BRACKET RIGHT_BRACKET
	| direct_abstract_declarator LEFT_BRACKET parameter_type_list RIGHT_BRACKET
	;

initializer
	: assignment_expression
	| LEFT_CURLY_BRACKET initializer_list RIGHT_CURLY_BRACKET
	| LEFT_CURLY_BRACKET initializer_list COMMA RIGHT_CURLY_BRACKET
	;

initializer_list
	: initializer
	| initializer_list COMMA initializer
	;

statement
	: labeled_statement
	| compound_statement
	| expression_statement
	| selection_statement
	| iteration_statement
	| jump_statement
	;

labeled_statement
	: IDENTIFIER COLON statement
	| CASE constant_expression COLON statement
	| DEFAULT COLON statement
	;

compound_statement
	: LEFT_CURLY_BRACKET RIGHT_CURLY_BRACKET
	| LEFT_CURLY_BRACKET statement_list RIGHT_CURLY_BRACKET
	| LEFT_CURLY_BRACKET declaration_list RIGHT_CURLY_BRACKET
	| LEFT_CURLY_BRACKET declaration_list statement_list RIGHT_CURLY_BRACKET
	;

declaration_list
	: declaration
	| declaration_list declaration
	;

statement_list
	: statement
	| statement_list statement
	;

expression_statement
	: SEMICOLON
	| expression SEMICOLON
	;

selection_statement
	: IF LEFT_BRACKET expression RIGHT_BRACKET statement
	| IF LEFT_BRACKET expression RIGHT_BRACKET statement ELSE statement
	| SWITCH LEFT_BRACKET expression RIGHT_BRACKET statement
	;

iteration_statement
	: WHILE LEFT_BRACKET expression RIGHT_BRACKET statement
	| DO statement WHILE LEFT_BRACKET expression RIGHT_BRACKET SEMICOLON
	| FOR LEFT_BRACKET expression_statement expression_statement RIGHT_BRACKET statement
	| FOR LEFT_BRACKET expression_statement expression_statement expression RIGHT_BRACKET statement
	;

jump_statement
	: GOTO IDENTIFIER SEMICOLON
	| CONTINUE SEMICOLON
	| BREAK SEMICOLON
	| RETURN SEMICOLON
	| RETURN expression SEMICOLON
	;

translation_unit
	: external_declaration
	| translation_unit external_declaration
	;

external_declaration
	: function_definition
	| declaration
	;

function_definition
	: declaration_specifiers declarator declaration_list compound_statement
	| declaration_specifiers declarator compound_statement
	| declarator declaration_list compound_statement
	| declarator compound_statement
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