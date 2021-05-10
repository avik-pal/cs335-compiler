import sys
import ply.lex as lex

reserved = (
    "AUTO",
    "BREAK",
    "CASE",
    "CHAR",
    "CONST",
    "CONTINUE",
    "DEFAULT",
    "DO",
    "DOUBLE",
    "ELSE",
    "ENUM",
    "EXTERN",
    "FLOAT",
    "FOR",
    "GOTO",
    "IF",
    "INT",
    "LONG",
    "REGISTER",
    "RETURN",
    "SHORT",
    "SIGNED",
    "SIZEOF",
    "STATIC",
    "STRUCT",
    "SWITCH",
    "TYPEDEF",
    "UNION",
    "UNSIGNED",
    "VOID",
    "VOLATILE",
    "WHILE",
    "CLASS",
    "PRIVATE",
    "PUBLIC",
    "PROTECTED",
    "ASSEMBLY_DIRECTIVE"
)

tokens = reserved + (
    "IDENTIFIER",
    "TYPE_NAME",
    "I_CONSTANT",
    "F_CONSTANT",
    "C_CONSTANT",
    "STRING_LITERAL",
    "ELLIPSIS",
    "RIGHT_ASSIGN",
    "LEFT_ASSIGN",
    "ADD_ASSIGN",
    "SUB_ASSIGN",
    "MUL_ASSIGN",
    "DIV_ASSIGN",
    "MOD_ASSIGN",
    "AND_ASSIGN",
    "XOR_ASSIGN",
    "OR_ASSIGN",
    "RIGHT_OP",
    "LEFT_OP",
    "INC_OP",
    "DEC_OP",
    "INHERITANCE_OP",
    "PTR_OP",
    "AND_OP",
    "OR_OP",
    "LE_OP",
    "GE_OP",
    "EQ_OP",
    "NE_OP",
    "SEMICOLON",
    "LEFT_CURLY_BRACKET",
    "RIGHT_CURLY_BRACKET",
    "COMMA",
    "COLON",
    "EQ",
    "LEFT_BRACKET",
    "RIGHT_BRACKET",
    "LEFT_THIRD_BRACKET",
    "RIGHT_THIRD_BRACKET",
    "DOT",
    "LOGICAL_AND",
    "NOT",
    "LOGICAL_NOT",
    "MINUS",
    "PLUS",
    "MULTIPLY",
    "DIVIDE",
    "MOD",
    "LESS",
    "GREATER",
    "EXPONENT",
    "LOGICAL_OR",
    "QUESTION",
)

disallowed_identifiers = {r.lower(): r for r in reserved}
disallowed_identifiers["__asm_direc"] = "ASSEMBLY_DIRECTIVE"

t_I_CONSTANT = r"\d+([uU]|[lL]|[uU][lL]|[lL][uU])?"
t_F_CONSTANT = r"((\d+)(\.\d+)(e(\+|-)?(\d+))? | (\d+)e(\+|-)?(\d+))([lL]|[fF])?"
t_STRING_LITERAL = r"\"([^\\\n]|(\\.))*?\""
t_C_CONSTANT = r"(L)?\'([^\\\n]|(\\.))*?\'"

t_ELLIPSIS = r"\.\.\."
t_RIGHT_ASSIGN = r">>="
t_LEFT_ASSIGN = r"<<="
t_ADD_ASSIGN = r"\+="
t_SUB_ASSIGN = r"-="
t_MUL_ASSIGN = r"\*="
t_DIV_ASSIGN = r"/="
t_MOD_ASSIGN = r"%="
t_AND_ASSIGN = r"&="
t_XOR_ASSIGN = r"^="
t_OR_ASSIGN = r"\|="
t_RIGHT_OP = r">>"
t_LEFT_OP = r"<<"
t_INC_OP = r"\+\+"
t_DEC_OP = r"--"
t_INHERITANCE_OP = r"<-"
t_PTR_OP = r"->"
t_AND_OP = r"&&"
t_OR_OP = r"\|\|"
t_LE_OP = r"<="
t_GE_OP = r">="
t_EQ_OP = r"=="
t_NE_OP = r"!="
t_SEMICOLON = r";"
t_LEFT_CURLY_BRACKET = r"({|<%)"
t_RIGHT_CURLY_BRACKET = r"(}|%>)"
t_COMMA = r","
t_COLON = r":"
t_EQ = r"="
t_LEFT_BRACKET = r"\("
t_RIGHT_BRACKET = r"\)"
t_LEFT_THIRD_BRACKET = r"(\[|<:)"
t_RIGHT_THIRD_BRACKET = r"(\]|:>)"
t_DOT = r"\."
t_LOGICAL_AND = r"&"
t_NOT = r"!"
t_LOGICAL_NOT = r"~"
t_MINUS = r"-"
t_PLUS = r"\+"
t_MULTIPLY = r"\*"
t_DIVIDE = r"/"
t_MOD = r"%"
t_LESS = r"<"
t_GREATER = r">"
t_EXPONENT = r"\^"
t_LOGICAL_OR = r"\|"
t_QUESTION = r"\?"

TYPE_NAMES = []


def t_IDENTIFIER(t):
    r"[A-Za-z_][\w_]*"
    global EXPECTED_TYPENAMES
    t.type = disallowed_identifiers.get(t.value, "IDENTIFIER")
    if t.type == "IDENTIFIER":
        if t.value in TYPE_NAMES:
            t.type = "TYPE_NAME"
    return t


def t_NEWLINE(t):
    r"\n+"
    t.lexer.lineno += t.value.count("\n")


def t_comment(t):
    r"/\*(.|\n)*?\*/ | //(.)*?\n"
    t.lexer.lineno += t.value.count("\n")


def t_preprocessor(t):
    r"\#(.)*?\n"
    t.lexer.lineno += 1


# A string containing ignored characters (spaces and tabs)
t_ignore = " \t"

# Error handling rule
def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)


lexer = lex.lex()

if __name__ == "__main__":
    with open(str(sys.argv[1]), "r+") as file:
        data = file.read()
        file.close()
        print("{token type, token name, line nunmber, index relative to start of input}")
        lex.runmain(lexer, data)
