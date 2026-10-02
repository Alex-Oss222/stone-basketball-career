#!/usr/bin/env python3
"""Write library/2003/league/nba_2003_offseason_transactions.json: the real 2003 offseason, dated.

World data under option D (AGENTS.md): it fixes when each real free agent left the
market and what his real contract was, so a player simulated Miami does not sign
follows history on that date. Miami's front office never reads a row before its
date. Rows that involved real Miami are flagged `involves_miami` and skipped by
rule 1; they still record the alternatives Miami competed against.

Evidence: V = read in a period source (ESPN 2003, AP, Basketball-Reference);
S = search snippet only (unverified amount); I = inferred. Sources are in
library/2003/league/nba_2003_offseason_market_research.md. Names are resolved
to Basketball-Reference IDs from the rights, careers and roster files; a row
that cannot be resolved is written with `bbr_id` null and listed.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime.player_stats import alias

OUT = ROOT / "library/2003/league/nba_2003_offseason_transactions.json"
MIA = "Miami Heat"
C = {"ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers",
     "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets", "DET": "Detroit Pistons", "GSW": "Golden State Warriors",
     "HOU": "Houston Rockets", "IND": "Indiana Pacers", "LAC": "Los Angeles Clippers", "LAL": "Los Angeles Lakers",
     "MEM": "Memphis Grizzlies", "MIA": MIA, "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves",
     "NJN": "New Jersey Nets", "NOH": "New Orleans Hornets", "NYK": "New York Knicks", "ORL": "Orlando Magic",
     "PHI": "Philadelphia 76ers", "PHO": "Phoenix Suns", "POR": "Portland Trail Blazers", "SAC": "Sacramento Kings",
     "SAS": "San Antonio Spurs", "SEA": "Seattle SuperSonics", "TOR": "Toronto Raptors", "UTA": "Utah Jazz",
     "WAS": "Washington Wizards", None: None}

# (date, kind, player, from, to, years, total, note, evidence, sources)
SIGNINGS = [
    ("2003-07-16", "signing", "Alonzo Mourning", "MIA", "NJN", 4, 22000000, "mid-level sized; July 11 report said $20M", "V", "SB, ZO"),
    ("2003-07-16", "signing", "Juwan Howard", "DEN", "ORL", 5, 28000000, "starts at the full mid-level $4.917M; reports range $28M to $38M", "V", "SB, HOW, HOW2"),
    ("2003-07-16", "signing", "Karl Malone", "UTA", "LAL", 2, 3000000, "$1.5M first year ($1.5M exception)", "V", "SB, MAL"),
    ("2003-07-16", "signing", "Gary Payton", "MIL", "LAL", 2, 10325700, "full mid-level start $4.917M; total per Spotrac snippet", "V/S", "SB, PAY, SPOT"),
    ("2003-07-16", "signing", "Rasho Nesterovic", "MIN", "SAS", 6, 42000000, "$42M (Stein) or $45M (ESPN scoreboard); Minnesota had offered 7 years $50M+", "V", "ST15, SB, ST13"),
    ("2003-07-16", "signing", "Michael Olowokandi", "LAC", "MIN", 3, 16200000, "full mid-level for three years", "V", "SB, AMILL"),
    ("2003-07-16", "re_sign", "Tim Duncan", "SAS", "SAS", 7, 122000000, "early termination option after 2007-08", "V", "DUNC, SB"),
    ("2003-07-16", "re_sign", "Jermaine O'Neal", "IND", "IND", 7, 120000000, "$120M (scoreboard) or $126,588,000 (snippet)", "V/S", "SB, PAC, SHAM"),
    ("2003-07-16", "re_sign", "Kenny Thomas", "PHI", "PHI", 7, 40000000, "restricted; 'over $40M' (scoreboard) or $50,400,500 (snippet)", "V/S", "SB, SHAM"),
    ("2003-07-16", "offer_sheet", "Elton Brand", "LAC", "MIA", 6, 82200000, "Miami offer sheet (Heat side reported $84.2M); matched by the Clippers July 19", "V", "BRAND, MATCH, SB"),
    ("2003-07-19", "match", "Elton Brand", "LAC", "LAC", 6, 82200000, "Clippers matched Miami's sheet", "V", "MATCH"),
    ("2003-07-16", "offer_sheet", "Andre Miller", "LAC", "DEN", 6, 51170000, "plus $4.5M bonuses, $10M signing bonus, $14M up front; Clippers declined; signed August 1", "V", "AMILL, MM, BBR04"),
    ("2003-08-01", "match_declined", "Andre Miller", "LAC", "DEN", 6, 51170000, "Clippers declined to match; registered August 1", "V", "BBR04"),
    ("2003-07-16", "offer_sheet", "Corey Maggette", "LAC", "UTA", 6, 42000000, "$42M ($45M per AP), front-loaded; Clippers matched within 15 days (date not found)", "V", "JAZZ, MATCH, SB"),
    ("2003-07-31", "match", "Corey Maggette", "LAC", "LAC", 6, 42000000, "match date not found; placed at the end of the 15-day window", "I", "MATCH"),
    ("2003-07-16", "signing", "Jerome Moiso", "NOH", "TOR", None, None, "undisclosed", "V", "BBR04"),
    ("2003-07-16", "signing", "Milt Palacio", "CLE", "TOR", None, None, "undisclosed", "V", "BBR04"),
    ("2003-07-16", "signing", "Amal McCaskill", None, "PHI", None, None, "undisclosed", "V", "BBR04"),
    ("2003-07-16", "signing", "Theron Smith", None, "MEM", None, None, "undrafted; undisclosed", "V", "BBR04"),
    ("2003-07-16", "re_sign", "Jason Kidd", "NJN", "NJN", 6, 103670000, "agreed July 11 at $99M, raised to $103.67M by the cap figure (30% maximum, 12.5% raises)", "V", "KIDD, CAP, SB"),
    ("2003-07-17", "signing", "Kevin Ollie", "SEA", "CLE", 5, 15000000, "", "V", "SB, HOW"),
    ("2003-07-17", "signing", "Brian Skinner", "PHI", "MIL", 3, 5000000, "", "V", "SB"),
    ("2003-07-17", "signing", "Erick Strickland", "IND", "MIL", 2, 3100000, "", "V", "SB"),
    ("2003-07-17", "signing", "Daniel Santiago", None, "MIL", None, None, "from Lottomatica Roma; undisclosed", "V", "SB"),
    ("2003-07-17", "signing", "Mengke Bateer", "SAS", "TOR", None, None, "undisclosed", "V", "BBR04"),
    ("2003-07-19", "signing", "Antonio Daniels", "POR", "SEA", 3, 7500000, "multiyear; $7.5M per snippet", "V/S", "DAN, SB"),
    ("2003-07-20", "signing", "Scottie Pippen", "POR", "CHI", 2, 10000000, "mid-level", "V", "SB"),
    ("2003-07-21", "signing", "Sean Rooks", "LAC", "NOH", 1, None, "one year", "V", "SB"),
    ("2003-07-21", "offer_sheet", "Gilbert Arenas", "GSW", "WAS", 6, 64000000, "$64M to $65M; Golden State could not match (Early Bird rights only); registered August 8", "V", "ARENAS, FRIEND, SB, BBR04"),
    ("2003-08-08", "match_declined", "Gilbert Arenas", "GSW", "WAS", 6, 64000000, "Warriors unable to match; registered August 8", "V", "BBR04"),
    ("2003-07-22", "signing", "Ira Newble", "ATL", "CLE", None, None, "half of the $4.9M mid-level", "V", "SB"),
    ("2003-07-23", "signing", "Speedy Claxton", "SAS", "GSW", 3, 10000000, "about $10M", "V", "SB"),
    ("2003-07-24", "signing", "Robert Horry", "LAL", "SAS", 2, 9450000, "$4.5M first year; Spurs team option on year two", "V", "HORRY, ST28"),
    ("2003-07-24", "signing", "Anthony Johnson", "NJN", "IND", 1, None, "one year", "V", "SB"),
    ("2003-07-24", "sign_and_trade", "Brad Miller", "IND", "SAC", 7, 68000000, "signed by Indiana and traded to Sacramento (three-team trade)", "V", "BMILL"),
    ("2003-07-25", "signing", "Mike James", "MIA", "BOS", None, None, "undisclosed", "V", "BBR04"),
    ("2003-07-26", "signing", "Elden Campbell", "SEA", "DET", 2, 8400000, "about $8.4M", "V", "SB"),
    ("2003-07-26", "signing", "Eric Piatkowski", "LAC", "HOU", 3, 8000000, "", "V", "SB"),
    ("2003-07-28", "signing", "Fred Hoiberg", "CHI", "MIN", 1, None, "one year", "V", "SB"),
    ("2003-07-28", "signing", "Mark Madsen", "LAL", "MIN", None, None, "undisclosed", "V", "SB"),
    ("2003-07-29", "signing", "Darrell Armstrong", "ORL", "NOH", 2, 6000000, "", "V", "SB"),
    ("2003-07-29", "signing", "Horace Grant", "ORL", "LAL", None, None, "undisclosed; minimum inferred", "V/I", "SB"),
    ("2003-07-29", "signing", "Marquis Daniels", None, "DAL", 1, None, "undrafted; one year", "V", "BBR04"),
    ("2003-07-30", "signing", "Anthony Carter", "MIA", "SAS", 2, 1500000, "", "V", "SB"),
    ("2003-07-31", "signing", "Devin Brown", None, "SAS", None, None, "undisclosed", "V", "BBR04"),
    ("2003-08-02", "signing", "Samaki Walker", "LAL", "MIA", 1, None, "one year", "V", "SB, BBRMIA"),
    ("2003-08-04", "signing", "Olden Polynice", None, "LAC", 1, None, "one year", "V", "SB"),
    ("2003-08-05", "re_sign", "Richard Hamilton", "DET", "DET", 7, 62000000, "restricted; $62M (scoreboard) or $62,562,500 (snippet)", "V/S", "SB, SHAM"),
    ("2003-08-06", "signing", "Udonis Haslem", None, "MIA", 2, None, "undrafted; two-year minimum, partially guaranteed (snippet)", "V/S", "BBRMIA, SHAM"),
    ("2003-08-06", "signing", "Michael Ruffin", None, "UTA", None, None, "undisclosed", "V", "BBR04"),
    ("2003-08-07", "signing", "Adrian Griffin", "DAL", "HOU", 2, 1500000, "", "V", "SB"),
    ("2003-08-08", "signing", "John Wallace", None, "MIA", None, None, "undisclosed", "V", "BBRMIA"),
    ("2003-08-08", "signing", "Loren Woods", "MIN", "MIA", None, None, "undisclosed", "V", "BBRMIA"),
    ("2003-08-09", "signing", "James Posey", "HOU", "MEM", 4, 23000000, "restricted; reported $23M", "V", "SB"),
    ("2003-08-11", "offer_sheet", "Lamar Odom", "LAC", "MIA", 6, 65000000, "'almost $67M' (scoreboard) or $63.6M (snippet); Clippers declined August 25; signed August 26", "V/S", "SB, ST09, BBRMIA, SHAM"),
    ("2003-08-25", "match_declined", "Lamar Odom", "LAC", "MIA", 6, 65000000, "Clippers declined to match Miami's sheet", "V", "ST09, BBRMIA"),
    ("2003-08-13", "signing", "Eddie House", "MIA", "LAC", None, None, "undisclosed", "V", "BBR04"),
    ("2003-08-13", "signing", "Rick Brunson", "CHI", "TOR", None, None, "undisclosed; later to the Clippers September 30", "V", "BBR04"),
    ("2003-08-15", "signing", "Anthony Peeler", "MIL", "SAC", 1, None, "waived by Milwaukee July 7", "V", "SB"),
    ("2003-08-18", "signing", "Earl Boykins", "GSW", "DEN", 5, 13700000, "", "V", "SB"),
    ("2003-08-19", "signing", "Jon Barry", "DET", "DEN", None, None, "undisclosed", "V", "BBR04"),
    ("2003-08-19", "rookie_signing", "Dwyane Wade", None, "MIA", 3, None, "rookie scale, No. 5 pick (real Miami; the career's Wade signs by simulation)", "V", "BBRMIA"),
    ("2003-08-20", "signing", "Kendall Gill", "MIN", "CHI", None, None, "undisclosed", "V", "BBR04"),
    ("2003-08-21", "re_sign", "Reggie Miller", "IND", "IND", 3, 16500000, "date approximate; amount from a snippet", "S", "PAC, DES"),
    ("2003-08-22", "signing", "Travis Best", "MIA", "DAL", None, None, "undisclosed", "V", "BBR04"),
    ("2003-08-22", "signing", "Tony Massenburg", "UTA", "SAC", None, None, "undisclosed", "V", "BBR04"),
    ("2003-08-25", "signing", "Chris Whitney", "ORL", "WAS", None, None, "undisclosed", "V", "BBR04"),
    ("2003-08-27", "signing", "Calbert Cheaney", "UTA", "GSW", None, None, "undisclosed", "V", "BBR04"),
    ("2003-09-04", "signing", "Rafer Alston", "TOR", "MIA", None, None, "undisclosed; a short deal (he was a free agent again in 2004)", "V/I", "BBRMIA"),
    ("2003-09-04", "signing", "Jacque Vaughn", "ORL", "ATL", None, None, "undisclosed", "V", "BBR04"),
    ("2003-09-11", "offer_sheet", "Jason Terry", "ATL", "UTA", 3, 22500000, "Utah offer sheet; Atlanta matched September 25 (snippet dates)", "S", "WP Jason_Terry, SHAM"),
    ("2003-09-25", "match", "Jason Terry", "ATL", "ATL", 3, 22500000, "Atlanta matched (snippet)", "S", "WP Jason_Terry, SHAM"),
    ("2003-09-12", "signing", "Voshon Lenard", "TOR", "DEN", None, None, "undisclosed", "V", "BBR04"),
    ("2003-09-19", "signing", "Kenny Anderson", "NOH", "IND", None, None, "undisclosed", "V", "BBR04"),
    ("2003-09-20", "signing", "Mark Pope", "NYK", "DEN", None, None, "undisclosed", "V", "BBR04"),
    ("2003-09-23", "signing", "Bimbo Coles", "BOS", "MIA", None, None, "undisclosed", "V", "BBRMIA"),
    ("2003-09-23", "signing", "Darvin Ham", "ATL", "DET", None, None, "undisclosed", "V", "BBR04"),
    ("2003-09-23", "signing", "Donnell Harvey", "DEN", "ORL", None, None, "undisclosed", "V", "BBR04"),
    ("2003-09-26", "signing", "Raja Bell", "DAL", "UTA", None, None, "undisclosed", "V", "BBR04"),
    ("2003-09-27", "signing", "Bobby Simmons", "WAS", "LAC", None, None, "undisclosed", "V", "BBR04"),
    ("2003-09-29", "signing", "Sean Marks", "MIA", "SAS", None, None, "camp deal; waived October 31", "V", "BBR04"),
    ("2003-09-29", "signing", "Tracy Murray", "LAL", "POR", None, None, "camp deal", "V", "BBR04"),
    ("2003-09-29", "signing", "Shammond Williams", None, "ORL", None, None, "camp deal", "V", "BBR04"),
    ("2003-09-29", "signing", "Alton Ford", None, "ORL", None, None, "camp deal", "V", "BBR04"),
    ("2003-09-29", "signing", "Dan Langhi", None, "SAS", None, None, "camp deal", "V", "BBR04"),
    ("2003-09-30", "signing", "Jim Jackson", "SAC", "HOU", None, None, "undisclosed", "V", "BBR04"),
    ("2003-09-30", "signing", "Lee Nailon", "NYK", "ATL", None, None, "undisclosed", "V", "BBR04"),
    ("2003-10-01", "signing", "Bryon Russell", "WAS", "LAL", None, None, "undisclosed", "V", "BBR04"),
    ("2003-10-01", "signing", "DerMarr Johnson", "ATL", "PHO", None, None, "waived October 16", "V", "BBR04"),
    ("2003-10-03", "signing", "Stephen Jackson", "SAS", "ATL", 2, None, "two years; $2.1M per a doubtful snippet", "V/S", "BBR04"),
    ("2003-10-09", "signing", "Dikembe Mutombo", "NJN", "NYK", 2, None, "after a New Jersey buyout (waived October 7)", "V/S", "BBR04"),
    ("2003-10-10", "signing", "Glen Rice", "UTA", "LAC", None, None, "waived by Utah after the September 30 trade", "V", "BBR04"),
    ("2003-10-23", "signing", "Vladimir Stepania", "MIA", "POR", None, None, "undisclosed", "V", "BBR04"),
    ("2003-10-28", "signing", "Scott Padgett", "UTA", "HOU", None, None, "undisclosed", "V", "BBR04"),
    ("2003-10-28", "signing", "Trenton Hassell", "CHI", "MIN", None, None, "waived by Chicago October 23", "V", "BBR04"),
    ("2003-10-29", "signing", "Steve Smith", "SAS", "NOH", None, None, "undisclosed", "V", "BBR04"),
    # Re-signings the Basketball-Reference log does not date (same-club); dated at the first signing day.
    ("2003-07-16", "re_sign", "P.J. Brown", "NOH", "NOH", 4, 34000000, "date not logged", "V", "SB"),
    ("2003-07-16", "re_sign", "Derrick Coleman", "PHI", "PHI", 2, 10000000, "$10M to $12M; date not logged", "V", "SB"),
    ("2003-07-16", "re_sign", "Lucious Harris", "NJN", "NJN", 2, 5000000, "date not logged", "V", "SB"),
    ("2003-07-16", "re_sign", "Andrew DeClercq", "ORL", "ORL", 2, 5000000, "date not logged", "V", "SB"),
    ("2003-07-16", "re_sign", "Jake Voskuhl", "PHO", "PHO", 3, 5000000, "date not logged", "V", "SB"),
    ("2003-07-16", "re_sign", "Scott Williams", "PHO", "PHO", 1, 1000000, "date not logged", "V", "SB"),
    ("2003-07-16", "re_sign", "Corie Blount", "CHI", "CHI", 2, 3400000, "date not logged", "V", "SB"),
    ("2003-07-16", "re_sign", "Mark Blount", "BOS", "BOS", None, None, "multiyear; date not logged", "V", "SB"),
    ("2003-07-16", "re_sign", "Walter McCarty", "BOS", "BOS", None, None, "multiyear; date not logged", "V", "SB"),
    ("2003-07-16", "re_sign", "Kevin Willis", "SAS", "SAS", None, None, "date not logged", "V", "SB"),
    ("2003-07-16", "signing", "Tyronn Lue", "WAS", "ORL", 2, 3000000, "date not logged", "V", "SB"),
    ("2003-07-16", "signing", "Damon Jones", "SAC", "MIL", None, None, "date not logged", "V", "SB"),
    # Miami's real later signings, outside the window, for completeness (all skipped by rule 1).
    ("2003-11-03", "signing", "Kirk Penney", None, "MIA", None, None, "waived November 7", "V", "BBRMIA"),
    ("2003-11-07", "signing", "Tyrone Hill", "PHI", "MIA", None, None, "waived December 1", "V", "BBRMIA"),
    ("2003-12-01", "signing", "Wang Zhizhi", "LAC", "MIA", None, None, "", "V", "BBRMIA"),
]

# (date, clubs and assets, mechanism, evidence, sources)
TRADES = [
    ("2003-06-23", {"DAL": {"out": ["Xue Yuyang (draft rights)"], "in": ["2004 2nd-round pick"]}, "DEN": {"out": ["2004 2nd-round pick"], "in": ["Xue Yuyang (draft rights)"]}}, "draft rights", "V", "BBR03"),
    ("2003-06-25", {"BOS": {"out": ["Darius Songaila (draft rights)"], "in": ["Brandon Hunter (2003 2nd)", "2005 2nd-round pick"]}, "SAC": {"out": ["Brandon Hunter (2003 2nd)", "2005 2nd-round pick"], "in": ["Darius Songaila (draft rights)"]}}, "draft rights", "V", "BBR03"),
    ("2003-06-26", {"CHI": {"out": ["Matt Bonner (draft rights)"], "in": ["2004 2nd-round pick"]}, "TOR": {"out": ["2004 2nd-round pick"], "in": ["Matt Bonner (draft rights)"]}}, "draft night", "V", "BBR03"),
    ("2003-06-26", {"NJN": {"out": ["Kyle Korver (draft rights)"], "in": ["cash"]}, "PHI": {"out": ["cash"], "in": ["Kyle Korver (draft rights)"]}}, "draft night, cash", "V", "BBR03"),
    ("2003-06-26", {"BOS": {"out": ["Troy Bell (draft rights)", "Dahntay Jones (draft rights)"], "in": ["Marcus Banks (draft rights)", "Kendrick Perkins (draft rights)"]}, "MEM": {"out": ["Marcus Banks (draft rights)", "Kendrick Perkins (draft rights)"], "in": ["Troy Bell (draft rights)", "Dahntay Jones (draft rights)"]}}, "draft night", "V", "BBR03"),
    ("2003-06-26", {"PHI": {"out": ["Paccelis Morlende (draft rights)"], "in": ["Willie Green (draft rights)"]}, "SEA": {"out": ["Willie Green (draft rights)"], "in": ["Paccelis Morlende (draft rights)"]}}, "draft night", "V", "BBR03"),
    ("2003-06-26", {"PHO": {"out": ["2005 1st-round pick"], "in": ["Leandro Barbosa (draft rights)"]}, "SAS": {"out": ["Leandro Barbosa (draft rights)"], "in": ["2005 1st-round pick"]}}, "draft night", "V", "BBR03"),
    ("2003-06-26", {"MIL": {"out": ["Keith Bogans (draft rights)"], "in": ["cash"]}, "ORL": {"out": ["cash"], "in": ["Keith Bogans (draft rights)"]}}, "draft night, cash", "V", "BBR03"),
    ("2003-06-27", {"MIL": {"out": ["Sam Cassell", "Ervin Johnson"], "in": ["Anthony Peeler", "Joe Smith"]}, "MIN": {"out": ["Anthony Peeler", "Joe Smith"], "in": ["Sam Cassell", "Ervin Johnson"]}}, "salary matching; Peeler waived July 7", "V", "BBR03, PAY"),
    ("2003-07-23", {"ATL": {"out": ["Glenn Robinson", "2006 2nd-round pick"], "in": ["Terrell Brandon", "Randy Holcomb", "conditional 2007 1st-round pick (became cash)"]}, "PHI": {"out": ["Keith Van Horn", "Randy Holcomb", "conditional 2007 1st-round pick"], "in": ["Glenn Robinson", "Marc Jackson", "2006 2nd-round pick"]}, "MIN": {"out": ["Terrell Brandon", "Marc Jackson"], "in": ["Latrell Sprewell"]}, "NYK": {"out": ["Latrell Sprewell"], "in": ["Keith Van Horn"]}}, "four-team salary match; Brandon's insured contract was Atlanta's asset", "V", "FOUR, BBR04"),
    ("2003-07-24", {"IND": {"out": ["Brad Miller (sign-and-trade)", "Ron Mercer"], "in": ["Scot Pollard", "Danny Ferry"]}, "SAC": {"out": ["Scot Pollard", "Hedo Turkoglu"], "in": ["Brad Miller"]}, "SAS": {"out": ["Danny Ferry"], "in": ["Hedo Turkoglu", "Ron Mercer"]}}, "three-team sign-and-trade; Spurs absorbed salary into room", "V", "BMILL, BBR04"),
    ("2003-07-29", {"BOS": {"out": ["J.R. Bremer", "Bruno Sundov", "2005 2nd-round pick"], "in": ["Jumaine Jones"]}, "CLE": {"out": ["Jumaine Jones"], "in": ["J.R. Bremer", "Bruno Sundov", "2005 2nd-round pick"]}}, "Jones was a Cleveland restricted free agent; sign-and-trade likely (unverified)", "V/I", "BBR04"),
    ("2003-08-05", {"SAC": {"out": ["Keon Clark", "2004 2nd-round pick", "2007 2nd-round pick"], "in": ["2004 2nd-round pick"]}, "UTA": {"out": ["2004 2nd-round pick"], "in": ["Keon Clark", "2004 2nd-round pick", "2007 2nd-round pick"]}}, "tax dump into Utah's room", "V", "BBR04"),
    ("2003-08-18", {"DAL": {"out": ["Evan Eschmeyer", "Avery Johnson", "Popeye Jones", "Antoine Rigaudeau", "Nick Van Exel"], "in": ["Danny Fortson", "Antawn Jamison", "Chris Mills", "Jiri Welsch"]}, "GSW": {"out": ["Danny Fortson", "Antawn Jamison", "Chris Mills", "Jiri Welsch"], "in": ["Evan Eschmeyer", "Avery Johnson", "Popeye Jones", "Antoine Rigaudeau", "Nick Van Exel"]}}, "nine-player salary match", "V", "BBR04"),
    ("2003-08-21", {"DET": {"out": ["Clifford Robinson", "Pepe Sanchez"], "in": ["Bob Sura"]}, "GSW": {"out": ["Bob Sura"], "in": ["Clifford Robinson", "Pepe Sanchez"]}}, "salary match", "V", "BBR04"),
    ("2003-08-28", {"DET": {"out": ["Michael Curry"], "in": ["Lindsey Hunter"]}, "TOR": {"out": ["Lindsey Hunter"], "in": ["Michael Curry"]}}, "salary match", "V", "BBR04"),
    ("2003-09-28", {"LAC": {"out": ["2004 2nd-round pick"], "in": ["Predrag Drobnjak"]}, "SEA": {"out": ["Predrag Drobnjak"], "in": ["2004 2nd-round pick"]}}, "into the Clippers' remaining room (inferred)", "V/I", "BBR04"),
    ("2003-09-30", {"HOU": {"out": ["Glen Rice", "three 2nd-round picks"], "in": ["John Amaechi", "2004 2nd-round pick", "trade exception"]}, "UTA": {"out": ["John Amaechi", "2004 2nd-round pick"], "in": ["Glen Rice", "three 2nd-round picks"]}}, "Utah absorbed Rice into room and later waived him", "V", "BBR04"),
    ("2003-09-30", {"MEM": {"out": ["Robert Archibald", "Brevin Knight", "Cezary Trybanski"], "in": ["Bo Outlaw", "Jake Tsakalidis"]}, "PHO": {"out": ["Bo Outlaw", "Jake Tsakalidis"], "in": ["Robert Archibald", "Brevin Knight", "Cezary Trybanski"]}}, "salary match", "V", "BBR04"),
    ("2003-10-20", {"BOS": {"out": ["Antoine Walker", "Tony Delk"], "in": ["Raef LaFrentz", "Chris Mills", "Jiri Welsch", "2004 1st-round pick"]}, "DAL": {"out": ["Raef LaFrentz", "Chris Mills", "Jiri Welsch", "2004 1st-round pick"], "in": ["Antoine Walker", "Tony Delk"]}}, "salary match; Boston tax relief", "V", "BBR04"),
    ("2003-10-25", {"CHI": {"out": ["future considerations"], "in": ["Erick Barkley", "cash"]}, "SAS": {"out": ["Erick Barkley", "cash"], "in": ["future considerations"]}}, "roster move; Barkley waived", "V", "BBR04"),
]

WAIVERS = [
    ("2003-07-07", "Anthony Peeler", "MIL", "waived after the Cassell trade", "V", "PAY, BBR04"),
    ("2003-10-07", "Dikembe Mutombo", "NJN", "buyout", "V", "BBR04"),
    ("2003-10-16", "DerMarr Johnson", "PHO", "", "V", "BBR04"),
    ("2003-10-23", "Trenton Hassell", "CHI", "", "V", "BBR04"),
    ("2003-10-27", "Sean Lampley", "MIA", "real Miami; skipped by rule 1", "V", "BBRMIA"),
    ("2003-10-31", "Sean Marks", "SAS", "", "V", "BBR04"),
]


def name_index():
    """alias -> set of bbr_ids from every player file the repository holds."""
    index = {}
    def add(name, bbr):
        if name and bbr:
            index.setdefault(alias(name), set()).add(bbr)
    rights = json.loads((ROOT / "library/2003/league/nba_2003_free_agent_rights.json").read_text(encoding="utf-8"))
    for club in rights["clubs"].values():
        for p in club["free_agents"]:
            add(p["player"], p.get("bbr_id"))
    careers = json.loads((ROOT / "library/careers/nba_player_careers.json").read_text(encoding="utf-8"))
    for bbr, p in careers["players"].items():
        add(p["player_name"], bbr)
    stats = json.loads((ROOT / "library/2003/league/nba_2002_03_player_stats.json").read_text(encoding="utf-8"))
    for r in stats["records"]:
        add(r["player_name"], r["bbr_id"])
    contracts = json.loads((ROOT / "library/2003/league/nba_2003_contracts.json").read_text(encoding="utf-8"))
    for club in contracts["clubs"].values():
        for p in club["players"] + club.get("draft_rights", []) + club.get("released_players", []):
            add(p.get("player"), p.get("bbr_id"))
    return index


def main():
    index = name_index()
    unresolved = []
    def resolve(name):
        ids = index.get(alias(name), set())
        if len(ids) == 1:
            return next(iter(ids))
        unresolved.append(name)
        return None
    rows = []
    for date, kind, player, src, dst, years, total, note, evidence, sources in SIGNINGS:
        rows.append({"date": date, "kind": kind, "player": player, "bbr_id": resolve(player),
                     "from": C[src], "to": C[dst], "years": years, "total": total,
                     "note": note, "evidence": evidence, "sources": sources,
                     "involves_miami": MIA in (C[src], C[dst])})
    trades = []
    for date, clubs, mechanism, evidence, sources in TRADES:
        trades.append({"date": date, "clubs": {C[k]: v for k, v in clubs.items()}, "mechanism": mechanism,
                       "evidence": evidence, "sources": sources, "involves_miami": "MIA" in clubs})
    waivers = [{"date": d, "player": p, "bbr_id": resolve(p), "club": C[c], "note": n, "evidence": e, "sources": s,
                "involves_miami": c == "MIA"} for d, p, c, n, e, s in WAIVERS]
    data = {
        "schema_version": 1, "league": "NBA", "season": "2003-04", "kind": "offseason_transactions",
        "window": {"from": "2003-06-23", "to": "2003-12-01"},
        "usage": ("World data (option D): real free-agent signings, offer sheets, matches, trades and waivers of the 2003 "
                  "offseason, dated. A free agent simulated Miami has not signed by his date joins his real club then. "
                  "Rows with involves_miami are real Miami transactions, skipped by rule 1; they remain as the "
                  "alternatives Miami competed against. Miami's front office never reads a row before its date."),
        "evidence_key": {"V": "read in a period source", "S": "search snippet only; amount unverified", "I": "inferred"},
        "sources": "library/2003/league/nba_2003_offseason_market_research.md (source keys)",
        "cap_context": {"salary_cap": 43840000, "mid_level": 4917000, "million_dollar_exception": 1500000,
                        "minimum_team_salary": 32880000, "tax_line_2002_03": 52880000,
                        "tax_line_2003_04_projection": 57000000, "published": "2003-07-15"},
        "signings": sorted(rows, key=lambda r: (r["date"], r["player"])),
        "trades": trades, "waivers": waivers,
        "unresolved_names": sorted(set(unresolved)),
    }
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(rows)} signings, {len(trades)} trades, {len(waivers)} waivers; unresolved names: {sorted(set(unresolved))}")


if __name__ == "__main__":
    main()
