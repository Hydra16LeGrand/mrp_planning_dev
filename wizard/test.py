section = [2,4, 5, 6, 8]
product = [1, 3, 7, 9, 10]

print(len(section))
print(range(len(section)))
print(range(len(section) - 1))


for i in range(len(section) - 1):
    for p in product:
        if section[i] < p < section[i+1]:
            print(f"{section[i]} < {p} < {section[i+1]}")
        if p > section[-1]:
            print(f"{p} > {section[-1]}")