import sys
import os
from typing import cast
import lex
import ply.yacc as yacc
import argparse
import copy
from dot import parse_code
from type_utils import get_type_fields, get_flookup_type
from symtab import (
    BASIC_TYPES,
    INTEGER_TYPES,
    pop_scope,
    push_scope,
    new_scope,
    get_current_symtab,
    get_tmp_label,
    get_tmp_var,
    get_tmp_closure,
    get_default_value,
    get_global_symtab,
    get_stdlib_codes,
    compute_storage_size,
    NUMERIC_TYPES,
    CHARACTER_TYPES,
    DATATYPE2SIZE,
    BASIC_TYPES,
    FLOATING_POINT_TYPES,
    INTEGER_TYPES,
    SYMBOL_TABLES,
    STATIC_VARIABLE_MAPS,
)
import numpy as np
from mips import generate_mips_from_3ac

flag_for_error = 0
### Error flags
UNKNOWN_ERR = 0
TYPE_CAST_ERR = 1

GLOBAL_ERROR_LIST = []

# Take two types and return the final dataype to cast to.
def _type_cast(s1, s2):
    global flag_for_error
    s1 = s1.upper()
    s2 = s2.upper()
    if s1 == s2:
        return s1
    if s1.count("*") != s2.count("*"):
        err_msg = "Pointer level mismatch. Type Casting not supported"
        GLOBAL_ERROR_LIST.append(err_msg)
        raise SyntaxError
        # raise Exception("Pointer level mismatch. Type Casting not supported")
    if (s1 not in BASIC_TYPES) or (s2 not in BASIC_TYPES):
        flag_for_error = TYPE_CAST_ERR
        err_msg = "Type Cast not possible"
        GLOBAL_ERROR_LIST.append(err_msg)
        raise SyntaxError
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
        err_msg = "Type Cast not possible: UNKNOWN"
        GLOBAL_ERROR_LIST.append(err_msg)
        raise SyntaxError
        # return "error"


def type_cast(s1, s2):
    # print(s1)
    # print(s2)
    if s1.get("pointer_lvl", 0) > 0 and s2.get("pointer_lvl", 0) > 0:
        err_msg = "Can not cast pointer to pointer"
        GLOBAL_ERROR_LIST.append(err_msg)
        raise SyntaxError
    elif s1.get("pointer_lvl", 0) > 0:
        if s2["type"].upper() in INTEGER_TYPES:
            return s1
        else:
            err_msg = f"Can not cast {s2['type']} to pointer!"
            GLOBAL_ERROR_LIST.append(err_msg)
            raise SyntaxError

    elif s2.get("pointer_lvl", 0) > 0:
        if s1["type"].upper() in INTEGER_TYPES:
            return s2
        else:
            err_msg = f"Can not cast {s1['type']} to pointer!"
            GLOBAL_ERROR_LIST.append(err_msg)
            raise SyntaxError
    else:
        return {
            "type": _type_cast(s1["type"], s2["type"]).lower(),
            "pointer_lvl": 0,
        }


def type_cast2(s1, s2):
    if s1.get("pointer_lvl", 0) > 0:

        if s2.get("pointer_lvl", 0) > 0:
            return s1

        elif s2["type"].upper() in INTEGER_TYPES:
            return s1

        else:
            err_msg = f"Can not cast {s2['type']} to pointer!"
            GLOBAL_ERROR_LIST.append(err_msg)
            raise SyntaxError

    elif s2.get("pointer_lvl", 0) > 0:
        if s1["type"].upper() in INTEGER_TYPES:
            return s2
        else:
            err_msg = f"Can not cast {s1['type']} to pointer!"
            GLOBAL_ERROR_LIST.append(err_msg)
            raise SyntaxError
    else:
        return {
            "type": _type_cast(s1["type"], s2["type"]).lower(),
            "pointer_lvl": 0,
        }


def cast_value_to_type(val, type):
    # TODO: Throw an error if typecast is not possible
    return val


def _get_conversion_function(p, tcast):
    t1, t2 = get_flookup_type(p), get_flookup_type(tcast)
    # print(t1, t2, p)
    if t1 == t2:
        return p
    else:
        nvar = get_tmp_var(t2)
        arg = {"value": nvar, "type": t2, "kind": "FUNCTION CALL"}
        arg["code"] = p.get("code", []) + [
            [
                "FUNCTION CALL",
                t2,
                f"__convert({t1},{t2})",
                [
                    p,
                    {
                        "value": get_default_value(t2),
                        "type": t2,
                        "kind": "CONSTANT",
                    },
                ],
                nvar,
            ]
        ]
        return arg


def _get_conversion_function_expr(p, tcast):
    t1, t2 = get_flookup_type(p), get_flookup_type(tcast)
    if t1 == t2:
        return p
    else:
        nvar = get_tmp_var(t2)
        arg = {"value": nvar, "type": t2, "kind": "FUNCTION CALL"}
        arg["code"] = p["code"] + [
            [
                "FUNCTION CALL",
                t1,
                f"__convert({t1},{t2})",
                [
                    p["value"],
                    {
                        "value": get_default_value(t2),
                        "type": t2,
                        "kind": "CONSTANT",
                    },
                ],
                nvar,
            ]
        ]
        return arg


def resolve_function_name_uniform_types(fname, plist, totype=None):
    symTab = get_current_symtab()
    if len(plist) == 0:
        entry = symTab.lookup(f"{fname}()")
        if entry is None:
            err_msg = f"{fname}() : No such function in symbol table"
            GLOBAL_ERROR_LIST.append(err_msg)
            raise SyntaxError
            # raise Exception
        return f"{fname}()", entry, plist

    if len(plist) == 1:
        par_type = get_flookup_type(plist[0])
        entry = symTab.lookup(f"{fname}({par_type})")
        if entry is None:
            err_msg = f"{fname}({plist[0]['type']}) : No such function in symbol table"
            GLOBAL_ERROR_LIST.append(err_msg)
            raise SyntaxError
            # raise Exception
        return (
            f"{fname}({par_type})",
            entry,
            [_get_conversion_function(plist[0], totype) if totype is not None else plist[0]],
        )
    if totype is None:
        # t1, t2 = plist[0]["type"], plist[1]["type"]
        tcast = type_cast(plist[0], plist[1])
        for t in plist[2:]:
            tcast = type_cast(t, tcast)
    else:
        tcast = totype

    funcname = f"{fname}(" + ",".join([get_flookup_type(tcast)] * len(plist)) + ")"
    entry = get_current_symtab().lookup(funcname)
    if entry is None:
        err_msg = f"{funcname} function is not declared!"
        GLOBAL_ERROR_LIST.append(err_msg)
        raise SyntaxError
        # raise Exception(f"{funcname} function is not declared!!")

    args = [_get_conversion_function(p, tcast) for p in plist]

    return funcname, entry, args


def _array_init(p, values, types, dim, arr, idx):
    if len(dim) == 1:
        # print(dim[0])
        count = 0
        tinfo = {
            "type": p[1]["value"],
            "pointer_lvl": arr.get("pointer_lvl", 0),
        }
        for i, (item, t) in enumerate(zip(values, types)):
            count += 1
            expr = _get_conversion_function({"value": item, "type": t, "code": []}, tinfo)
            if len(expr["code"]) > 0:
                p[0]["code"] += expr["code"]
            vname = get_tmp_var()
            p[0]["code"] += [
                [
                    "FUNCTION CALL",
                    get_flookup_type(tinfo),
                    f"__store({p[1]['value']}*,{p[1]['value']})",
                    [
                        {
                            "value": arr["value"],
                            "type": get_flookup_type(tinfo),
                            "index": idx + [i],
                        },
                        {
                            "value": expr["value"],
                            "type": get_flookup_type(tinfo),
                        },
                    ],
                    vname,
                ]
            ]
        if dim[0] == "variable":
            dim[0] = count
            arr["dimensions"][len(idx)] = {"value": count, "type": "int"}
        elif count > dim[0]:
            err_msg = f"[{dim[0]}] Array {arr['value']} filled beyond capacity"
            # print(err_msg)
            GLOBAL_ERROR_LIST.append(err_msg)
            return -1
        else:
            for i in range(count, dim[0]):
                vname = get_tmp_var(get_flookup_type(tinfo))
                p[0]["code"] += [
                    [
                        "FUNCTION CALL",
                        get_flookup_type(tinfo),
                        f"__store({p[1]['value']}*,{p[1]['value']})",
                        [
                            {
                                "value": arr["value"],
                                "type": get_flookup_type(tinfo),
                                "index": idx + [i],
                            },
                            {
                                "value": get_default_value(get_flookup_type(tinfo)),
                                "type": get_flookup_type(tinfo),
                            },
                        ],
                        vname,
                    ]
                ]

        return 1
    else:

        if len(types) > dim[0]:
            err_msg = f"[{dim[0]}] Array {arr['value']} filled beyond capacity"
            # print(err_msg)
            GLOBAL_ERROR_LIST.append(err_msg)
            return -1
        for i in range(dim[0]):
            if i < len(types):
                ret = _array_init(p, values[i], types[i], dim[1:], arr, idx + [i])
                if ret < 0:
                    return -1
            else:
                ret = _array_init(p, [], [], dim[1:], arr, idx + [i])
                if ret < 0:
                    return -1
        return 1


LAST_POPPED_TABLE = None
INITIALIZE_PARAMETERS_IN_NEW_SCOPE = None
LAST_FUNCTION_DECLARATION = None

tokens = lex.tokens

start = "translation_unit"


def p_primary_expression(p):
    """primary_expression : identifier
    | f_const
    | i_const
    | c_const
    | str_literal
    | LEFT_BRACKET expression RIGHT_BRACKET"""
    if len(p) == 4:
        p[0] = p[2]
    else:
        p[0] = p[len(p) - 1]


def p_str_literal(p):
    """str_literal : STRING_LITERAL"""
    p[0] = {
        "value": p[1],
        "code": [],
        "type": "char",
        "pointer_lvl": 1,
        "kind": "CONSTANT",
    }


def p_identifier(p):
    """identifier : IDENTIFIER"""
    symTab = get_current_symtab()
    entry = symTab.lookup(p[1])
    global LAST_FUNCTION_DECLARATION
    val = p[1]
    if type(entry) is list:
        entry = entry[0]
    if entry is None:
        entry = symTab.lookup(p[1] + ".static." + LAST_FUNCTION_DECLARATION)
        val = p[1] + ".static." + LAST_FUNCTION_DECLARATION
        if entry is None:
            err_msg = "Error at line number " + str(p.lineno(1)) + ": Undeclared identifier used"
            GLOBAL_ERROR_LIST.append(err_msg)
            raise SyntaxError
    if entry["kind"] == 1:
        p[0] = {
            "value": val,
            "code": [],
            "type": entry["return type"],
            "pointer_lvl": entry.get("pointer_lvl", 0),
            "kind": "IDENTIFIER",
            # "entry": entry,  # FIXME: Add this back in the final code
        }
    elif entry["kind"] == 0:
        p[0] = {
            "value": val,
            "code": [],
            "type": entry["type"],
            "pointer_lvl": entry.get("pointer_lvl", 0),
            "kind": "IDENTIFIER",
            "is_array": entry.get("is_array", False),
            "dimensions": entry.get("dimensions", [])
            # "entry": entry,  # FIXME: Add this back in the final code
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
        symTab = get_current_symtab()

        # check for pointer arguments
        if p[1].get("pointer_lvl", 0) > 0:
            # obtain offset
            offset = DATATYPE2SIZE[p[1]["type"].upper()]
            arg_type = "long"

        else:
            offset = 1
            arg_type = p[1]["type"]

        funcname = p[2] + f"({arg_type})"
        entry = symTab.lookup(funcname)
        if entry is None:
            # Uncessary for this case
            err_msg = "Error at line number " + str(p.lineno(2)) + ": No entry found in symbol table"
            GLOBAL_ERROR_LIST.append(err_msg)
            raise SyntaxError
            # raise Exception
        p[0] = {
            "value": funcname,
            "type": entry["return type"],
            "arguments": [p[1]],
            "kind": "FUNCTION CALL",
            "p_offset": offset,
        }

        nvar = get_tmp_var(p[0]["type"])
        p[0]["code"] = (
            p[1]["code"] + [[nvar, ":=", p[1]["value"]]] + [[p[1]["value"], ":=", p[1]["value"], p[2][0], str(offset)]]
        )
        p[0]["value"] = nvar
        del p[0]["arguments"]
        # p[0] = ("postfix_expression",) + tuple(p[-len(p) + 1 :])

    elif len(p) == 4:
        if p[2] == ".":
            # p[1] is a struct
            symTab = get_current_symtab()
            struct_identifier = p[1]["value"]
            _ss = struct_identifier.split(".")
            struct_identifier = _ss[0]
            fields_hierarchy = _ss[1:] + [p[3]]

            entry = symTab.lookup(struct_identifier)
            if entry is None:
                err_msg = "Error at line number " + str(p.lineno(1)) + ": Undeclared identifier used"
                GLOBAL_ERROR_LIST.append(err_msg)
                raise SyntaxError
                # raise Exception  # undeclared identifier

            _type = entry["type"]
            for d in fields_hierarchy[:-1]:
                _entry = symTab.lookup_type(_type)
                _type = _entry["field types"][_entry["field names"].index(d)]

            struct_entry = symTab.lookup_type(_type)  # not needed if already checked at time of storing
            if struct_entry is None:
                err_msg = (
                    "Error at line number "
                    + str(p.lineno(1))
                    + ": Undeclared Struct/Union used or using . after a non indexable type"
                )
                GLOBAL_ERROR_LIST.append(err_msg)
                raise SyntaxError
                # raise Exception  # undeclared struct used
            else:
                # check if p[1] is a struct
                # print(p[1],p[3])
                if struct_entry["kind"] in [2, 5]:
                    if p[3] not in struct_entry["field names"]:
                        err_msg = "Error at line number " + str(p.lineno(3)) + ": No such field exists"
                        GLOBAL_ERROR_LIST.append(err_msg)
                        raise SyntaxError
                        # raise Exception  # wrong field name
                    else:
                        p[0] = {
                            "type": struct_entry["field types"][struct_entry["field names"].index(p[3])],
                            "value": p[1]["value"] + "." + p[3],
                            "code": [],
                        }
                        # print(p[0])
                else:
                    err_msg = "Error at line number " + str(p.lineno(1)) + ": No such Struct/Union definition"
                    GLOBAL_ERROR_LIST.append(err_msg)
                    raise SyntaxError
                    # raise Exception  # no struct defn found

        elif p[2] == "->":
            # p[1] is a pointer to struct
            symTab = get_current_symtab()
            entry = symTab.lookup(p[1]["value"])
            if entry is None:
                err_msg = "Error at line number " + str(p.lineno(1)) + ": Undeclared identifier used"
                GLOBAL_ERROR_LIST.append(err_msg)
                raise SyntaxError

            if entry.get("pointer_lvl", 0) == 0:
                err_msg = "Error at line number " + str(p.lineno(1)) + "Cannot de-reference non-pointer"
                GLOBAL_ERROR_LIST.append(err_msg)
                raise SyntaxError

            # TODO
            struct_entry = symTab.lookup_type(entry["type"])
            if struct_entry is None:
                err_msg = "Error at line number " + str(p.lineno(1)) + ": Undeclared Struct/Union used"
                GLOBAL_ERROR_LIST.append(err_msg)
                raise SyntaxError
                # raise Exception  # undeclared struct used
            else:
                # check if p[1] is a struct
                # print(p[1],p[3])
                if struct_entry["kind"] in [2, 5]:
                    if p[3] not in struct_entry["field names"]:
                        err_msg = "Error at line number " + str(p.lineno(3)) + ": No such field exists"
                        GLOBAL_ERROR_LIST.append(err_msg)
                        raise SyntaxError
                        # raise Exception  # wrong field name
                    else:
                        _type = struct_entry["field types"][struct_entry["field names"].index(p[3])]
                        # tvar = get_tmp_var(_type)
                        p[0] = {
                            "type": _type,
                            "value": p[1]["value"] + " -> " + p[3],  # tvar,
                            "code": [],  # [tvar, ":=", p[1]["value"], "->", p[3]]],
                        }
                        # print(p[0])
                else:
                    err_msg = "Error at line number " + str(p.lineno(1)) + ": No such Struct/Union definition"
                    GLOBAL_ERROR_LIST.append(err_msg)
                    raise SyntaxError
                    # raise Exception  # no struct defn found

        else:
            # function call
            symTab = get_current_symtab()
            funcname = p[1]["value"] + "()"
            entry = symTab.lookup(funcname)
            if entry is None:
                err_msg = "Error at line number " + str(p.lineno(1)) + ": No such function in symbol table"
                GLOBAL_ERROR_LIST.append(err_msg)
                raise SyntaxError
                # raise Exception

            p[0] = {
                "value": funcname,
                "type": entry["return type"],
                "arguments": [],
                "kind": "FUNCTION CALL",
            }
            nvar = get_tmp_var(p[0]["type"])
            p[0]["code"] = [
                [
                    p[0]["kind"],
                    p[0]["type"],
                    p[0]["value"],
                    p[0]["arguments"],
                    nvar,
                ]
            ]
            p[0]["value"] = nvar
            del p[0]["arguments"]

    elif len(p) == 5:
        if p[2] == "(":
            # function call
            symTab = get_current_symtab()
            # print(f"function call {p[3]}")
            funcname = p[1]["value"] + "(" + ",".join(p[3]["type"]) + ")"
            entry = symTab.lookup(funcname)
            if entry is None:
                err_msg = "Error at line number " + str(p.lineno(1)) + ": No such function in symbol table"
                GLOBAL_ERROR_LIST.append(err_msg)
                raise SyntaxError
                # raise Exception  # no function

            args = p[3]["value"]
            p[0] = {
                "value": funcname,
                "type": entry["return type"],
                "arguments": args,
                "kind": "FUNCTION CALL",
            }

            nvar = get_tmp_var(p[0]["type"])
            p[0]["code"] = p[3]["code"] + [
                [
                    p[0]["kind"],
                    p[0]["type"],
                    p[0]["value"],
                    p[0]["arguments"],
                    nvar,
                ]
            ]
            p[0]["value"] = nvar
            del p[0]["arguments"]
        # Array indexing
        elif p[2] == "[":
            if p[3]["type"] == "int":
                symTab = get_current_symtab()
                temp_dict = copy.deepcopy(p[1])
                temp_dict["is_array"] = False
                funcname = "__get_array_element" + f"({get_flookup_type(temp_dict)}*,int)"
                # nvar = get_tmp_var(get_flookup_type(temp_dict))
                nvar = get_tmp_var(temp_dict["type"])
                c1 = p[1]["code"]
                c2 = p[3]["code"]
                p[1]["code"] = []
                p[3]["code"] = []
                ventry = symTab.lookup(p[1]["value"])
                # print(
                #     c1
                #     + c2
                #     + [nvar, ":=", p[1]["value"], f"[{p[3]['value']}]"]
                # )
                p[0] = {
                    "value": nvar,
                    "type": temp_dict["type"],
                    "code": c1
                    + c2
                    + [
                        [
                            "FUNCTION CALL",
                            temp_dict["type"],
                            funcname,
                            [p[1], p[3]],
                            nvar,
                        ]
                    ],
                    "potential_pending": max(p[1].get("potential_pending", len(ventry["dimensions"]) if "dimensions" in ventry else 1) - 1, 0),
                    "storing_array": True,
                }
                if p[1].get("potential_pending", 0) >= 1:
                    p[0]["code"] = c1[:-1] + c2 + [[nvar, ":=", c1[-1][2], f"{c1[-1][3]}[{p[3]['value']}]"]]
                else:
                    p[0]["code"] = c1 + c2 + [[nvar, ":=", p[1]["value"], f"[{p[3]['value']}]"]]

                if p[0]["potential_pending"] == 0:
                    c_d = p[0]["code"][:-1]
                    c_l = p[0]["code"][-1]
                    ventry = symTab.lookup(c_l[2])
                    act_dims = [int(z) for z in (ventry["dimensions"] if "dimensions" in ventry else ['0'])]
                    cact_dims = np.clip(np.cumsum(act_dims[::-1])[::-1] - act_dims, a_min=1, a_max=999999)
                    idxs = c_l[3].replace("[", " ").replace("]", " ").split()
                    ttvar1 = get_tmp_var("int")
                    if len(idxs) > 1:
                        ttvar2 = get_tmp_var("int")
                        c_d.append([ttvar1, ":=", idxs[0], "*", str(cact_dims[0])])
                    else:
                        c_d.append([ttvar1, ":=", idxs[0]])
                    for _i in range(1, len(idxs)):
                        _v = str(cact_dims[_i])
                        if _i == len(idxs) - 1:
                            c_d.append([ttvar2, ":=", idxs[_i]])
                        else:
                            c_d.append([ttvar2, ":=", idxs[_i], "*", _v])
                        c_d.append([ttvar1, ":=", ttvar1, "+", ttvar2])
                    # c_d.append([c_l[0], ":=", c_l[2], f"[{ttvar1}]"])
                    c_d.append(
                        [
                            "FUNCTION CALL",
                            temp_dict["type"],
                            funcname,
                            [{"value": c_l[2]}, {"value": ttvar1}],
                            c_l[0],
                        ]
                    )
                    p[0]["code"] = c_d

                del temp_dict
            else:
                err_msg = "Error at line number " + str(p.lineno(3)) + ": Not an integer index"
                GLOBAL_ERROR_LIST.append(err_msg)
                raise SyntaxError
                # raise Exception

    else:
        p[0] = ("postfix_expression",) + tuple(p[-len(p) + 1 :])


def p_argument_expression_list(p):
    """argument_expression_list : assignment_expression
    | argument_expression_list COMMA assignment_expression"""
    # p[0] = ("argument_expression_list",) + tuple(p[-len(p) + 1 :])

    p[0] = {"code": [], "type": [], "value": []}

    if len(p) == 2:
        ind = 1
    else:
        ind = 3
        p[0]["code"] += p[1]["code"]
        p[0]["type"] += p[1]["type"]
        p[0]["value"] += p[1]["value"]
    # print(f"arg_expr_list {p[1]}")
    out_dict = copy.deepcopy(p[ind])
    if p[ind].get("is_array", False):
        out_dict["dimensions"][0] = "variable"
    p[0]["code"] += out_dict["code"]
    p[0]["type"].append(get_flookup_type(out_dict))
    p[0]["value"].append(out_dict["value"])
    del out_dict


def p_unary_expression(p):
    """unary_expression : postfix_expression
    | INC_OP unary_expression
    | DEC_OP unary_expression
    | unary_operator cast_expression
    | SIZEOF unary_expression
    | SIZEOF LEFT_BRACKET type_name RIGHT_BRACKET"""
    if len(p) == 2:
        p[0] = p[1]

    elif len(p) == 3:
        if p[1] == "++" or p[1] == "--":
            symTab = get_current_symtab()

            # check for pointer arguments
            if p[2].get("pointer_lvl", 0) > 0:
                # obtain offset
                offset = DATATYPE2SIZE[p[2]["type"].upper()]
                arg_type = "long"

            else:
                offset = 1
                arg_type = p[2]["type"]

            funcname = p[1] + f"({arg_type})"
            entry = symTab.lookup(funcname)

            if entry is None:
                err_msg = "Error at line number " + str(p.lineno(1)) + ": No such function in symbol table"
                GLOBAL_ERROR_LIST.append(err_msg)
                raise SyntaxError
                # raise Exception

            p[0] = {
                "value": funcname,
                "type": entry["return type"],
                "arguments": [p[2]],
                "kind": "FUNCTION CALL",
                "p_offset": offset,
            }

            nvar = get_tmp_var(p[0]["type"])
            # p[0]["code"] = [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
            p[0]["code"] = (
                p[1]["code"]
                + [[p[1]["value"], ":=", p[1]["value"], p[2][0], str(offset)]]
                + [[nvar, ":=", p[1]["value"]]]
            )
            # print(p[0]["code"])
            p[0]["value"] = nvar
            del p[0]["arguments"]

        elif p[1] == "sizeof":
            symTab = get_current_symtab()
            entry = symTab.lookup(p[2]["value"])
            typeentry = symTab.lookup_type(entry["type"])
            p[0] = {
                "type": "int",
                "value": str(compute_storage_size(entry, typeentry)),
            }

            p[0]["code"] = p[2]["code"]

        elif p[1].startswith("*"):
            p[0] = copy.deepcopy(p[2])
            # p[0]["deref"] = p[0].get("deref", 0) + len(p[1])
            if p[2].get("pointer_lvl", 0) > 0:
                nvar = get_tmp_var(get_flookup_type(p[2]))
                p[0]["code"] = [
                    [
                        "FUNCTION CALL",
                        get_flookup_type(p[2]),
                        f"__deref({get_flookup_type(p[2])})",
                        [
                            {
                                "value": p[2]["value"],
                                "type": get_flookup_type(p[2]),
                                "kind": p[2].get("kind", "CONSTANT"),
                                "code": p[2].get("code", []),
                            }
                        ],
                        nvar,
                    ]
                ]
                p[0]["pointer_lvl"] -= 1
                p[0]["value"] = nvar
            else:
                err_msg = "Cannot Dereference a non-pointer : %s" % ((p[0]["value"]))
                GLOBAL_ERROR_LIST.append(err_msg)

        elif p[1].startswith("&"):

            # TODO: handle cases when len(p[1]["code"] > 1
            # assert len(p[2]["code"]) <= 1, AssertionError(f"Fix this case-> {p[2]['code']}, len: {len(p[2]['code'])}")

            tmp_code = copy.deepcopy(p[2]["code"])

            if len(p[2]["code"]) > 1:
                f_call_ind = len(p[2]["code"]) - 1
            else:
                f_call_ind = 0

            if (not p[2]["code"] == []) and (p[2]["code"][f_call_ind][2].startswith("__get_array_element")):  # &a[i]
                tmp_code = p[2]["code"][:-1]
                rep = p[2]["code"][f_call_ind][3][0]["value"] + " [" + p[2]["code"][f_call_ind][3][1]["value"] + "]"
                p[2]["value"] = rep

            p[0] = copy.deepcopy(p[2])
            p[0]["code"] = tmp_code
            p[0]["pointer_lvl"] = p[0].get("pointer_lvl", 0) + 1
            nvar = get_tmp_var(get_flookup_type(p[0]))
            p[0]["code"] += [
                [
                    "FUNCTION CALL",
                    get_flookup_type(p[2]),
                    f"__ref({get_flookup_type(p[2])})",
                    [
                        {
                            "value": p[2]["value"],
                            "type": get_flookup_type(p[2]),
                            "kind": p[2].get("kind", "CONSTANT"),
                        }
                    ],
                    nvar,
                ]
            ]
            # print(p[0]["pointer_lvl"])
            p[0]["value"] = nvar
            # print(p[0])

        elif p[1] == "+" or p[1] == "-" or p[1] == "!":

            symTab = get_current_symtab()
            arg = p[2]["type"]
            funcname = p[1] + f"({arg})"
            entry = symTab.lookup(funcname)

            if entry is None:
                err_msg = "Error at line number " + str(p.lineno(1)) + ": No such function in symbol table"
                GLOBAL_ERROR_LIST.append(err_msg)
                raise SyntaxError
                # raise Exception

            p[0] = {
                "value": funcname,
                "type": entry["return type"],
                "arguments": [p[2]],
                "kind": "FUNCTION CALL",
            }

            nvar = get_tmp_var(p[0]["type"])
            # p[0]["code"] = [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
            p[0]["code"] = [[nvar, ":=", p[1], p[0]["arguments"][0]["value"]]]
            p[0]["value"] = nvar
            del p[0]["arguments"]

        else:
            # TODO: depends on cast expression
            pass

    else:
        if p[1] == "sizeof":
            p[0] = {
                "type": "int",
                "value": str(compute_storage_size({"value": p[3]["value"], "type": p[3]["value"]}, None)),
                "code": p[3]["code"],
            }

    # p[0] = ("unary_expression",) + tuple(p[-len(p) + 1 :])


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
        # TODO: set correct pointer level
        p_level = p[2].get("pointer_lvl", 0)
        p[0] = _get_conversion_function_expr(p[4], {"type": p[2]["value"], "pointer_lvl": p_level})

        # p[0] = ("cast_expression",) + tuple(p[-len(p) + 1 :])


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
        codes = []
        for _a in args:
            if len(_a["code"]) == 0:
                continue
            codes += _a["code"]
            _a["code"] = []
        # p[0]["code"] = codes + [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
        p[0]["code"] = codes + [
            [
                nvar,
                ":=",
                p[0]["arguments"][0]["value"],
                p[2],
                p[0]["arguments"][1]["value"],
            ]
        ]
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
        codes = []
        for _a in args:
            if len(_a["code"]) == 0:
                continue
            codes += _a["code"]
            _a["code"] = []
        # p[0]["code"] = codes + [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
        p[0]["code"] = codes + [
            [
                nvar,
                ":=",
                p[0]["arguments"][0]["value"],
                p[2],
                p[0]["arguments"][1]["value"],
            ]
        ]
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
        codes = []
        for _a in args:
            if len(_a["code"]) == 0:
                continue
            codes += _a["code"]
            _a["code"] = []
        # p[0]["code"] = codes + [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
        p[0]["code"] = codes + [
            [
                nvar,
                ":=",
                p[0]["arguments"][0]["value"],
                p[2],
                p[0]["arguments"][1]["value"],
            ]
        ]
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
        codes = []
        for _a in args:
            if len(_a["code"]) == 0:
                continue
            codes += _a["code"]
            _a["code"] = []
        # p[0]["code"] = codes + [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
        p[0]["code"] = codes + [
            [
                nvar,
                ":=",
                p[0]["arguments"][0]["value"],
                p[2],
                p[0]["arguments"][1]["value"],
            ]
        ]
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
        codes = []
        for _a in args:
            if len(_a["code"]) == 0:
                continue
            codes += _a["code"]
            _a["code"] = []
        # p[0]["code"] = codes + [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
        p[0]["code"] = codes + [
            [
                nvar,
                ":=",
                p[0]["arguments"][0]["value"],
                p[2],
                p[0]["arguments"][1]["value"],
            ]
        ]
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
        codes = []
        for _a in args:
            if len(_a["code"]) == 0:
                continue
            codes += _a["code"]
            _a["code"] = []
        # p[0]["code"] = codes + [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
        p[0]["code"] = codes + [
            [
                nvar,
                ":=",
                p[0]["arguments"][0]["value"],
                p[2],
                p[0]["arguments"][1]["value"],
            ]
        ]
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
        codes = []
        for _a in args:
            if len(_a["code"]) == 0:
                continue
            codes += _a["code"]
            _a["code"] = []
        p[0]["code"] = codes + [
            [
                p[0]["kind"],
                p[0]["type"],
                p[0]["value"],
                p[0]["arguments"],
                nvar,
            ]
        ]
        # p[0]["code"] = codes + [[nvar, ":=", p[0]["arguments"][0]["value"], p[2], p[0]["arguments"][1]["value"]]]
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
        codes = []
        for _a in args:
            if len(_a["code"]) == 0:
                continue
            codes += _a["code"]
            _a["code"] = []
        p[0]["code"] = codes + [
            [
                p[0]["kind"],
                p[0]["type"],
                p[0]["value"],
                p[0]["arguments"],
                nvar,
            ]
        ]
        # p[0]["code"] = codes + [[nvar, ":=", p[0]["arguments"][0]["value"], p[2], p[0]["arguments"][1]["value"]]]
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
        codes = []
        for _a in args:
            if len(_a["code"]) == 0:
                continue
            codes += _a["code"]
            _a["code"] = []
        # p[0]["code"] = codes + [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
        p[0]["code"] = codes + [
            [
                nvar,
                ":=",
                p[0]["arguments"][0]["value"],
                p[2],
                p[0]["arguments"][1]["value"],
            ]
        ]
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
        codes = []
        for _a in args:
            if len(_a["code"]) == 0:
                continue
            codes += _a["code"]
            _a["code"] = []
        # p[0]["code"] = codes + [[p[0]["kind"], p[0]["type"], p[0]["value"], p[0]["arguments"], nvar]]
        p[0]["code"] = codes + [
            [
                nvar,
                ":=",
                p[0]["arguments"][0]["value"],
                p[2],
                p[0]["arguments"][1]["value"],
            ]
        ]
        p[0]["value"] = nvar
        del p[0]["arguments"]
        # p[0] = ("logical_or_expression",) + tuple(p[-len(p) + 1 :])


def p_conditional_expression(p):
    """conditional_expression : logical_or_expression
    | logical_or_expression QUESTION expression COLON conditional_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = {"code": []}
        tcast = type_cast(p[3], p[5])

        vname = get_tmp_var(tcast["type"])

        cond_code = []
        elseLabel = get_tmp_label()
        endLabel = get_tmp_label()
        if len(p[1]["code"]) > 0:
            cond_code += p[1]["code"]
        if p[1]["value"] is not None:
            expr = _get_conversion_function_expr(p[1], {"type": "int", "pointer_lvl": 0})
            if len(expr["code"]) > 0:
                cond_code += expr["code"]
            cond_code += [["IF", expr["value"], "==", "0", "GOTO", elseLabel]]

        succ_code = []
        if len(p[3]["code"]) > 0:
            expr = _get_conversion_function_expr(p[3], tcast)
            succ_code += p[3]["code"]
        else:
            expr = _get_conversion_function(p[3], tcast)
        if len(expr["code"]) > 0:
            succ_code += expr["code"]
        succ_code += [[vname, ":=", expr["value"]], ["GOTO", endLabel]]

        fail_code = []
        if len(p[5]["code"]) > 0:
            expr = _get_conversion_function_expr(p[5], tcast)
            fail_code += p[5]["code"]
        else:
            expr = _get_conversion_function(p[5], tcast)
        if len(expr["code"]) > 0:
            fail_code += expr["code"]
        fail_code += [[vname, ":=", expr["value"]]]

        p[0]["code"] += cond_code + succ_code + [[elseLabel + ":"]] + fail_code + [[endLabel + ":"]]

        p[0]["type"] = tcast["type"]
        p[0]["pointer_lvl"] = tcast["pointer_lvl"]
        p[0]["value"] = vname

        raise Exception("Conditional will only work in the special case of no function call / register swap")


def p_assignment_expression(p):
    """assignment_expression : conditional_expression
    | unary_expression assignment_operator assignment_expression"""
    if len(p) == 2:
        # print(f"ass_expr {p[1]}")
        p[0] = p[1]
    else:
        # print(f"ass_expr {p[1]}{p[2]}{p[3]}")

        if p[2] == "=":
            arg = _get_conversion_function(p[3], p[1])
            p[0] = {
                "value": f"__store({p[1]['type']}*,{p[1]['type']})",
                "type": p[1]["type"],
                "arguments": [p[1], arg],
                "kind": "FUNCTION CALL",
            }
            # TODO: handle cases when len(p[1]["code"] > 1
            # assert len(p[1]["code"]) <= 1, AssertionError(f"Fix this case-> {p[1]['code']}, len: {len(p[1]['code'])}")

            if len(p[1]["code"]) > 1:
                tmp_code = p[1]["code"][:-1]
                f_call_ind = len(p[1]["code"]) - 1
            else:
                tmp_code = []
                f_call_ind = 0

            if (not p[1]["code"] == []) and (p[1]["code"][f_call_ind][2].startswith("__get_array_element")):
                rep = p[1]["code"][f_call_ind][3][0]["value"] + "[" + p[1]["code"][f_call_ind][3][1]["value"] + "]"
                p[0]["arguments"][0]["value"] = rep
                p[1]["code"] = tmp_code

            elif (not p[1]["code"] == []) and (p[1]["code"][f_call_ind][2].startswith("__deref")):
                rep = "*" + p[1]["code"][f_call_ind][3][0]["value"]
                p[0]["arguments"][0]["value"] = rep
                p[1]["code"] = tmp_code

            nvar = get_tmp_var(p[0]["type"])
            p[0]["code"] = (
                p[1]["code"]
                + arg["code"]
                + [
                    [
                        p[0]["kind"],
                        p[0]["type"],
                        p[0]["value"],
                        p[0]["arguments"],
                        nvar,
                    ]
                ]
            )
            p[0]["value"] = nvar
            arg["code"] = []
            p[1]["code"] = []
            del p[0]["arguments"]
            # print(p[0])

        else:
            fname, fentry, args = resolve_function_name_uniform_types(p[2][:-1], [p[1], p[3]])
            codes = []
            for _a in args:
                if len(_a["code"]) == 0:
                    continue
                codes += _a["code"]
                _a["code"] = []
            nvar = get_tmp_var(fentry["return type"])
            expr = {
                "value": nvar,
                "type": fentry["return type"],
                "arguments": args,
                "kind": "FUNCTION CALL",
                "code": [[nvar, ":=", args[0]["value"], p[2][:-1], args[1]["value"]]],
            }
            arg = _get_conversion_function(expr, p[1])
            codes += arg["code"]
            arg["code"] = []
            p[0] = {
                "value": f"__store({p[1]['type']}*,{p[1]['type']})",
                "type": p[1]["type"],
                "arguments": [p[1], arg["value"]],
                "kind": "FUNCTION CALL",
            }
            nvar = get_tmp_var(p[0]["type"])
            p[0]["code"] = codes + [
                [
                    p[0]["kind"],
                    p[0]["type"],
                    p[0]["value"],
                    p[0]["arguments"],
                    nvar,
                ]
            ]
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
        p[0] = {
            "value": p[1]["value"],
            "type": p[1]["type"],
            "pointer_lvl": p[1].get("pointer_lvl", 0),
            "kind": "EXPRESSION",
            "code": p[1]["code"],
        }
    else:
        p[0] = {
            "value": p[3]["value"],
            "type": p[3]["type"],
            "pointer_lvl": p[3].get("pointer_lvl", 0),
            "kind": "EXPRESSION",
            "code": p[1]["code"] + p[3]["code"],
        }
        # p[0] = p[1] + p[3]
        # p[0] = ("expression",) + tuple(p[-len(p) + 1 :])


def p_constant_expression(p):
    """constant_expression : conditional_expression"""
    p[0] = p[1]
    # p[0] = ("constant_expression",) + tuple(p[-len(p) + 1 :])


def p_declaration(p):
    """declaration : declaration_specifiers SEMICOLON
    | declaration_specifiers init_declarator_list SEMICOLON"""
    global LAST_FUNCTION_DECLARATION
    symTab = get_current_symtab()
    p[0] = {"code": [], "value": ""}
    # print(p[1], len(p), p[2], p.lineno(1))
    if len(p) == 3:
        pass
        # p[0] = ("declaration",) + tuple(p[-len(p) + 1 :])
    else:
        tinfo = p[1]["value"]
        is_static = False
        if tinfo.startswith("static"):
            tinfo = tinfo[7:]
            is_static = True

        for _p in p[2]:
            if len(_p["code"]) > 0:
                p[0]["code"] += _p["code"]
            if "store" in _p:
                if not _p.get("is_array", False) and _p["store"].get("types", None) is None:
                    _p["type"] = p[1]["value"]
                    if len(_p["code"]) > 0:
                        _tcast = type_cast2(
                            _p["store"],
                            {
                                "type": tinfo,
                                "pointer_lvl": _p.get("pointer_lvl", 0),
                            },
                        )
                        expr = _get_conversion_function_expr(
                            _p["store"],
                            {
                                "type": tinfo,
                                "pointer_lvl": _p.get("pointer_lvl", 0),
                            },
                        )
                        if len(expr["code"]) > 0:
                            p[0]["code"] += expr["code"]
                    else:
                        _tcast = type_cast2(
                            _p["store"],
                            {
                                "type": tinfo,
                                "pointer_lvl": _p.get("pointer_lvl", 0),
                            },
                        )
                        expr = _get_conversion_function(
                            _p["store"],
                            {
                                "type": tinfo,
                                "pointer_lvl": _p.get("pointer_lvl", 0),
                            },
                        )
                        if len(expr["code"]) > 0:
                            p[0]["code"] += expr["code"]
                    vname = get_tmp_var()
                    __t = get_flookup_type(_p)
                    p[0]["code"] += [
                        [
                            "FUNCTION CALL",
                            tinfo,
                            f"__store({__t}*,{__t})",
                            [
                                {"value": _p["value"], "type": tinfo},
                                {"value": expr["value"], "type": tinfo},
                            ],
                            vname,
                        ]
                    ]
                    # p[0]["value"] = vname
                elif not _p.get("is_array", False) and _p["store"].get("types", None) is not None:
                    # print(_p)
                    struct_entry = symTab.lookup_type(p[1]["value"])
                    if struct_entry is None:
                        err_msg = "Error at line number " + str(p.lineno(1)) + ": Undeclared struct used"
                        GLOBAL_ERROR_LIST.append(err_msg)
                        raise SyntaxError
                        # raise Exception  # undeclared struct used
                    if len(struct_entry["field names"]) != len(_p["store"]["value"]):
                        err_msg = "Error at line number " + str(p.lineno(1)) + ": Improper Initialization of struct"
                        GLOBAL_ERROR_LIST.append(err_msg)
                        raise SyntaxError
                    # raise Exception  # Imroper Initialization of Struct
                    for i in range(len(_p["store"]["value"])):
                        # print(_p["store"]["value"][i])
                        _tcast = struct_entry["field types"][i]
                        if len(_p["store"]["value"][i]["code"]) > 0:
                            _tcast = type_cast2(
                                _p["store"]["value"][i],
                                {
                                    "type": struct_entry["field types"][i],
                                    "pointer_lvl": _p.get("pointer_lvl", 0),
                                },
                            )
                            expr = _get_conversion_function_expr(
                                _p["store"]["value"][i],
                                {
                                    "type": struct_entry["field types"][i],
                                    "pointer_lvl": _p.get("pointer_lvl", 0),
                                },
                            )
                            if len(expr["code"]) > 0:
                                p[0]["code"] += expr["code"]
                        else:
                            _tcast = type_cast2(
                                _p["store"]["value"][i],
                                {
                                    "type": struct_entry["field types"][i],
                                    "pointer_lvl": _p.get("pointer_lvl", 0),
                                },
                            )
                            expr = _get_conversion_function(
                                _p["store"]["value"][i],
                                {
                                    "type": struct_entry["field types"][i],
                                    "pointer_lvl": _p.get("pointer_lvl", 0),
                                },
                            )
                            if len(expr["code"]) > 0:
                                p[0]["code"] += expr["code"]
                        vname = get_tmp_var()
                        __t = get_flookup_type(_tcast)
                        p[0]["code"] += [
                            [
                                "FUNCTION CALL",
                                tinfo,
                                f"__store({__t}*,{__t})",
                                [
                                    {"value": _p["value"], "type": tinfo},
                                    {"value": expr["value"], "type": tinfo},
                                ],
                                vname,
                            ]
                        ]
                    # print(p[0])
                else:
                    # For array initialization
                    # Added support for multidimensional array initialization
                    dim = []
                    # print(_p)
                    for d in _p["dimensions"]:
                        if d == "variable":
                            dim.append("variable")
                        else:
                            dim.append(int(d["value"]))
                    _array_init(
                        p,
                        _p["store"]["value"],
                        _p["store"]["types"],
                        dim,
                        _p,
                        [],
                    )
                    # raise Exception
                    # p[0]["value"] = vname

            if is_static:
                global SYMBOL_TABLES, STATIC_VARIABLE_MAPS
                valid, entry = SYMBOL_TABLES[0].insert(
                    {
                        "name": _p["value"] + ".static." + LAST_FUNCTION_DECLARATION,
                        "type": tinfo,
                        "is_array": _p.get("is_array", False),
                        "dimensions": _p.get("dimensions", []),
                        "pointer_lvl": _p.get("pointer_lvl", 0),
                    },
                    kind=0,
                )
                STATIC_VARIABLE_MAPS[(_p["value"], LAST_FUNCTION_DECLARATION)] = entry["name"]

            else:
                if tinfo == "void":
                    err_msg = "Error at line number " + str(p.lineno(2)) + ": Incomplete type is not allowed"
                    GLOBAL_ERROR_LIST.append(err_msg)
                    raise SyntaxError
                    # raise Exception("Incomplete type is not allowed")
                # print(_p)
                valid, entry = symTab.insert(
                    {
                        "name": _p["value"],
                        "type": tinfo,
                        "is_array": _p.get("is_array", False),
                        "dimensions": _p.get("dimensions", []),
                        "pointer_lvl": _p.get("pointer_lvl", 0),
                    },
                    kind=0,
                    fname=LAST_FUNCTION_DECLARATION,
                )
            if not valid:
                # print(f"Error at {_p}")
                err_msg = (
                    "Error at line number "
                    + str(p.lineno(2))
                    + ": "
                    + f"Variable {_p['value']} already declared with type {entry['type']}"
                )
                GLOBAL_ERROR_LIST.append(err_msg)
                raise SyntaxError
                # raise Exception(f"Variable {_p['value']} already declared with type {entry['type']}")


def p_declaration_specifiers(p):
    """declaration_specifiers : storage_class_specifier
    | storage_class_specifier declaration_specifiers
    | type_specifier
    | type_specifier declaration_specifiers
    | type_qualifier
    | type_qualifier declaration_specifiers"""
    if len(p) == 2:
        # print(f"Declaration Specifier {p[1]}")
        p[0] = p[1]
    else:
        # print(f"Declaration Specifier {p[1]} {p[2]}")
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
        if "types" in p[3]:
            p[0] = {
                "value": p[1]["value"],
                "code": p[3]["code"],
                "store": {"value": p[3]["value"], "types": p[3]["types"]},
                "is_array": p[1].get("is_array", False),
                "dimensions": p[1].get("dimensions", []),
                "pointer_lvl": p[1].get("pointer_lvl", 0),
            }
        else:
            p[0] = {
                "value": p[1]["value"],
                "code": p[3]["code"],
                "store": {
                    "value": p[3]["value"],
                    "type": p[3]["type"],
                    "code": [],
                    "pointer_lvl": p[3].get("pointer_lvl", 0),
                },
                "is_array": p[1].get("is_array", False),
                "dimensions": p[1].get("dimensions", []),
                "pointer_lvl": p[1].get("pointer_lvl", 0),
            }
        # p[0] = ("init_declarator",) + tuple(p[-len(p) + 1 :])


def p_storage_class_specifier(p):
    """storage_class_specifier : TYPEDEF
    | EXTERN
    | STATIC
    | AUTO
    | REGISTER"""
    p[0] = {"value": p[1], "code": []}


def p_type_specifier(p):
    """type_specifier : VOID
    | CHAR
    | SHORT
    | INT
    | LONG
    | FLOAT
    | DOUBLE
    | SIGNED
    | UNSIGNED"""
    # p[0] = ("type_specifier",) + tuple(p[-len(p) + 1 :])

    # Check if it is a valid type
    symTab = get_current_symtab()
    if not symTab.check_type(p[1]):
        err_msg = "Error at line number " + str(p.lineno(1)) + ": " + f"{p[1]} is not a valid type"
        GLOBAL_ERROR_LIST.append(err_msg)
        raise SyntaxError
        # raise Exception(f"{p[1]} is not a valid type")
    p[0] = {"value": p[1], "code": []}


def p_type_specifier_custom_types(p):
    """type_specifier : struct_or_union_specifier
    | class_definition
    | enum_specifier
    | TYPE_NAME"""
    # print(p[1])
    symTab = get_current_symtab()
    if p[1]["kind"] == 2:
        if p[1]["insert"]:
            symTab.insert(
                {
                    "name": p[1]["name"],
                    "alt name": p[1]["alt_name"],
                    "field names": p[1]["field names"],
                    "field types": p[1]["field types"],
                    "field values": p[1]["field values"],
                },
                kind=2,
            )
        else:
            if not symTab.check_type("struct " + p[1]["name"]):
                err_msg = (
                    "Error at line number " + str(p.lineno(1)) + ": " + f"struct {p[1]['name']} is not a valid type"
                )
                GLOBAL_ERROR_LIST.append(err_msg)
                raise SyntaxError
                # raise Exception(f"struct {p[1]['name']} is not a valid type")
        p[0] = {"value": "struct " + p[1]["name"], "code": []}

    elif p[1]["kind"] == 5:
        if p[1]["insert"]:
            symTab.insert(
                {
                    "name": p[1]["name"],
                    "alt name": p[1]["alt_name"],
                    "field names": p[1]["field names"],
                    "field types": p[1]["field types"],
                    "field values": p[1]["field values"],
                },
                kind=5,
            )
        else:
            if not symTab.check_type("union " + p[1]["name"]):
                err_msg = (
                    "Error at line number " + str(p.lineno(1)) + ": " + f"union {p[1]['name']} is not a valid type"
                )
                GLOBAL_ERROR_LIST.append(err_msg)
                raise SyntaxError
                # raise Exception(f"union {p[1]['name']} is not a valid type")
        p[0] = {"value": "union " + p[1]["name"], "code": []}

    elif p[1]["kind"] == 4:
        if p[1]["insert"]:
            symTab.insert(
                {
                    "name": p[1]["value"].split(" ")[-1],
                    "field names": p[1]["fnames"],
                    "field values": p[1]["fvalues"],
                },
                kind=4,
            )
        else:
            if not symTab.check_type(p[1]["value"]):
                err_msg = "Error at line number " + str(p.lineno(1)) + ": " + f"{p[1]['value']} is not a valid type"
                GLOBAL_ERROR_LIST.append(err_msg)
                raise SyntaxError
                # raise Exception(f"{p[1]['value']} is not a valid type")
        p[0] = {"value": p[1]["value"], "code": []}
    else:
        err_msg = "Error at line number " + str(p.lineno(1)) + ": Unsupported Custom Type"
        GLOBAL_ERROR_LIST.append(err_msg)
        raise SyntaxError
        # raise Exception("Unsupported Custom Type")


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
    p[0] = p[1]


def p_class(p):
    """class : CLASS"""
    p[0] = p[1]


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
    if len(p) in [5, 6]:
        if p[1] == "struct":
            p[0] = {
                "name": p[2] if len(p) == 6 else get_tmp_var(),
                "alt_name": None,
                "field names": p[len(p) - 2]["field names"],
                "field types": p[len(p) - 2]["field types"],
                "field values": p[len(p) - 2]["field values"],
                "kind": 2,
                "insert": True,
                "code": [],
            }
        else:
            p[0] = {
                "name": p[2] if len(p) == 6 else get_tmp_var(),
                "alt_name": None,
                "field names": p[len(p) - 2]["field names"],
                "field types": p[len(p) - 2]["field types"],
                "field values": p[len(p) - 2]["field values"],
                "kind": 5,
                "insert": True,
                "code": [],
            }
    else:
        symTab = get_current_symtab()
        struct_union_entry = symTab.lookup_type(p[1] + " " + p[2])
        if struct_union_entry is None:
            err_msg = "Error at line number " + str(p.lineno(1)) + ": Undeclared Struct Used"
            GLOBAL_ERROR_LIST.append(err_msg)
            raise SyntaxError
            # raise Exception  # undeclared struct used
        else:
            p[0] = {
                "name": p[2],
                "kind": 2 if p[1] == "struct" else 5,
                "insert": False,
                "code": [],
            }
    # p[0] = ("struct_or_union_specifier",) + tuple(p[-len(p) + 1 :])


def p_struct_or_union(p):
    """struct_or_union : STRUCT
    | UNION"""
    p[0] = p[1]
    # p[0] = ("struct_or_union",) + tuple(p[-len(p) + 1 :])


def p_struct_declaration_list(p):
    """struct_declaration_list : struct_declaration
    | struct_declaration_list struct_declaration"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        variables = p[1]["field names"] + p[2]["field names"]
        types = p[1]["field types"] + p[2]["field types"]
        values = p[1]["field values"] + p[2]["field values"]
        p[0] = {
            "field names": variables,
            "field types": types,
            "field values": values,
        }
    # p[0] = ("struct_declaration_list",) + tuple(p[-len(p) + 1 :])


def p_struct_declaration(p):
    """struct_declaration : specifier_qualifier_list struct_declarator_list SEMICOLON"""
    variables = [var["value"] for var in p[2]]
    types = [p[1]["value"] + "*" * _a.get("pointer_lvl", 0) for _a in p[2]]
    values = [get_default_value(p[1]["value"])] * len(variables)
    p[0] = {
        "field names": variables,
        "field types": types,
        "field values": values,
    }
    # p[0] = ("struct_declaration",) + tuple(p[-len(p) + 1 :])


def p_specifier_qualifier_list(p):
    """specifier_qualifier_list : type_specifier specifier_qualifier_list
    | type_specifier
    | type_qualifier specifier_qualifier_list
    | type_qualifier"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        # print("2", p[1], p[2])
        p[0] = {"value": p[1]["value"] + " " + p[2]["value"], "code": []}
    # p[0] = ("specifier_qualifier_list",) + tuple(p[-len(p) + 1 :])


def p_struct_declarator_list(p):
    """struct_declarator_list : struct_declarator
    | struct_declarator_list COMMA struct_declarator"""
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]
        # p[0] = ("struct_declarator_list",) + tuple(p[-len(p) + 1 :])


def p_struct_declarator(p):
    """struct_declarator : declarator
    | COLON constant_expression
    | declarator COLON constant_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        # TODO
        p[0] = ("struct_declarator",) + tuple(p[-len(p) + 1 :])


def p_enum_specifier(p):
    """enum_specifier : ENUM LEFT_CURLY_BRACKET enumerator_list RIGHT_CURLY_BRACKET
    | ENUM IDENTIFIER LEFT_CURLY_BRACKET enumerator_list RIGHT_CURLY_BRACKET
    | ENUM IDENTIFIER"""
    if len(p) in [5, 6]:
        name = p[2] if len(p) == 6 else get_tmp_var()
        names, values = [], []
        cval = 0
        for _x in p[4]:
            if isinstance(_x, tuple):
                names.append(_x[0])
                values.append(int(_x[1]["value"]))
                cval = values[-1] + 1
            else:
                names.append(_x)
                values.append(cval)
                cval += 1
        p[0] = {
            "value": f"enum {p[2]}",
            "code": [],
            "fnames": names,
            "fvalues": values,
            "kind": 4,
            "insert": True,
        }
    else:
        p[0] = {
            "value": f"enum {p[2]}",
            "code": [],
            "kind": 4,
            "insert": False,
        }
    # p[0] = ("enum_specifier",) + tuple(p[-len(p) + 1 :])


def p_enumerator_list(p):
    """enumerator_list : enumerator
    | enumerator_list COMMA enumerator"""
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]


def p_enumerator(p):
    """enumerator : IDENTIFIER
    | IDENTIFIER EQ constant_expression"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = (p[1], p[3])


def p_type_qualifier(p):
    """type_qualifier : CONST
    | VOLATILE"""
    p[0] = p[1]


def p_declarator(p):
    """declarator : pointer direct_declarator
    | direct_declarator"""
    if len(p) == 3:
        p[0] = p[2]
        p[0]["pointer_lvl"] = len(p[1])
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
        # print(f"size 4 {p[2]}")
        if p[2] == "(":
            p[0] = {"value": p[1]["value"], "code": [], "parameters": []}
        elif p[2] == "[":
            # TODO
            # print(p[2], p[0])
            # print(f"direct_declarator {p[1]}{p[2]}{p[3]}")
            # p[0] = ("direct_declarator_1.1",) + tuple(p[-len(p) + 1 :])
            p[0] = {
                "code": p[1]["code"],
                "value": p[1]["value"],
                "is_array": True,
                "dimensions": p[1].get("dimensions", []),
            }
            # print(p[0])
            if "variable" not in p[0]["dimensions"]:
                # smth
                p[0]["dimensions"].append("variable")
            else:
                err_msg = "Invalid array declaration"
                # print(err_msg)
                GLOBAL_ERROR_LIST.append(err_msg)
                raise SyntaxError
        else:
            # Rule 5: No parameter function
            p[0] = {"value": p[1]["value"], "code": [], "parameters": []}
    else:
        p[0] = {
            "code": p[1]["code"],
            "value": p[1]["value"],
            "is_array": True,
            "dimensions": p[1].get("dimensions", []),
        }
        if len(p[3]["code"]) > 0:
            # TODO: Type casting might be needed
            p[0]["code"] += p[3]["code"]
        p[0]["dimensions"] += [p[3]["value"] if p[3]["kind"] != "CONSTANT" else p[3]]
        # print(f"direct_declarator {p[0]}")
        # p[0]["text"] = ("direct_declarator_1.2",) + tuple(p[-len(p) + 1 :])


def p_direct_declarator_2(p):
    """direct_declarator : direct_declarator LEFT_BRACKET parameter_type_list RIGHT_BRACKET"""
    # print(p[3])
    global INITIALIZE_PARAMETERS_IN_NEW_SCOPE
    p[0] = {
        "value": p[1]["value"],
        "code": [],
        "parameters": [(get_flookup_type(_p), _p["value"]) for _p in p[3]],
    }
    INITIALIZE_PARAMETERS_IN_NEW_SCOPE = p[0]["parameters"]


def p_direct_declarator_3(p):
    """direct_declarator : direct_declarator LEFT_BRACKET identifier_list RIGHT_BRACKET"""
    p[0] = ("direct_declarator_3",) + tuple(p[-len(p) + 1 :])


def p_pointer(p):
    """pointer : MULTIPLY
    | MULTIPLY type_qualifier_list
    | MULTIPLY pointer
    | MULTIPLY type_qualifier_list pointer"""
    if len(p) == 3:
        p[0] = p[2] + p[1]
    else:
        p[0] = p[1]


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

    p[0] = p[2]
    p[0]["type"] = p[1]["value"]


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
    # p[0] = ("type_name",) + tuple(p[-len(p) + 1 :])
    if len(p) == 2:
        p[0] = p[1]

    else:
        # TODO : should have a value field
        p[0] = {"value": p[1]["value"] + p[2], "code": []}
        pass


def p_abstract_declarator(p):
    """abstract_declarator : pointer
    | direct_abstract_declarator
    | pointer direct_abstract_declarator"""
    # p[0] = ("abstract_declarator",) + tuple(p[-len(p) + 1 :])
    if len(p) == 2:
        p[0] = p[1]
    else:
        # TODO
        pass


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
        p[0] = {"code": [], "value": [], "types": []}
        for _p in p[2]:
            if len(_p["code"]) > 0:
                p[0]["code"] += _p["code"]
            if "type" not in _p:
                p[0]["value"].append(_p["value"])
                p[0]["types"].append(_p["types"])
            else:
                p[0]["value"].append(_p["value"] if _p["kind"] != "CONSTANT" else _p)
                p[0]["types"].append(_p["type"])
        p[0]["is_array"] = True
        # if all(map(lambda x: x == p[0]["types"][0], p[0]["types"])):
        #     p[0]["type"] = p[0]["types"][0]
        # else:
        #     # FIXME: Type inference by casting maybe?
        #     p[0]["type"] = "all"
        # p[0] = ("initializer",) + tuple(p[-len(p) + 1 :])


def p_initializer_list(p):
    """initializer_list : initializer
    | initializer_list COMMA initializer"""
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]
    # p[0] = ("initializer_list",) + tuple(p[-len(p) + 1 :])


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
    symTab = get_current_symtab()
    if len(p) == 4:
        if p[1] == "default":
            p[0] = {"code": [["DEFAULT"]] + p[3]["code"]}
        else:
            valid, entry = symTab.insert({"name": p[1]}, kind=6)
            p[0] = {"code": [[p[1] + ":"]] + p[3]["code"]}
    else:
        p[0] = {"code": p[2]["code"] + [["CASE", p[2]["value"]]] + p[4]["code"]}
    # p[0] = ("labeled_statement",) + tuple(p[-len(p) + 1 :])


def p_compound_statement_1(p):
    """compound_statement : lbrace rbrace
    | lbrace statement_list rbrace
    | lbrace declaration_list statement_list rbrace"""
    if len(p) == 3:
        p[0] = {"code": []}
    elif len(p) == 4:
        p[0] = p[2]
    else:
        p[0] = p[3]
        if len(p[2]["code"]) > 0:
            p[0]["code"] = p[2]["code"] + p[3]["code"]
    p[0]["code"] = [["SYMTAB", "PUSH", p[len(p) - 1]["popped_table"].table_name]] + p[0]["code"] + [["SYMTAB", "POP"]]


def p_compound_statement_2(p):
    """compound_statement : lbrace declaration_list rbrace"""
    # p[0] = ("compound_statement",) + tuple(p[-len(p) + 1 :])
    p[0] = p[2]
    p[0]["code"] = [["SYMTAB", "PUSH", p[len(p) - 1]["popped_table"].table_name]] + p[0]["code"] + [["SYMTAB", "POP"]]


def p_compound_statement_3(p):
    """compound_statement : ASSEMBLY_DIRECTIVE STRING_LITERAL"""
    p[0] = {"code": [["ASSEMBLY_DIRECTIVE", p[2]]]}


def p_declaration_list(p):
    """declaration_list : declaration
    | declaration_list declaration"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[2]
        p[0]["code"] = p[1]["code"] + p[2]["code"]
    # p[0] = ("declaration_list",) + tuple(p[-len(p) + 1 :])


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
        if p[3]["value"] is not None:
            expr = _get_conversion_function_expr(p[3], {"type": "int", "pointer_lvl": 0})
            if len(expr["code"]) > 0:
                p[0]["code"] += expr["code"]
            else:
                p[0]["code"] += p[3]["code"]
            p[0]["code"] += [["IF", expr["value"], "==", "0", "GOTO", elseLabel]]
        if len(p[5]["code"]) > 0:
            p[0]["code"] += p[5]["code"]
        if len(p) == 6:
            p[0]["code"] += [[elseLabel + ":"]]
        else:
            finishLabel = get_tmp_label()
            p[0]["code"] += [["GOTO", finishLabel], [elseLabel + ":"]]
            if len(p[7]["code"]) > 0:
                p[0]["code"] += p[7]["code"]
            else:
                p[0]["code"] += p[7]["code"]
            p[0]["code"] += [[finishLabel + ":"]]
    else:
        # p[0] = ("selection_statement",) + tuple(p[-len(p) + 1 :])
        if p[3]["type"] not in INTEGER_TYPES:
            err_msg = (
                "Error at line number "
                + str(p.lineno(1))
                + ": "
                + f"Switch Expression must have integral type. Current Type: {p[3]['type']}"
            )
            GLOBAL_ERROR_LIST.append(err_msg)
            raise SyntaxError
        p[0] = {"code": p[3]["code"] + [["BEGINSWITCH", p[3]["value"]]] + p[5]["code"] + [["ENDSWITCH"]]}


def p_iteration_statement(p):
    """iteration_statement : WHILE LEFT_BRACKET expression RIGHT_BRACKET statement
    | DO statement WHILE LEFT_BRACKET expression RIGHT_BRACKET SEMICOLON
    | FOR LEFT_BRACKET expression_statement expression_statement RIGHT_BRACKET statement
    | FOR LEFT_BRACKET expression_statement expression_statement expression RIGHT_BRACKET statement"""
    beginLabel = get_tmp_label()
    endLabel = get_tmp_label()
    code = [["LOOPBEGIN", beginLabel, endLabel]]
    if p[1] == "while":
        code += [[beginLabel + ":"]]
        if p[3]["value"] != "":
            expr = _get_conversion_function_expr(p[3], {"type": "int", "pointer_lvl": 0})
            if len(expr["code"]) > 0:
                code += expr["code"]
            else:
                code += p[3]["code"]
            code += [["IF", expr["value"], "==", "0", "GOTO", endLabel]]
        if len(p[5]["code"]) > 0:
            code += p[5]["code"]

    elif p[1] == "do":
        code += [[beginLabel + ":"]]
        if len(p[2]["code"]) > 0:
            code += p[2]["code"]
        if p[5]["value"] != "":
            expr = _get_conversion_function_expr(p[5], {"type": "int", "pointer_lvl": 0})
            if len(expr["code"]) > 0:
                code += expr["code"]
            else:
                code += p[5]["code"]
            code += [["IF", expr["value"], "==", "0", "GOTO", endLabel]]

    elif p[1] == "for":
        if len(p[3]["code"]) > 0:
            code += p[3]["code"]
        code += [[beginLabel + ":"]]
        if p[4]["value"] != "":
            expr = _get_conversion_function_expr(p[4], {"type": "int", "pointer_lvl": 0})
            if len(expr["code"]) > 0:
                code += expr["code"]
            else:
                code += p[4]["code"]
            code += [["IF", expr["value"], "==", "0", "GOTO", endLabel]]
        if len(p[len(p) - 1]["code"]) > 0:
            code += p[len(p) - 1]["code"]
        if len(p) == 8 and len(p[5]["code"]) > 0:
            code += p[5]["code"]

    # p[0] = ("iteration_statement",) + tuple(p[-len(p) + 1 :])

    code += [["GOTO", beginLabel], [endLabel + ":"], ["ENDLOOP"]]
    p[0] = {"code": code}


def p_jump_statement(p):
    """jump_statement : GOTO IDENTIFIER SEMICOLON
    | CONTINUE SEMICOLON
    | BREAK SEMICOLON
    | RETURN SEMICOLON
    | RETURN expression SEMICOLON"""
    p[0] = {"code": []}
    symTab = get_current_symtab()
    if p[1] == "goto":
        if symTab.lookup(p[2]["value"]) is None:
            err_msg = "Error at line number " + str(p.lineno(2)) + ": Label not present"
            GLOBAL_ERROR_LIST.append(err_msg)
            raise SyntaxError
            # raise Exception("Label not present")
        p[0]["code"] += [["GOTO", p[2]["value"]]]
    elif p[1] == "continue":
        p[0]["code"] += [["CONTINUE"]]
    elif p[1] == "break":
        p[0]["code"] += [["BREAK"]]
    elif p[1] == "return":
        # Return type matching done in p_function_definition
        if len(p) == 3:
            p[0]["code"] += [["RETURN"]]
        else:
            p[0]["code"] += p[2]["code"]
            p[2]["code"] = []
            p[0]["code"] += [["RETURN", p[2]]]


def p_translation_unit(p):
    """translation_unit : external_declaration
    | translation_unit external_declaration"""
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[2]]


def p_external_declaration(p):
    """external_declaration : function_definition
    | declaration"""
    p[0] = p[1]
    # p[0] = ("external_declaration",) + tuple(p[-len(p) + 1 :])


NEW_FUNCTION_INCOMING = False


def p_function_definition_full(p):
    """function_definition_full : declaration_specifiers declarator"""
    symTab = get_current_symtab()
    global LAST_FUNCTION_DECLARATION
    global NEW_FUNCTION_INCOMING
    NEW_FUNCTION_INCOMING = True
    # TODO: Again arrays as parameters wont work for now
    #       Recursive functions wont work for now
    valid, entry = symTab.insert(
        {
            "name": p[2]["value"],
            "return type": p[1]["value"],
            "parameter types": [_p[0] for _p in p[2]["parameters"]],
        },
        kind=1,
    )
    if not valid:
        err_msg = "Error at line number " + str(p.lineno(2)) + f": Failed to create function named {p[2]['value']}"
        GLOBAL_ERROR_LIST.append(err_msg)
        raise SyntaxError
        # raise Exception(f"Failed to create function named {p[2]['value']}")
    p[0] = {"code": [], "value": ""}
    p[0]["code"] = [["BEGINFUNCTION", entry["return type"], entry["name resolution"]]]
    p[0]["value"] = p[1]["value"]
    LAST_FUNCTION_DECLARATION = entry["name resolution"]


def p_function_definition(p):
    """function_definition : declaration_specifiers declarator declaration_list compound_statement
    | function_definition_full compound_statement
    | declarator declaration_list compound_statement
    | declarator compound_statement"""
    global LAST_FUNCTION_DECLARATION
    symTab = get_current_symtab()
    if len(p) == 3:
        p[0] = p[1]
        p[0]["code"] += p[2]["code"] + [["ENDFUNCTION"]]

        no_return = True
        ignorecheck = False
        for code in p[2]["code"]:
            # print(code, ignorecheck, p[1]["value"])
            if len(code) > 0 and code[0] == "BEGINFUNCTION":
                ignorecheck = True
            elif len(code) > 0 and code[0] == "ENDFUNCTION":
                ignorecheck = False
            elif len(code) > 0 and code[0] == "RETURN" and not ignorecheck:
                if len(code) == 1 and p[1]["value"] != "void":
                    err_msg = "Error at line number " + str(p.lineno(1)) + ": Return type not matching declared type"
                    GLOBAL_ERROR_LIST.append(err_msg)
                    raise SyntaxError
                    # raise Exception("Return type not matching declared type")
                elif (
                    len(code) > 1
                    and p[1]["value"] != code[1]["type"]
                    and not (p[1]["value"] == "int" and code[1]["type"].startswith("enum"))
                ):
                    err_msg = "Error at line number " + str(p.lineno(1)) + ": Return type not matching declared type"
                    GLOBAL_ERROR_LIST.append(err_msg)
                    raise SyntaxError
                    # raise Exception("Return type not matching declared type")
                no_return = False
        if no_return and p[1]["value"] != "void":
            err_msg = "Error at line number " + str(p.lineno(1)) + ": Return type not matching declared type"
            GLOBAL_ERROR_LIST.append(err_msg)
            raise SyntaxError
            # raise Exception("Return type not matching declared type")
        LAST_FUNCTION_DECLARATION = None
    else:
        # TODO
        p[0] = ("function_definition",) + tuple(p[-len(p) + 1 :])


def p_lbrace(p):
    """lbrace : LEFT_CURLY_BRACKET"""
    # TODO: Handling insert for arrays in parameters
    global NEW_FUNCTION_INCOMING, LAST_FUNCTION_DECLARATION
    push_scope(
        new_scope(
            get_current_symtab(),
            LAST_FUNCTION_DECLARATION if NEW_FUNCTION_INCOMING else None,
        )
    )
    symTab = get_current_symtab()
    global INITIALIZE_PARAMETERS_IN_NEW_SCOPE
    if not INITIALIZE_PARAMETERS_IN_NEW_SCOPE is None:
        for param in INITIALIZE_PARAMETERS_IN_NEW_SCOPE:
            entry = get_type_fields(param[0])

            entry["name"] = param[1]
            entry["is_parameter"] = True
            # print(entry)
            symTab.insert(entry, param=True)
        INITIALIZE_PARAMETERS_IN_NEW_SCOPE = None
    # p[0] = ("lbrace",) + tuple(p[-len(p) + 1 :])


def p_rbrace(p):
    """rbrace : RIGHT_CURLY_BRACKET"""
    global LAST_POPPED_TABLE
    # p[0] = ("rbrace",) + tuple(p[-len(p) + 1 :])
    s = pop_scope()
    p[0] = {"popped_table": s}
    LAST_POPPED_TABLE = s


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
    codes = get_stdlib_codes()

    # Some of the binary operators
    for op in ("+", "-", "/", "*"):
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

    for op in ("&&", "||", "&", "|"):
        for _type in NUMERIC_TYPES:
            _type = _type.lower()
            table.insert(
                {
                    "name": op,
                    "return type": "int",  # essentially boolean
                    "parameter types": [_type, _type],
                },
                1,
            )

    for op in "^":
        for _type in INTEGER_TYPES:
            _type = _type.lower()
            table.insert(
                {
                    "name": op,
                    "return type": "int",  # essentially boolean
                    "parameter types": [_type, _type],
                },
                1,
            )

    for op in "!":
        for _type in BASIC_TYPES:
            _type = _type.lower()
            table.insert(
                {
                    "name": op,
                    "return type": "int",
                    "parameter types": [_type],
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

    # for getting array elements from basic types
    for _type in BASIC_TYPES:
        _type = _type.lower()
        table.insert(
            {
                "name": "__get_array_element",
                "return type": _type,
                "parameter types": [f"{_type}*", "int"],
            },
            1,
        )

    # for & (reference)
    for _type in BASIC_TYPES:
        _type = _type.lower()
        table.insert(
            {
                "name": "__ref",
                "return type": f"{_type}*",
                "parameter types": [f"{_type}"],
            },
            1,
        )

    # for * (de-reference)
    for _type in BASIC_TYPES:
        _type = _type.lower()
        table.insert(
            {
                "name": "__deref",
                "return type": f"{_type}",
                "parameter types": [f"{_type}*"],
            },
            1,
        )

    # # for unary operators on pointers
    # for _type in BASIC_TYPES:
    #     _type = _type.lower()
    #     table.insert(
    #         {
    #             "name": "__get_array_element",
    #             "return type": _type,
    #             "parameter types": [f"{_type}*", "int"],
    #         },
    #         1,
    #     )

    # For unary operators + and - (for p_cast)
    for op in ("+", "-"):
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

    # TODO: Add the convert functions


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, default=None, help="Input file")
    parser.add_argument("-O", "--optimize", action="store_true", help="Optimize")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print IR")
    parser.add_argument("--no-assembly", action="store_true", help="Don't Generate Assembly Code")
    parser.add_argument("-o", "--output", type=str, default="AST", help="Output file")
    parser.add_argument("--no-dump", action="store_true", help="Run MIPS Generator but don't print the output")
    return parser


def preprocessor(lines):
    new_lines = []
    for line in lines:
        if "@include" in line:
            expanded_lines = preprocessor(open(line.split(" ")[-1][1:-2], "r").readlines())
            new_lines += expanded_lines
        else:
            new_lines += [line]
    return new_lines


if __name__ == "__main__":
    args = get_args().parse_args()
    if args.input == None:
        print("No input file specified")
    else:
        data = "".join(preprocessor(open(args.input)))

        push_scope(new_scope(get_current_symtab()))
        populate_global_symbol_table()

        tree = yacc.parse(data, tracking=True)

        gtab = pop_scope()

        if args.output[-4:] == ".dot":
            args.output = args.output[:-4]

        for err in GLOBAL_ERROR_LIST:
            print(err)

        if len(GLOBAL_ERROR_LIST) > 0:
            raise Exception("Compilation Errors detected. Fix before proceeding")

        code = parse_code(tree, args.output, args.optimize, args.verbose)
        if not args.no_assembly:
            generate_mips_from_3ac(code, args.no_dump)
