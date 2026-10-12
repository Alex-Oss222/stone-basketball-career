"""The live card's default period and awards scenario point at 2006-07, a season with no current_state.json."""
import json
from pathlib import Path
C = Path('/home/user/stone-basketball-career/career/Dwyane_Wade')
d = json.loads((C / 'Stats_and_Awards/player_cards_data.json').read_text())
p = next(x for x in d['periods'] if x['id'] == d['default_period'])
print('default_period', d['default_period'], '| label', p['label'], '| games', p['games'], '| start/end', p['start'], p['end'])
print('awards default scenario', d['awards']['default_scenario'])
print('live seasons (have current_state.json):', sorted(x.name for x in C.iterdir() if (x / 'current_state.json').is_file()))
print('2006-07 folder contents:', sorted(x.name for x in (C / '2006-07').iterdir()))
