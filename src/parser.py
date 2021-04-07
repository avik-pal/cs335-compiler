import sys
import os
from typing import cast
import lex
import ply.yacc as yacc
import argparse

from dot import generate_graph_from_ast, reduce_ast
from symtab import (
    BASIC_TYPES,
    pop_scope,
    push_scope,
    new_scope,
    get_current_symtab,
    get_tmp_label,
    get_tmp_var,
    get_default_value,
    NUMERIC_TYPES,
    CHARACTER_TYPES,
    DATATYPE2SIZE,
    BASIC_TYPES,
    FLOATING_POINT_TYPES,
    INTEGER_TYPES,
)

flag_for_error = 0
### Error flags
UNKNOWN_ERR = 0
TYPE_CAST_ERR = 1

# Take two types and return the final dataype to cast to.
def type_cast(s1, s2):
    global flag_for_error
    if s1 == s2:
        return s1

    if (s1 not in BASIC_TYPES) or (s2 not in BASIC_TYPES):
        flag_for_error = TYPE_CAST_ERR
        raise Exception("Type Cast not possible")
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
        raise Exception("Type Cast not possible")
        # return "error"


def cast_value_to_type(val, type):
    # TODO
    # Throw an error if typecast is not possible
    return val


def _get_conversion_function(p, tcast):
    return (
        p
        if p["type"] == tcast
        else {
            "value": f"__convert({p['type']},{tcast})",
            "type": tcast,
            "arguments": [
                p,
                {
                    "value": get_default_value(tcast),
                    "type": tcast,
                    "kind": "CONSTANT",
                },
            ],
            "kind": "FUNCTION CALL",
        }
    )


def resolve_function_name_uniform_types(fname, plist, totype=None):
    symTab = get_current_symtab()
    if len(plist) == 0:
        entry = symTab.lookup(f"{fname}()")
        if entry is None:
            raise Exception
        return f"{fname}()", entry, plist

    if len(plist) == 1:
        entry = symTab.lookup(f"{fname}({plist[0]['type']})")
        if entry is None:
            raise Exception
        return (
            f"{fname}({plist[0]['type']})",
            entry,
            [_get_conversion_function(plist[0], totype) if totype is not None else plist[0]],
        )

    if totype is None:
        t1, t2 = plist[0]["type"], plist[1]["type"]
        tcast = type_cast(t1, t2)
        for t in plist[2:]:
            tcast = type_cast(t, tcast)
    else:
        tcast = totype

    funcname = f"{fname}(" + ",".join([tcast] * len(plist)) + ")"
    entry = get_current_symtab().lookup(funcname)
    if entry is None:
        raise Exception

    args = [_get_conversion_function(p, tcast) for p in plist]

    return funcname, entry, args


LAST_POPPED_TABLE = None
INITIALIZE_PARAMETERS_IN_NEW_SCOPE = None

tokens = lex.tokens

start = "translation_unit"


def p_primary_expression(p):
    """primary_expression : identifier
    | f_const
    | i_const
    | c_const
    | STRING_LITERAL
    | LEFT_BRACKET expression RIGHT_BRACKET"""
    # TODO: String Literal
    if len(p) == 4:
        p[0] = p[2]
    else:
        p[0] = p[len(p) - 1]


def p_identifier(p):
    """identifier : IDENTIFIER"""
    symTab = get_current_symtab()
    entry = symTab.lookup(p[1])
    if entry is None:
        raise Exception  # undeclared identifier used
    p[0] = {
        "value": p[1],
        "code": [],
        "type": entry["type"],
        "kind": "IDENTIFIER",
    }


def p_f_const(p):
    """f_const : F_CONSTANT"""
    p[0] = {"value": p[1], "code": [], "type": "float", "kind": "CONSTANT"}


def p_i_const(p):
    """i_const : I_CONSTANT"""
    p[0] = {"value": p[1], "code": [], "type": "int", "kind": "CONSTANT"}


def p_c_const(p):
    """c_const : C_CONSTANT"""
    p[0] = {"value": p[1], "code": [], "type": "char", "kind": "CONSTANT"}


def p_postfix_expression(p):
    """postfix_expression : primary_expression
    | postfix_expression LEFT_THIRD_BRACKET expression RIGHT_THIRD_BRACKET
    | postfix_expression LEFT_BRACKET RIGHT_BRACKET
    | postfix_expression LEFT_BRACKET argument_expression_list RIGHT_BRACKET
    | postfix_expression DOT IDENTIFIER
    | postfix_expression PTR_OP IDENTIFIER
    | postfix_expression INC_OP
    | postfix_expression DEC_OP"""
    if len(p) == 2:
        p[0] = p[1]

    elif len(p) == 3:
        # VERIFY: Should always have a "type" field
        symTab = get_current_symtab()
        funcname = p[2] + f"({p[1]['type']})"
        entry = symTab.lookup(funcname)
        if entry is None:
            # Uncessary for this case
            raise Exception
        p[0] = {
            "value": funcname,
            "type": entry["return type"],
            "arguments": [p[1]],
            "kind": "FUNCTION CALL",
        }
        nvar = get_tmp_var(p[0]["type"])
        p[0]["code"] = [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
        p[0]["value"] = nvar
        del p[0]["arguments"]
        # p[0] = ("postfix_expression",) + tuple(p[-len(p) + 1 :])

    elif len(p) == 4:
        if p[2] == ".":
            # TODO
            # p[1] is a struct
            symTab = get_current_symtab()
            entry = symTab.lookup(p[1]["value"])
            if entry is None:
                raise Exception  # undeclared identifier
            struct_entry = symTab.lookup(entry["type"])  # not needed if already checked at time of storing
            if struct_entry is None:
                raise Exception  # undeclared struct used
            else:
                # check if p[1] is a struct
                if struct_entry["kind"] == 2:
                    if p[3] not in struct_entry["field names"]:
                        raise Exception  # wrong field name
                    else:
                        p[0]["type"] = struct_entry["field type"][struct_entry["field names"].index(p[3])]
                        p[0]["value"] = entry["values"][p[3]]
                        p[0]["code"] = []
                else:
                    raise Exception  # no struct defn found

        elif p[2] == "->":
            # p[1] is a pointer to struct
            symTab = get_current_symtab()
            entry = symTab.lookup(p[1]["value"])
            # TODO

        else:
            # function call
            symTab = get_current_symtab()
            funcname = p[1]["value"] + "()"
            entry = symTab.lookup(funcname)
            if entry is None:
                raise Exception

            p[0] = {
                "value": funcname,
                "type": entry["return type"],
                "arguments": [],
                "kind": "FUNCTION CALL",
            }
            nvar = get_tmp_var(p[0]["type"])
            p[0]["code"] = [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
            p[0]["value"] = nvar
            del p[0]["arguments"]

    elif len(p) == 5:
        if p[2] == "(":
            # function call
            # TODO: Depends on the argument expression list
            # symTab = get_current_symtab()
            # funcname = p[1]["value"] + "(" + ",".join(p[3]["type"]) + ")"
            # entry = symTab.lookup(funcname)
            # if entry is None:
            #     raise Exception  # no function

            # p[0] = ("FUNCTION CALL", entry["return type"], funcname)
            pass

        elif p[2] == "[":
            pass
            # TODO

    else:
        p[0] = ("postfix_expression",) + tuple(p[-len(p) + 1 :])


def p_argument_expression_list(p):
    """argument_expression_list : assignment_expression
    | argument_expression_list COMMA assignment_expression"""
    # p[0] = ("argument_expression_list",) + tuple(p[-len(p) + 1 :])

    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]


def p_unary_expression(p):
    """unary_expression : postfix_expression
    | INC_OP unary_expression
    | DEC_OP unary_expression
    | unary_operator cast_expression
    | SIZEOF unary_expression
    | SIZEOF LEFT_BRACKET type_name RIGHT_BRACKET"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        # TODO
        p[0] = ("unary_expression",) + tuple(p[-len(p) + 1 :])


def p_unary_operator(p):
    """unary_operator : LOGICAL_AND
    | MULTIPLY
    | PLUS
    | MINUS
    | LOGICAL_NOT
    | NOT"""
    p[0] = p[1]
    # p[0] = ("unary_operator",) + tuple(p[-len(p) + 1 :])


def p_cast_expression(p):
    """cast_expression : unary_expression
    | LEFT_BRACKET type_name RIGHT_BRACKET cast_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        # TODO
        p[0] = ("cast_expression",) + tuple(p[-len(p) + 1 :])


def p_multiplicative_expression(p):
    """multiplicative_expression : cast_expression
    | multiplicative_expression MULTIPLY cast_expression
    | multiplicative_expression DIVIDE cast_expression
    | multiplicative_expression MOD cast_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        fname, entry, args = resolve_function_name_uniform_types(p[2], [p[1], p[3]])

        p[0] = {
            "value": fname,
            "type": entry["return type"],
            "arguments": args,
            "kind": "FUNCTION CALL",
        }
        nvar = get_tmp_var(p[0]["type"])
        p[0]["code"] = [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
        p[0]["value"] = nvar
        del p[0]["arguments"]
        # p[0] = ("multiplicative_expression",) + tuple(p[-len(p) + 1 :])


def p_additive_expression(p):
    """additive_expression : multiplicative_expression
    | additive_expression PLUS multiplicative_expression
    | additive_expression MINUS multiplicative_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        fname, entry, args = resolve_function_name_uniform_types(p[2], [p[1], p[3]])

        p[0] = {
            "value": fname,
            "type": entry["return type"],
            "arguments": args,
            "kind": "FUNCTION CALL",
        }
        nvar = get_tmp_var(p[0]["type"])
        p[0]["code"] = [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
        p[0]["value"] = nvar
        del p[0]["arguments"]
        # p[0] = ("additive_expression",) + tuple(p[-len(p) + 1 :])


def p_shift_expression(p):
    """shift_expression : additive_expression
    | shift_expression LEFT_OP additive_expression
    | shift_expression RIGHT_OP additive_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        fname, entry, args = resolve_function_name_uniform_types(p[2], [p[1], p[3]])

        p[0] = {
            "value": fname,
            "type": entry["return type"],
            "arguments": args,
            "kind": "FUNCTION CALL",
        }
        nvar = get_tmp_var(p[0]["type"])
        p[0]["code"] = [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
        p[0]["value"] = nvar
        del p[0]["arguments"]
        # p[0] = ("shift_expression",) + tuple(p[-len(p) + 1 :])


def p_relational_expression(p):
    """relational_expression : shift_expression
    | relational_expression LESS shift_expression
    | relational_expression GREATER shift_expression
    | relational_expression LE_OP shift_expression
    | relational_expression GE_OP shift_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        fname, entry, args = resolve_function_name_uniform_types(p[2], [p[1], p[3]])

        p[0] = {
            "value": fname,
            "type": entry["return type"],
            "arguments": args,
            "kind": "FUNCTION CALL",
        }
        nvar = get_tmp_var(p[0]["type"])
        p[0]["code"] = [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
        p[0]["value"] = nvar
        del p[0]["arguments"]
        # p[0] = ("relational_expression",) + tuple(p[-len(p) + 1 :])


def p_equality_expression(p):
    """equality_expression : relational_expression
    | equality_expression EQ_OP relational_expression
    | equality_expression NE_OP relational_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        fname, entry, args = resolve_function_name_uniform_types(p[2], [p[1], p[3]])

        p[0] = {
            "value": fname,
            "type": entry["return type"],
            "arguments": args,
            "kind": "FUNCTION CALL",
        }
        nvar = get_tmp_var(p[0]["type"])
        p[0]["code"] = [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
        p[0]["value"] = nvar
        del p[0]["arguments"]
        # p[0] = ("equality_expression",) + tuple(p[-len(p) + 1 :])


def p_and_expression(p):
    """and_expression : equality_expression
    | and_expression LOGICAL_AND equality_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        fname, entry, args = resolve_function_name_uniform_types(p[2], [p[1], p[3]])

        p[0] = {
            "value": fname,
            "type": entry["return type"],
            "arguments": args,
            "kind": "FUNCTION CALL",
        }
        nvar = get_tmp_var(p[0]["type"])
        p[0]["code"] = [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
        p[0]["value"] = nvar
        del p[0]["arguments"]
        # p[0] = ("and_expression",) + tuple(p[-len(p) + 1 :])


def p_exclusive_or_expression(p):
    """exclusive_or_expression : and_expression
    | exclusive_or_expression EXPONENT and_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        fname, entry, args = resolve_function_name_uniform_types(p[2], [p[1], p[3]])

        p[0] = {
            "value": fname,
            "type": entry["return type"],
            "arguments": args,
            "kind": "FUNCTION CALL",
        }
        nvar = get_tmp_var(p[0]["type"])
        p[0]["code"] = [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
        p[0]["value"] = nvar
        del p[0]["arguments"]
        # p[0] = ("exclusive_or_expression",) + tuple(p[-len(p) + 1 :])


def p_inclusive_or_expression(p):
    """inclusive_or_expression : exclusive_or_expression
    | inclusive_or_expression LOGICAL_OR exclusive_or_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        fname, entry, args = resolve_function_name_uniform_types(p[2], [p[1], p[3]])

        p[0] = {
            "value": fname,
            "type": entry["return type"],
            "arguments": args,
            "kind": "FUNCTION CALL",
        }
        nvar = get_tmp_var(p[0]["type"])
        p[0]["code"] = [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
        p[0]["value"] = nvar
        del p[0]["arguments"]
        # p[0] = ("inclusive_or_expression",) + tuple(p[-len(p) + 1 :])


def p_logical_and_expression(p):
    """logical_and_expression : inclusive_or_expression
    | logical_and_expression AND_OP inclusive_or_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        fname, entry, args = resolve_function_name_uniform_types(p[2], [p[1], p[3]])

        p[0] = {
            "value": fname,
            "type": entry["return type"],
            "arguments": args,
            "kind": "FUNCTION CALL",
        }
        nvar = get_tmp_var(p[0]["type"])
        p[0]["code"] = [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
        p[0]["value"] = nvar
        del p[0]["arguments"]
        # p[0] = ("logical_and_expression",) + tuple(p[-len(p) + 1 :])


def p_logical_or_expression(p):
    """logical_or_expression : logical_and_expression
    | logical_or_expression OR_OP logical_and_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        fname, entry, args = resolve_function_name_uniform_types(p[2], [p[1], p[3]])

        p[0] = {
            "value": fname,
            "type": entry["return type"],
            "arguments": args,
            "kind": "FUNCTION CALL",
        }
        nvar = get_tmp_var(p[0]["type"])
        p[0]["code"] = [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
        p[0]["value"] = nvar
        del p[0]["arguments"]
        # p[0] = ("logical_or_expression",) + tuple(p[-len(p) + 1 :])


def p_conditional_expression(p):
    """conditional_expression : logical_or_expression
    | logical_or_expression QUESTION expression COLON conditional_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        # TODO: Translate to an IF Statement
        p[0] = ("conditional_expression",) + tuple(p[-len(p) + 1 :])


def p_assignment_expression(p):
    """assignment_expression : conditional_expression
    | unary_expression assignment_operator assignment_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        if p[2] == "=":
            # TODO: Check invalid type conversions
            arg = _get_conversion_function(p[3], p[1]["type"])
            p[0] = {
                "value": f"__store({p[1]['type']}*,{p[1]['type']})",
                "type": p[1]["type"],
                "arguments": [p[1], arg],
                "kind": "FUNCTION CALL",
            }
            nvar = get_tmp_var(p[0]["type"])
            p[0]["code"] = [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
            p[0]["value"] = nvar
            del p[0]["arguments"]

        else:
            # FIXME: Order of type conversion for +=, -=, etc.
            fname, fentry, args = resolve_function_name_uniform_types(p[2][:-1], [p[1], p[3]])
            expr = {"value": fname, "type": fentry["return type"], "arguments": args, "kind": "FUNCTION CALL"}
            arg = _get_conversion_function(expr, p[1]["type"])
            p[0] = {
                "value": f"__store({p[1]['type']}*,{p[1]['type']})",
                "type": p[1]["type"],
                "arguments": [p[1], arg],
                "kind": "FUNCTION CALL",
            }
            nvar = get_tmp_var(p[0]["type"])
            p[0]["code"] = [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
            p[0]["value"] = nvar
            del p[0]["arguments"]
            # p[0] = ("assignment_expression",) + tuple(p[-len(p) + 1 :])


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
    p[0] = p[1]
    # p[0] = ("assignment_operator",) + tuple(p[-len(p) + 1 :])


def p_expression(p):
    """expression : assignment_expression
    | expression COMMA assignment_expression"""
    if len(p) == 2:
        p[0] = {"value": p[1]["value"], "type": p[1]["type"], "kind": "EXPRESSION", "code": p[1]["code"]}
    else:
        p[0] = {"value": p[3]["value"], "type": p[3]["type"], "kind": "EXPRESSION", "code": p[1]["code"] + p[3]}
        # p[0] = p[1] + p[3]
        # p[0] = ("expression",) + tuple(p[-len(p) + 1 :])


def p_constant_expression(p):
    """constant_expression : conditional_expression"""
    p[0] = p[1]
    # p[0] = ("constant_expression",) + tuple(p[-len(p) + 1 :])


def p_declaration(p):
    """declaration : declaration_specifiers SEMICOLON
    | declaration_specifiers init_declarator_list SEMICOLON"""
    symTab = get_current_symtab()
    if len(p) == 3:
        # TODO
        p[0] = ("declaration",) + tuple(p[-len(p) + 1 :])
    else:
        # TODO: Handle arrays, structs, etc. Right now only handles basic variables
        for _p in p[2]:
            valid, entry = symTab.insert(
                {
                    "name": _p["value"],
                    "type": p[1]["value"],
                    "is_array": False,
                    "dimensions": [],
                    "value": cast_value_to_type(
                        _p.get("store", get_default_value(p[1]["value"])),
                        p[1]["value"],
                    ),
                },
                kind=0,
            )
            if not valid:
                raise Exception(f"Variable {_p['value']} already declared with type {entry['type']}")


def p_declaration_specifiers(p):
    """declaration_specifiers : storage_class_specifier
    | storage_class_specifier declaration_specifiers
    | type_specifier
    | type_specifier declaration_specifiers
    | type_qualifier
    | type_qualifier declaration_specifiers"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = {"value": p[1]["value"] + " " + p[2]["value"], "code": []}


def p_init_declarator_list(p):
    """init_declarator_list : init_declarator
    | init_declarator_list COMMA init_declarator"""
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]
        # p[0] = ("init_declarator_list",) + tuple(p[-len(p) + 1 :])


def p_init_declarator(p):
    """init_declarator : declarator
    | declarator EQ initializer"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        # TODO: Might require different handling for struct or array {1, 2, 3} type initialization
        p[0] = {"value": p[1]["value"], "code": [], "store": p[3]["value"]}
        # p[0] = ("init_declarator",) + tuple(p[-len(p) + 1 :])


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
    # p[0] = ("type_specifier",) + tuple(p[-len(p) + 1 :])

    # Check if it is a valid type
    symTab = get_current_symtab()
    if not symTab.check_type(p[1]):
        raise Exception(f"{p[1]} is not a valid type")
    p[0] = {"value": p[1], "code": []}


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
    if len(p) == 3:
        # TODO
        p[0] = ("declarator",) + tuple(p[-len(p) + 1 :])
    else:
        p[0] = p[1]


def p_direct_declarator_1(p):
    """direct_declarator : IDENTIFIER
    | LEFT_BRACKET declarator RIGHT_BRACKET
    | direct_declarator LEFT_THIRD_BRACKET constant_expression RIGHT_THIRD_BRACKET
    | direct_declarator LEFT_THIRD_BRACKET RIGHT_THIRD_BRACKET
    | direct_declarator LEFT_BRACKET RIGHT_BRACKET"""
    # TODO: Rules 2, 3, 4
    if len(p) == 2:
        # Identifier
        p[0] = {"value": p[1], "code": []}
    elif len(p) == 4:
        if p[1] == "(":
            # TODO: Rule 2
            p[0] = ("direct_declarator",) + tuple(p[-len(p) + 1 :])
        else:
            # Rule 7: No parameter function
            p[0] = {"value": p[1]["value"], "code": [], "parameters": []}
    else:
        # TODO
        p[0] = ("direct_declarator",) + tuple(p[-len(p) + 1 :])


def p_direct_declarator_2(p):
    """direct_declarator : direct_declarator LEFT_BRACKET parameter_type_list RIGHT_BRACKET"""
    global INITIALIZE_PARAMETERS_IN_NEW_SCOPE
    p[0] = {
        "value": p[1]["value"],
        "code": [],
        "parameters": [(_p["type"], _p["value"]) for _p in p[3]],
    }
    INITIALIZE_PARAMETERS_IN_NEW_SCOPE = p[0]["parameters"]


def p_direct_declarator_3(p):
    """direct_declarator : direct_declarator LEFT_BRACKET identifier_list RIGHT_BRACKET"""
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
    if len(p) == 2:
        p[0] = p[1]
    else:
        # TODO
        p[0] = ("parameter_type_list",) + tuple(p[-len(p) + 1 :])


def p_parameter_list(p):
    """parameter_list : parameter_declaration
    | parameter_list COMMA parameter_declaration"""
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]


def p_parameter_declaration_1(p):
    """parameter_declaration : declaration_specifiers declarator"""
    p[0] = {"value": p[2]["value"], "code": [], "type": p[1]["value"]}


def p_parameter_declaration_2(p):
    """parameter_declaration : declaration_specifiers abstract_declarator
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
    if len(p) == 2:
        p[0] = p[1]
    else:
        # TODO
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
    p[0] = p[1]
    # p[0] = ("statement",) + tuple(p[-len(p) + 1 :])


def p_labeled_statement(p):
    """labeled_statement : IDENTIFIER COLON statement
    | CASE constant_expression COLON statement
    | DEFAULT COLON statement"""
    p[0] = ("labeled_statement",) + tuple(p[-len(p) + 1 :])


def p_compound_statement_1(p):
    """compound_statement : lbrace rbrace
    | lbrace statement_list rbrace
    | lbrace declaration_list statement_list rbrace"""
    if len(p) == 3:
        p[0] = {"code": []}
    elif len(p) == 4:
        p[0] = p[2]
    else:
        # Declarations should not be shown in AST
        p[0] = p[3]


def p_compound_statement_2(p):
    """compound_statement : lbrace declaration_list rbrace"""
    p[0] = ("compound_statement",) + tuple(p[-len(p) + 1 :])


def p_declaration_list(p):
    """declaration_list : declaration
    | declaration_list declaration"""
    p[0] = ("declaration_list",) + tuple(p[-len(p) + 1 :])


def p_statement_list(p):
    """statement_list : statement
    | statement_list statement"""
    if len(p) == 2:
        p[0] = p[1]
        p[0]["kind"] = "STATEMENT"
    else:
        p[0] = p[2]
        p[0]["code"] = p[1]["code"] + p[2]["code"]
    # p[0] = ("statement_list",) + tuple(p[-len(p) + 1 :])


def p_expression_statement(p):
    """expression_statement : SEMICOLON
    | expression SEMICOLON"""
    p[0] = {"code": [], "value": None}
    if len(p) == 3:
        p[0] = p[1]
    # p[0] = ("expression_statement",) + tuple(p[-len(p) + 1 :])


def p_selection_statement(p):
    """selection_statement : IF LEFT_BRACKET expression RIGHT_BRACKET statement
    | IF LEFT_BRACKET expression RIGHT_BRACKET statement ELSE statement
    | SWITCH LEFT_BRACKET expression RIGHT_BRACKET statement"""
    if p[1] == "if":
        p[0] = {"code": []}
        elseLabel = get_tmp_label()
        if len(p[3]["code"]) > 0:
            p[0]["code"] += p[3]["code"]
        if p[3]["value"] is not None:
            p[0]["code"] += [["IF", p[3]["value"], "==", "0", "GOTO", elseLabel]]
        if len(p[5]["code"]) > 0:
            p[0]["code"] += p[5]["code"]
        if len(p) == 6:
            p[0]["code"] += [["LABEL", elseLabel]]
        else:
            finishLabel = get_tmp_label()
            p[0]["code"] += [["GOTO", finishLabel], ["LABEL", elseLabel]]
            if len(p[7]["code"]) > 0:
                p[0]["code"] += p[7]["code"]
            p[0]["code"] += [["LABEL", finishLabel]]
    else:
        # TODO
        p[0] = ("selection_statement",) + tuple(p[-len(p) + 1 :])


def p_iteration_statement(p):
    """iteration_statement : WHILE LEFT_BRACKET expression RIGHT_BRACKET statement
    | DO statement WHILE LEFT_BRACKET expression RIGHT_BRACKET SEMICOLON
    | FOR LEFT_BRACKET expression_statement expression_statement RIGHT_BRACKET statement
    | FOR LEFT_BRACKET expression_statement expression_statement expression RIGHT_BRACKET statement"""
    # TODO
    # NOTE: We translate all loops to its equivalent while loop for easy handling
    # beginLabel = get_tmp_label()
    # endLabel = get_tmp_label()
    # if p[1] == "while":
    #     p[0] = {
    #         "value": None, "kind": "LOOP",
    #         "code": [
    #             ["LABEL", beginLabel],
    #             [p[3]["code"]],
    #             []
    #         ]
    #     }
    # elif p[1] == "do":
    #     pass
    # elif p[1] == "for":
    #     if len(p) == 6:
    #         pass
    #     elif len(p) == 7:
    #         pass
    p[0] = ("iteration_statement",) + tuple(p[-len(p) + 1 :])


def p_jump_statement(p):
    """jump_statement : GOTO IDENTIFIER SEMICOLON
    | CONTINUE SEMICOLON
    | BREAK SEMICOLON
    | RETURN SEMICOLON
    | RETURN expression SEMICOLON"""
    # TODO
    p[0] = {"code": []}
    if p[1] == "goto":
        p[0]["code"] += [["GOTO", p[2]["value"]]]
    elif p[1] == "continue":
        pass
    elif p[1] == "break":
        pass
    elif p[1] == "return":
        # Handle return type matching
        pass
    # p[0] = ("jump_statement",) + tuple(p[-len(p) + 1 :])


def p_translation_unit(p):
    """translation_unit : external_declaration
    | translation_unit external_declaration"""
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]
    print(p[0])


def p_external_declaration(p):
    """external_declaration : function_definition
    | declaration"""
    p[0] = p[1]
    # p[0] = ("external_declaration",) + tuple(p[-len(p) + 1 :])


def p_function_definition(p):
    """function_definition : declaration_specifiers declarator declaration_list compound_statement
    | declaration_specifiers declarator compound_statement
    | declarator declaration_list compound_statement
    | declarator compound_statement"""
    symTab = get_current_symtab()
    if len(p) == 4:
        # TODO: Again arrays as parameters wont work for now
        #       Recursive functions wont work for now
        symTab.insert(
            {
                "name": p[2]["value"],
                "return type": p[1]["value"],
                "parameter types": [_p[0] for _p in p[2]["parameters"]],
            },
            kind=1,
        )
        p[0] = p[3]
    else:
        # TODO
        p[0] = ("function_definition",) + tuple(p[-len(p) + 1 :])


def p_lbrace(p):
    """lbrace : LEFT_CURLY_BRACKET"""
    # TODO: Handling insert for arrays in parameters
    push_scope(new_scope(get_current_symtab()))
    symTab = get_current_symtab()
    global INITIALIZE_PARAMETERS_IN_NEW_SCOPE
    if not INITIALIZE_PARAMETERS_IN_NEW_SCOPE is None:
        for param in INITIALIZE_PARAMETERS_IN_NEW_SCOPE:
            symTab.insert(
                {
                    "name": param[1],
                    "type": param[0],
                    "is_array": False,
                    "dimensions": [],
                }
            )
    p[0] = ("lbrace",) + tuple(p[-len(p) + 1 :])


def p_rbrace(p):
    """rbrace : RIGHT_CURLY_BRACKET"""
    global LAST_POPPED_TABLE
    p[0] = ("rbrace",) + tuple(p[-len(p) + 1 :])
    LAST_POPPED_TABLE = pop_scope()


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
        for _type in BASIC_TYPES:
            _type = _type.lower()
            table.insert(
                {
                    "name": op,
                    "return type": _type,
                    "parameter types": [_type, _type],
                },
                1,
            )

    for op in ("<", ">", "<=", ">=", "==", "!="):
        for _type in BASIC_TYPES:
            _type = _type.lower()
            table.insert(
                {
                    "name": op,
                    "return type": "int",  # essentially boolean
                    "parameter types": [_type, _type],
                },
                1,
            )

    for op in "%":
        for _type in INTEGER_TYPES:
            _type = _type.lower()
            table.insert(
                {
                    "name": op,
                    "return type": _type,
                    "parameter types": [_type, _type],
                },
                1,
            )

    for op in ("++", "--"):
        for _type in BASIC_TYPES:
            _type = _type.lower()
            table.insert(
                {
                    "name": op,
                    "return type": _type,
                    "parameter types": [_type],
                },
                1,
            )

    for op in ("__store",):
        for _type in BASIC_TYPES:
            _type = _type.lower()
            table.insert(
                {
                    "name": op,
                    "return type": _type,
                    "parameter types": [f"{_type}*", _type],
                },
                1,
            )


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, default=None, help="Input file")
    parser.add_argument("-o", "--output", type=str, default="AST", help="Output file")
    parser.add_argument("-t", "--trim", action="store_true", help="Trimmed ast")
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
