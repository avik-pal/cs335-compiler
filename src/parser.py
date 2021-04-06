import sys
import os
import lex
import ply.yacc as yacc
import argparse

from dot import generate_graph_from_ast, reduce_ast
from symtab import (
    pop_scope,
    push_scope,
    new_scope,
    get_current_symtab,
    get_tmp_label,
    get_tmp_var,
    NUMERIC_TYPES,
    CHARACTER_TYPES,
    DATATYPE2SIZE,
)

flag_for_error = 0
### Error flags
UNKNOWN_ERR = 0
TYPE_CAST_ERR = 1

# Take two types and return the final dataype to cast to.
def type_cast(s1, s2):
    global flag_for_error
    if (s1 not in DATATYPE2SIZE.keys()) or (s2 not in DATATYPE2SIZE.keys()):
        flag_for_error = TYPE_CAST_ERR
        return "error"
    elif s1 == "DOUBLE" or s2 == "DOUBLE":
        return "DOUBLE"
    elif s1 == "FLOAT" or s2 == "FLOAT":
        return "FLOAT"
    elif DATATYPE2SIZE[s1] > DATATYPE2SIZE[s2]:
        return s1
    elif DATATYPE2SIZE[s2] > DATATYPE2SIZE[s1]:
        return s2
    elif s1.startswith("UNSIGNED"):
        return s1
    elif s2.startswith("UNSIGNED"):
        return s2
    else:
        flag_for_error = UNKNOWN_ERR
        return "error"


tokens = lex.tokens

start = "translation_unit"


def p_primary_expression(p):
    """primary_expression : identifier
    | f_const
    | i_const
    | c_const
    | STRING_LITERAL
    | LEFT_BRACKET expression RIGHT_BRACKET"""
    if len(p) == 4:
        p[0] = p[2]
    else:
        p[0] = p[len(p) - 1]


def p_identifier(p):
    """identifier : IDENTIFIER"""
    # TODO: Check presence in symbol table
    symTab = get_current_symtab()
    if symTab.lookup(p[1]) is None:
        raise SyntaxError  # undeclared identifier used
    p[0] = p[1]


def p_f_const(p):
    """f_const : F_CONSTANT"""
    p[0] = {"value": p[1], "code": [], "type": "double"}


def p_i_const(p):
    """i_const : I_CONSTANT"""
    p[0] = {"value": p[1], "code": [], "type": "long"}


def p_c_const(p):
    """c_const : C_CONSTANT"""
    p[0] = {"value": p[1], "code": [], "type": "char"}


def p_postfix_expression(p):
    """postfix_expression : primary_expression
    | postfix_expression LEFT_THIRD_BRACKET expression RIGHT_THIRD_BRACKET
    | postfix_expression LEFT_BRACKET RIGHT_BRACKET
    | postfix_expression LEFT_BRACKET argument_expression_list RIGHT_BRACKET
    | postfix_expression DOT IDENTIFIER
    | postfix_expression PTR_OP IDENTIFIER
    | postfix_expression INC_OP
    | postfix_expression DEC_OP"""
    # p[0] = ("postfix_expression",) + tuple(p[-len(p) + 1 :])

    if len(p) == 2:
        p[0] = p[1]

    elif len(p) == 3:
        if p[1]["type"] != "long":
            raise SyntaxError
        else:
            p[0] = p[1]
            p[0]["value"] = (
                p[0]["value"] + 1 if (p[2] == "++") else p[0]["value"] - 1
            )

    elif len(p) == 4:
        if p[2] == ".":
            # p[1] is a struct
            symTab = get_current_symtab()
            entry = symTab.lookup(p[1])
            if entry is None:
                raise SyntaxError  # undeclared identifier
            struct_entry = symTab.lookup(
                entry["type"]
            )  # not needed if already checked at time of storing
            if struct_entry is None:
                raise SyntaxError  # undeclared struct used
            else:
                # check if p[1] is a struct
                if struct_entry["kind"] == 2:
                    if p[3] not in struct_entry["field names"]:
                        raise SyntaxError  # wrong field name
                    else:
                        p[0]["type"] = struct_entry["field type"][
                            struct_entry["field names"].index(p[3])
                        ]
                        p[0]["value"] = entry["values"][p[3]]
                        p[0]["code"] = []
                else:
                    raise SyntaxError  # no struct defn found

        elif p[2] == "->":
            # p[1] is a pointer to struct
            symTab = get_current_symtab()
            entry = symTab.lookup(p[1])
            # unhandled

        else:
            # function call
            symTab = get_current_symtab()
            entry = symTab.lookup(p[1])
            if entry is None:
                raise SyntaxError
            else:
                # parameter check ?
                if entry["parameter types"] != []:
                    raise SyntaxError  # type mismatch

                p[0]["type"] = entry["return type"]
                p[0]["code"] = []
                p[0]["value"] = p[1]["value"]

    elif len(p) == 5:
        if p[2] == "(":
            # function call
            symTab = get_current_symtab()
            entry = symTab.lookup(p[1])
            if entry is None:
                raise SyntaxError  # no function
            else:
                # type matching
                if p[3]["type"] != entry["parameter types"]:
                    raise SyntaxError  # type mismatch

                p[0]["type"] = entry["return type"]
                p[0]["code"] = []
                p[0]["value"] = p[1]["value"]  # not sure

        elif p[2] == "[":
            pass
        # unhandled


def p_argument_expression_list(p):
    """argument_expression_list : assignment_expression
    | argument_expression_list COMMA assignment_expression"""
    p[0] = ("argument_expression_list",) + tuple(p[-len(p) + 1 :])


def p_unary_expression(p):
    """unary_expression : postfix_expression
    | INC_OP unary_expression
    | DEC_OP unary_expression
    | unary_operator cast_expression
    | SIZEOF unary_expression
    | SIZEOF LEFT_BRACKET type_name RIGHT_BRACKET"""
    p[0] = ("unary_expression",) + tuple(p[-len(p) + 1 :])


def p_unary_operator(p):
    """unary_operator : LOGICAL_AND
    | MULTIPLY
    | PLUS
    | MINUS
    | LOGICAL_NOT
    | NOT"""
    p[0] = ("unary_operator",) + tuple(p[-len(p) + 1 :])


def p_cast_expression(p):
    """cast_expression : unary_expression
    | LEFT_BRACKET type_name RIGHT_BRACKET cast_expression"""
    p[0] = ("cast_expression",) + tuple(p[-len(p) + 1 :])


def p_multiplicative_expression(p):
    """multiplicative_expression : cast_expression
    | multiplicative_expression MULTIPLY cast_expression
    | multiplicative_expression DIVIDE cast_expression
    | multiplicative_expression MOD cast_expression"""
    p[0] = ("multiplicative_expression",) + tuple(p[-len(p) + 1 :])


def p_additive_expression(p):
    """additive_expression : multiplicative_expression
    | additive_expression PLUS multiplicative_expression
    | additive_expression MINUS multiplicative_expression"""
    p[0] = ("additive_expression",) + tuple(p[-len(p) + 1 :])


def p_shift_expression(p):
    """shift_expression : additive_expression
    | shift_expression LEFT_OP additive_expression
    | shift_expression RIGHT_OP additive_expression"""
    p[0] = ("shift_expression",) + tuple(p[-len(p) + 1 :])


def p_relational_expression(p):
    """relational_expression : shift_expression
    | relational_expression LESS shift_expression
    | relational_expression GREATER shift_expression
    | relational_expression LE_OP shift_expression
    | relational_expression GE_OP shift_expression"""
    p[0] = ("relational_expression",) + tuple(p[-len(p) + 1 :])


def p_equality_expression(p):
    """equality_expression : relational_expression
    | equality_expression EQ_OP relational_expression
    | equality_expression NE_OP relational_expression"""
    p[0] = ("equality_expression",) + tuple(p[-len(p) + 1 :])


def p_and_expression(p):
    """and_expression : equality_expression
    | and_expression LOGICAL_AND equality_expression"""
    p[0] = ("and_expression",) + tuple(p[-len(p) + 1 :])


def p_exclusive_or_expression(p):
    """exclusive_or_expression : and_expression
    | exclusive_or_expression EXPONENT and_expression"""
    p[0] = ("exclusive_or_expression",) + tuple(p[-len(p) + 1 :])


def p_inclusive_or_expression(p):
    """inclusive_or_expression : exclusive_or_expression
    | inclusive_or_expression LOGICAL_OR exclusive_or_expression"""
    p[0] = ("inclusive_or_expression",) + tuple(p[-len(p) + 1 :])


def p_logical_and_expression(p):
    """logical_and_expression : inclusive_or_expression
    | logical_and_expression AND_OP inclusive_or_expression"""
    p[0] = ("logical_and_expression",) + tuple(p[-len(p) + 1 :])


def p_logical_or_expression(p):
    """logical_or_expression : logical_and_expression
    | logical_or_expression OR_OP logical_and_expression"""
    p[0] = ("logical_or_expression",) + tuple(p[-len(p) + 1 :])


def p_conditional_expression(p):
    """conditional_expression : logical_or_expression
    | logical_or_expression QUESTION expression COLON conditional_expression"""
    p[0] = ("conditional_expression",) + tuple(p[-len(p) + 1 :])


def p_assignment_expression(p):
    """assignment_expression : conditional_expression
    | unary_expression assignment_operator assignment_expression"""
    p[0] = ("assignment_expression",) + tuple(p[-len(p) + 1 :])


def p_assignment_operator(p):
    """assignment_operator : EQ
    | MUL_ASSIGN
    | DIV_ASSIGN
    | MOD_ASSIGN
    | ADD_ASSIGN
    | SUB_ASSIGN
    | LEFT_ASSIGN
    | RIGHT_ASSIGN
    | AND_ASSIGN
    | XOR_ASSIGN
    | OR_ASSIGN"""
    p[0] = ("assignment_operator",) + tuple(p[-len(p) + 1 :])


def p_expression(p):
    """expression : assignment_expression
    | expression COMMA assignment_expression"""
    p[0] = ("expression",) + tuple(p[-len(p) + 1 :])


def p_constant_expression(p):
    """constant_expression : conditional_expression"""
    p[0] = ("constant_expression",) + tuple(p[-len(p) + 1 :])


def p_declaration(p):
    """declaration : declaration_specifiers SEMICOLON
    | declaration_specifiers init_declarator_list SEMICOLON"""
    p[0] = ("declaration",) + tuple(p[-len(p) + 1 :])


def p_declaration_specifiers(p):
    """declaration_specifiers : storage_class_specifier
    | storage_class_specifier declaration_specifiers
    | type_specifier
    | type_specifier declaration_specifiers
    | type_qualifier
    | type_qualifier declaration_specifiers"""
    p[0] = ("declaration_specifiers",) + tuple(p[-len(p) + 1 :])


def p_init_declarator_list(p):
    """init_declarator_list : init_declarator
    | init_declarator_list COMMA init_declarator"""
    p[0] = ("init_declarator_list",) + tuple(p[-len(p) + 1 :])


def p_init_declarator(p):
    """init_declarator : declarator
    | declarator EQ initializer"""
    p[0] = ("init_declarator",) + tuple(p[-len(p) + 1 :])


def p_storage_class_specifier(p):
    """storage_class_specifier : TYPEDEF
    | EXTERN
    | STATIC
    | AUTO
    | REGISTER"""
    p[0] = ("storage_class_specifier",) + tuple(p[-len(p) + 1 :])


def p_type_specifier(p):
    """type_specifier : VOID
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
    | TYPE_NAME"""
    p[0] = ("type_specifier",) + tuple(p[-len(p) + 1 :])


def p_inheritance_specifier(p):
    """inheritance_specifier : access_specifier IDENTIFIER"""
    p[0] = ("inheritance_specifier",) + tuple(p[-len(p) + 1 :])


def p_inheritance_specifier_list(p):
    """inheritance_specifier_list : inheritance_specifier
    | inheritance_specifier_list COMMA inheritance_specifier"""
    p[0] = ("inheritance_specifier_list",) + tuple(p[-len(p) + 1 :])


def p_access_specifier(p):
    """access_specifier : PRIVATE
    | PUBLIC
    | PROTECTED"""
    p[0] = ("access_specifier",) + tuple(p[-len(p) + 1 :])


def p_class(p):
    """class : CLASS"""
    p[0] = ("class",) + tuple(p[-len(p) + 1 :])


def p_class_definition_head(p):
    """class_definition_head : class
    | class INHERITANCE_OP inheritance_specifier_list
    | class IDENTIFIER
    | class IDENTIFIER  INHERITANCE_OP inheritance_specifier_list"""
    p[0] = ("class_definition_head",) + tuple(p[-len(p) + 1 :])


def p_class_definition(p):
    """class_definition : class_definition_head lbrace class_internal_definition_list rbrace
    | class_definition_head"""
    p[0] = ("class_definition",) + tuple(p[-len(p) + 1 :])


def p_class_internal_definition_list(p):
    """class_internal_definition_list : class_internal_definition
    | class_internal_definition_list class_internal_definition"""
    p[0] = ("class_internal_definition_list",) + tuple(p[-len(p) + 1 :])


def p_class_internal_definition(p):
    """class_internal_definition : access_specifier lbrace class_member_list rbrace SEMICOLON"""
    p[0] = ("class_internal_definition",) + tuple(p[-len(p) + 1 :])


def p_class_member_list(p):
    """class_member_list : class_member
    | class_member_list class_member"""
    p[0] = ("class_member_list",) + tuple(p[-len(p) + 1 :])


def p_class_member(p):
    """class_member : function_definition
    | declaration"""
    p[0] = ("class_member",) + tuple(p[-len(p) + 1 :])


def p_struct_or_union_specifier(p):
    """struct_or_union_specifier : struct_or_union IDENTIFIER LEFT_CURLY_BRACKET struct_declaration_list RIGHT_CURLY_BRACKET
    | struct_or_union LEFT_CURLY_BRACKET struct_declaration_list RIGHT_CURLY_BRACKET
    | struct_or_union IDENTIFIER"""
    p[0] = ("struct_or_union_specifier",) + tuple(p[-len(p) + 1 :])


def p_struct_or_union(p):
    """struct_or_union : STRUCT
    | UNION"""
    p[0] = ("struct_or_union",) + tuple(p[-len(p) + 1 :])


def p_struct_declaration_list(p):
    """struct_declaration_list : struct_declaration
    | struct_declaration_list struct_declaration"""
    p[0] = ("struct_declaration_list",) + tuple(p[-len(p) + 1 :])


def p_struct_declaration(p):
    """struct_declaration : specifier_qualifier_list struct_declarator_list SEMICOLON"""
    p[0] = ("struct_declaration",) + tuple(p[-len(p) + 1 :])


def p_specifier_qualifier_list(p):
    """specifier_qualifier_list : type_specifier specifier_qualifier_list
    | type_specifier
    | type_qualifier specifier_qualifier_list
    | type_qualifier"""
    p[0] = ("specifier_qualifier_list",) + tuple(p[-len(p) + 1 :])


def p_struct_declarator_list(p):
    """struct_declarator_list : struct_declarator
    | struct_declarator_list COMMA struct_declarator"""
    p[0] = ("struct_declarator_list",) + tuple(p[-len(p) + 1 :])


def p_struct_declarator(p):
    """struct_declarator : declarator
    | COLON constant_expression
    | declarator COLON constant_expression"""
    p[0] = ("struct_declarator",) + tuple(p[-len(p) + 1 :])


def p_enum_specifier(p):
    """enum_specifier : ENUM LEFT_CURLY_BRACKET enumerator_list RIGHT_CURLY_BRACKET
    | ENUM IDENTIFIER LEFT_CURLY_BRACKET enumerator_list RIGHT_CURLY_BRACKET
    | ENUM IDENTIFIER"""
    p[0] = ("enum_specifier",) + tuple(p[-len(p) + 1 :])


def p_enumerator_list(p):
    """enumerator_list : enumerator
    | enumerator_list COMMA enumerator"""
    p[0] = ("enumerator_list",) + tuple(p[-len(p) + 1 :])


def p_enumerator(p):
    """enumerator : IDENTIFIER
    | IDENTIFIER EQ constant_expression"""
    p[0] = ("enumerator",) + tuple(p[-len(p) + 1 :])


def p_type_qualifier(p):
    """type_qualifier : CONST
    | VOLATILE"""
    p[0] = ("type_qualifier",) + tuple(p[-len(p) + 1 :])


def p_declarator(p):
    """declarator : pointer direct_declarator
    | direct_declarator"""
    p[0] = ("declarator",) + tuple(p[-len(p) + 1 :])


def p_direct_declarator(p):
    """direct_declarator : IDENTIFIER
    | LEFT_BRACKET declarator RIGHT_BRACKET
    | direct_declarator LEFT_THIRD_BRACKET constant_expression RIGHT_THIRD_BRACKET
    | direct_declarator LEFT_THIRD_BRACKET RIGHT_THIRD_BRACKET
    | direct_declarator LEFT_BRACKET parameter_type_list RIGHT_BRACKET
    | direct_declarator LEFT_BRACKET identifier_list RIGHT_BRACKET
    | direct_declarator LEFT_BRACKET RIGHT_BRACKET"""
    p[0] = ("direct_declarator",) + tuple(p[-len(p) + 1 :])


def p_pointer(p):
    """pointer : MULTIPLY
    | MULTIPLY type_qualifier_list
    | MULTIPLY pointer
    | MULTIPLY type_qualifier_list pointer"""
    p[0] = ("pointer",) + tuple(p[-len(p) + 1 :])


def p_type_qualifier_list(p):
    """type_qualifier_list : type_qualifier
    | type_qualifier_list type_qualifier"""
    p[0] = ("type_qualifier_list",) + tuple(p[-len(p) + 1 :])


def p_parameter_type_list(p):
    """parameter_type_list : parameter_list
    | parameter_list COMMA ELLIPSIS"""
    p[0] = ("parameter_type_list",) + tuple(p[-len(p) + 1 :])


def p_parameter_list(p):
    """parameter_list : parameter_declaration
    | parameter_list COMMA parameter_declaration"""
    p[0] = ("parameter_list",) + tuple(p[-len(p) + 1 :])


def p_parameter_declaration(p):
    """parameter_declaration : declaration_specifiers declarator
    | declaration_specifiers abstract_declarator
    | declaration_specifiers"""
    p[0] = ("parameter_declaration",) + tuple(p[-len(p) + 1 :])


def p_identifier_list(p):
    """identifier_list : IDENTIFIER
    | identifier_list COMMA IDENTIFIER"""
    p[0] = ("identifier_list",) + tuple(p[-len(p) + 1 :])


def p_type_name(p):
    """type_name : specifier_qualifier_list
    | specifier_qualifier_list abstract_declarator"""
    p[0] = ("type_name",) + tuple(p[-len(p) + 1 :])


def p_abstract_declarator(p):
    """abstract_declarator : pointer
    | direct_abstract_declarator
    | pointer direct_abstract_declarator"""
    p[0] = ("abstract_declarator",) + tuple(p[-len(p) + 1 :])


def p_direct_abstract_declarator(p):
    """direct_abstract_declarator : LEFT_BRACKET abstract_declarator RIGHT_BRACKET
    | LEFT_THIRD_BRACKET RIGHT_THIRD_BRACKET
    | LEFT_THIRD_BRACKET constant_expression RIGHT_THIRD_BRACKET
    | direct_abstract_declarator LEFT_THIRD_BRACKET RIGHT_THIRD_BRACKET
    | direct_abstract_declarator LEFT_THIRD_BRACKET constant_expression RIGHT_THIRD_BRACKET
    | LEFT_BRACKET RIGHT_BRACKET
    | LEFT_BRACKET parameter_type_list RIGHT_BRACKET
    | direct_abstract_declarator LEFT_BRACKET RIGHT_BRACKET
    | direct_abstract_declarator LEFT_BRACKET parameter_type_list RIGHT_BRACKET"""
    p[0] = ("direct_abstract_declarator",) + tuple(p[-len(p) + 1 :])


def p_initializer(p):
    """initializer : assignment_expression
    | LEFT_CURLY_BRACKET initializer_list RIGHT_CURLY_BRACKET
    | LEFT_CURLY_BRACKET initializer_list COMMA RIGHT_CURLY_BRACKET"""
    p[0] = ("initializer",) + tuple(p[-len(p) + 1 :])


def p_initializer_list(p):
    """initializer_list : initializer
    | initializer_list COMMA initializer"""
    p[0] = ("initializer_list",) + tuple(p[-len(p) + 1 :])


def p_statement(p):
    """statement : labeled_statement
    | compound_statement
    | expression_statement
    | selection_statement
    | iteration_statement
    | jump_statement"""
    p[0] = ("statement",) + tuple(p[-len(p) + 1 :])


def p_labeled_statement(p):
    """labeled_statement : IDENTIFIER COLON statement
    | CASE constant_expression COLON statement
    | DEFAULT COLON statement"""
    p[0] = ("labeled_statement",) + tuple(p[-len(p) + 1 :])


def p_compound_statement(p):
    """compound_statement : lbrace rbrace
    | lbrace statement_list rbrace
    | lbrace declaration_list rbrace
    | lbrace declaration_list statement_list rbrace"""
    p[0] = ("compound_statement",) + tuple(p[-len(p) + 1 :])


def p_declaration_list(p):
    """declaration_list : declaration
    | declaration_list declaration"""
    p[0] = ("declaration_list",) + tuple(p[-len(p) + 1 :])


def p_statement_list(p):
    """statement_list : statement
    | statement_list statement"""
    p[0] = ("statement_list",) + tuple(p[-len(p) + 1 :])


def p_expression_statement(p):
    """expression_statement : SEMICOLON
    | expression SEMICOLON"""
    p[0] = ("expression_statement",) + tuple(p[-len(p) + 1 :])


def p_selection_statement(p):
    """selection_statement : IF LEFT_BRACKET expression RIGHT_BRACKET statement
    | IF LEFT_BRACKET expression RIGHT_BRACKET statement ELSE statement
    | SWITCH LEFT_BRACKET expression RIGHT_BRACKET statement"""
    p[0] = ("selection_statement",) + tuple(p[-len(p) + 1 :])


def p_iteration_statement(p):
    """iteration_statement : WHILE LEFT_BRACKET expression RIGHT_BRACKET statement
    | DO statement WHILE LEFT_BRACKET expression RIGHT_BRACKET SEMICOLON
    | FOR LEFT_BRACKET expression_statement expression_statement RIGHT_BRACKET statement
    | FOR LEFT_BRACKET expression_statement expression_statement expression RIGHT_BRACKET statement"""
    p[0] = ("iteration_statement",) + tuple(p[-len(p) + 1 :])


def p_jump_statement(p):
    """jump_statement : GOTO IDENTIFIER SEMICOLON
    | CONTINUE SEMICOLON
    | BREAK SEMICOLON
    | RETURN SEMICOLON
    | RETURN expression SEMICOLON"""
    p[0] = ("jump_statement",) + tuple(p[-len(p) + 1 :])


def p_translation_unit(p):
    """translation_unit : external_declaration
    | translation_unit external_declaration"""
    p[0] = ("translation_unit",) + tuple(p[-len(p) + 1 :])


def p_external_declaration(p):
    """external_declaration : function_definition
    | declaration"""
    p[0] = ("external_declaration",) + tuple(p[-len(p) + 1 :])


def p_function_definition(p):
    """function_definition : declaration_specifiers declarator declaration_list compound_statement
    | declaration_specifiers declarator compound_statement
    | declarator declaration_list compound_statement
    | declarator compound_statement"""
    p[0] = ("function_definition",) + tuple(p[-len(p) + 1 :])


def p_lbrace(p):
    """lbrace : LEFT_CURLY_BRACKET"""
    push_scope(new_scope(get_current_symtab()))
    p[0] = ("lbrace",) + tuple(p[-len(p) + 1 :])


def p_rbrace(p):
    """rbrace : RIGHT_CURLY_BRACKET"""
    p[0] = ("rbrace",) + tuple(p[-len(p) + 1 :])
    pop_scope()


def p_error(p):
    global flag_for_error
    # flag_for_error = 1

    if p is not None:
        print("error at line no:  %s :: %s" % ((p.lineno), (p.value)))
        parser.errok()
    else:
        print("Unexpected end of input")


parser = yacc.yacc()


def populate_global_symbol_table() -> None:
    # TODO: Need to do this for all the base functions / keywords
    table = get_current_symtab()

    # Some of the binary operators
    for op in ("+", "-", "/"):
        for _type in NUMERIC_TYPES:
            _type = _type.lower()
            table.insert(
                {
                    "name": op,
                    "return type": _type,
                    "parameter types": [_type, _type],
                },
                1,
            )
        for _type in CHARACTER_TYPES:
            _type = _type.lower()
            # Numeric operations on char is performed by typecasting to integer
            table.insert(
                {
                    "name": op,
                    "return type": "int",
                    "parameter types": [_type, _type],
                },
                1,
            )


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, default=None, help="Input file")
    parser.add_argument(
        "-o", "--output", type=str, default="AST", help="Output file"
    )
    parser.add_argument(
        "-t", "--trim", action="store_true", help="Trimmed ast"
    )
    return parser


if __name__ == "__main__":
    args = get_args().parse_args()
    if args.input == None:
        print("No input file specified")
    else:
        with open(str(args.input), "r+") as file:
            data = file.read()

            push_scope(new_scope(get_current_symtab()))
            populate_global_symbol_table()

            tree = yacc.parse(data)

            pop_scope()
            # if args.output[-4:] == ".dot":
            #     args.output = args.output[:-4]
            # if args.trim:
            #     generate_graph_from_ast(reduce_ast(tree), args.output)
            # else:
            #     generate_graph_from_ast(tree, args.output)
