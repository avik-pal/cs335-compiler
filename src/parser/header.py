import sys
import os
import lex
import ply.yacc as yacc
import argparse

from dot import generate_graph_from_ast, reduce_ast

