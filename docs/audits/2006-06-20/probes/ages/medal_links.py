import sys; sys.path.insert(0,'/home/user/stone-basketball-career')
from runtime import national_medals as nm
L=nm.links(on='2006-06-20')
print(L.keys())
for k,v in L['linked'].items():
    print(k, v.get('bbr_id'), v.get('linked_on'), v.get('basis'))
print('ambiguous', L['ambiguous'])
print(nm.medals_for(bbr_id='garcifr01', on='2006-06-20'))
