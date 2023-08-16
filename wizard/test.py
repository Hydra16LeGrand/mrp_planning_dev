# section = [2,4, 5, 6, 8]
# product = [1, 3, 7, 9, 10]
#
# print(len(section))
# print(range(len(section)))
# print(range(len(section) - 1))
#
#
# for i in range(len(section) - 1):
#     for p in product:
#         if section[i] < p < section[i+1]:
#             print(f"{section[i]} < {p} < {section[i+1]}")
#         if p > section[-1]:
#             print(f"{p} > {section[-1]}")

test = {'lang': 'fr_FR', 'tz': 'Africa/Abidjan', 'uid': 2, 'allowed_company_ids': [1], 'params': {'cids': 1, 'menu_id': 381, 'action': 657, 'model': 'mrp.planning', 'view_type': 'form', 'id': 9}}

test2 = test.get('params')
print(test2)

print(test2.get('id'))