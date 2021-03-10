header = open("header.py","r").readlines()
main = open("main.py","r").readlines()
lines = open("./c_yacc.y", "r").readlines()

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
    for line in header:
        file.write(line)
    file.write("\n")
    for rules in all_prod_rules:
        rules = list(map(lambda x: x.replace("\t", "   "), rules))
        rules[1] = rules[1][3:]
        name = rules[0].split()[0]
        comb = " ".join(rules[1:-1])
        comb = comb[:-1]
        file.write(f"def p_{name}(p):\n")
        file.write(f'    """{name} {comb}"""\n')
        file.write(f'    p[0] = ("{name}",) + tuple(p[-len(p)+1:])\n\n')
    for line in main:
        file.write(line)
