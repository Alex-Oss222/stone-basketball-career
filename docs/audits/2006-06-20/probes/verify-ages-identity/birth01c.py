exec(open('birth01.py').read().split("print('records'")[0])
for r in recs:
    if r['birth'] in ('1984-03-26','1981-09-10') : print(r)
