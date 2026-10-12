import sys, json
sys.path.insert(0, '/home/user/stone-basketball-career')
from pathlib import Path
R = Path('/home/user/stone-basketball-career')
from runtime import league_cards, seasons
seasons.live_season_on = lambda on, root=None: '2003-04'      # reproduce the FIRST_SEASON path used at the 2004-10-01 write
reg = {p['name']: p for p in json.loads((R/'career/Dwyane_Wade/Stats_and_Awards/League/player_registry.json').read_text())['players']}
tx = json.loads((R/league_cards.TRANSACTIONS).read_text())
names = ['Smush Parker','Adam Harrington','Dion Glover','Lavor Postell','Chris Jefferies','Tremaine Fowlkes','Maciej Lampe','Tyrone Hill','Jelani McCoy','Keon Clark','Mikki Moore','Wang Zhizhi','Jamal Sampson','Dan Langhi','DerMarr Johnson','Paul Shirley','Ruben Boumtje-Boumtje','Alton Ford','Randy Livingston','Donyell Marshall']
for n in names:
    c = league_cards.club_on(reg[n], '2004-10-01', root=R)
    print(n, '|', c['code'], '|', c['basis'])
