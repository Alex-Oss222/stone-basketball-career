# How to collect Miami's cap data (roadmap items 2 and 3)

Two small jobs. Both unblock Miami's June 30 decisions and Wade's rookie contract.

- **Item 2:** the 1999 agreement's rules for free-agent cap holds and qualifying offers. These decide how much cap room Miami really has.
- **Item 3:** each expiring Miami player's history with the club. This decides whom Miami can re-sign over the cap (Bird rights).

Only rules and facts that existed on June 26, 2003 are wanted. Do not collect what any player signed later, or whether Miami made him a qualifying offer; those are decisions the simulation makes.

## Item 2: 1999 cap-hold and qualifying-offer rules

### Where to look

1. Larry Coon's 1999 Salary Cap FAQ: http://www.cbafaq.com/salarycap99.htm. It is the standard plain-English guide to the 1999 agreement.
2. If that page fails to load, use the Internet Archive copy: https://web.archive.org/web/2003/http://www.cbafaq.com/salarycap99.htm

### What to copy

Copy the full text of the answers to these questions. The FAQ numbers its questions; use the browser's find (Ctrl+F) with the words in brackets.

| Topic | Search for | Why it is needed |
|---|---|---|
| Free-agent cap holds (the "free agent amount") | `cap hold`, `free agent amount` | How much each unsigned free agent still counts against Miami's cap |
| How cap holds are removed (renouncing a player) | `renounce` | Miami can clear a hold by giving up a player's rights |
| Qualifying offers and restricted free agency | `qualifying offer`, `restricted free agent` | The June 30 decision for House, Allen and James |
| Bird, Early Bird and Non-Bird exceptions | `Larry Bird exception`, `Early Bird`, `Non-Bird` | Who Miami can re-sign over the cap, and for how much |
| Minimum salary exception | `minimum salary exception` | Filling the roster when over the cap |
| Rookie scale and draft-pick cap holds | `rookie scale`, `cap hold` near the draft section | Wade's hold and contract range (already sourced; copy if nearby) |

### How to save it

1. Open Notepad.
2. For each topic, paste the full question and answer text.
3. Above each pasted block, add a line with the page address and the question number, for example: `SOURCE: http://www.cbafaq.com/salarycap99.htm, Question 23`.
4. Save as `cba_1999_cap_holds.txt`.

Paste exactly as written. Do not summarise or reword; the importer needs the exact percentages and conditions.

## Item 3: Miami's expiring players

### The seven players

| Player | Basketball-Reference ID | Page |
|---|---|---|
| Eddie House | houseed01 | https://www.basketball-reference.com/players/h/houseed01.html |
| Malik Allen | allenma01 | https://www.basketball-reference.com/players/a/allenma01.html |
| Mike James | jamesmi01 | https://www.basketball-reference.com/players/j/jamesmi01.html |
| Alonzo Mourning | mournal01 | https://www.basketball-reference.com/players/m/mournal01.html |
| Travis Best | besttr01 | https://www.basketball-reference.com/players/b/besttr01.html |
| Vladimir Stepania | stepavl01 | https://www.basketball-reference.com/players/s/stepavl01.html |
| Sean Marks | marksse01 | https://www.basketball-reference.com/players/m/marksse01.html |

### What to record for each player

From each page, record only the seasons up to and including 2002-03:

1. **Every season's team,** from the "Per Game" table. A season with two teams means he was traded or released mid-season; record both.
2. **How he joined Miami:** drafted, traded, signed as a free agent, or claimed off waivers, with the date. Look for the "Transactions" section near the bottom of the page.
3. **Years in the NBA** before 2003-04 (count the seasons in the Per Game table). This sets his minimum salary.

If a page has no transactions section, write `unknown` rather than guessing.

### How to save it

Save one file named `miami_expiring_tenure.csv` with exactly these columns. Fill one row per player per season, then one row per player for how he joined Miami:

```
bbr_id,player,season,team,how_joined_miami,join_date,nba_seasons_before_2003_04,source_url
houseed01,Eddie House,2000-01,MIA,,,,https://www.basketball-reference.com/players/h/houseed01.html
houseed01,Eddie House,2001-02,MIA,,,,https://www.basketball-reference.com/players/h/houseed01.html
houseed01,Eddie House,2002-03,MIA,,,,https://www.basketball-reference.com/players/h/houseed01.html
houseed01,Eddie House,,,drafted,2000-06-28,3,https://www.basketball-reference.com/players/h/houseed01.html
```

The rows above only show the layout; check every value against the page. Use the team codes shown on Basketball-Reference (MIA, LAL, and so on). Dates as YYYY-MM-DD.

## Upload

1. Go to https://github.com/Alex-Oss222/stone-basketball-career/tree/milestone-1/library/incoming
2. **Add file → Upload files**, drag in `cba_1999_cap_holds.txt` and `miami_expiring_tenure.csv`, choose **Commit directly to the milestone-1 branch**, and click **Commit changes**.
3. Tell Claude "cap data uploaded".

## What happens next

The rules become a 1999 rules file in `library/2003/league/`. The tenure facts are added to Miami's contract sheet in `00_Team/Finances`. Claude then computes each expiring player's cap hold and Bird status, checks them against Miami's sheet, and marks roadmap items 2 and 3 done.
