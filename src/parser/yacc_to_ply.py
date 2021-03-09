lines = open("../lexer/c_yacc.y", "r").readlines()

lines = lines[lines.index("%%\n") + 1 :]
lines = lines[: lines.index("%%\n")]

all_prod_rules = []
prod_rules = []
for line in lines:
    if line == "\n":
        if len(prod_rules) > 0:
            all_prod_rules.append(prod_rules)
        prod_rules = []
        continue
    prod_rules.append(line)

with open("ply_file.py", "w+") as file:
    for rules in all_prod_rules:
        name = rules[0].split()[0]
        comb = (name + " ").join(rules[1:-1])
        file.write(f"def p_{name}(p):\n")
        file.write(f'    """{comb}"""\n')
        file.write(f'    p[0] = ("{name}",) + tuple(p[-len(p)+1:])\n\n')
