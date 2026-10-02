# Research: the real 2003 NBA offseason market

**World data, hindsight about other clubs (AGENTS.md, option D).** Everything below happened after the June 26, 2003 checkpoint. It is accepted for the world only: it fixes when each real free agent left the market and what his real contract was, so a player simulated Miami does not sign follows history. Miami's front office never reads it before the dates it records; its decisions use only evidence dated on or before the career date. Rows marked MIA are real Miami transactions and are skipped (rule 1). The machine-readable version is `nba_2003_offseason_transactions.json`, built by `scripts/build_offseason_transactions.py`.

Nothing in the repository was modified. Repository files read for structure only: `library/2003/league/nba_2003_free_agent_rights.json` (129 expiring players, Bird class, holds, QO arithmetic; no outcomes), `nba_2003_contracts.json` (June 26 ledger, no post-checkpoint events), `nba_2003_expiring_contracts.json` (July 1 Deseret list; `rfa_eligible` is eligibility only). The findings below are consistent with those files' "no outcomes recorded" design and are offered as the real-world market evidence the AI/GM world model (option D) needs for the 28 other clubs.

**Evidence legend.** V = read directly in a period source (ESPN 2003 article, AP wire, Basketball-Reference). S = figure came only from a search-engine snippet of a source this sandbox could not open (shamsports, spotrac, deseret, UPI were blocked); treat as unverified. I = my inference from CBA arithmetic.

**Source keys (URLs).**
- BBR04 https://www.basketball-reference.com/leagues/NBA_2004_transactions.html (all dates below unless noted; BBR does not list same-club re-signings)
- BBR03 https://www.basketball-reference.com/leagues/NBA_2003_transactions.html (June 23–27 trades)
- BBRMIA https://www.basketball-reference.com/teams/MIA/2004_transactions.html
- SB https://www.espn.com/nba/s/2003/freeagents/scoreboard.html (ESPN scoreboard, updated Aug 25, 2003; the main amounts source)
- CAP https://www.espn.com/nba/news/2003/0715/1581132.html (AP, Jul 15: cap $43.84M, MLE $4.917M, tax line $52.9M, min team salary $32.88M)
- LAW https://www.espn.com/nba/columns/lawrence_mitch/1574522.html (Jun 30 preview)
- SMITH https://www.espn.com/nba/columns/smith_sam/1580965.html (Jul 15, Heat cap room)
- ST28 https://www.espn.com/nba/columns/stein_marc/1586512.html (Stein scorecard, Jul 28)
- ST12 https://www.espn.com/nba/columns/stein_marc/1579816.html ; ST13 https://www.espn.com/nba/news/2003/0713/1580271.html ; ST15 https://www.espn.com/nba/columns/stein_marc/1580887.html ; ST09 https://www.espn.com/nba/columns/stein_marc/1593277.html (Odom, Aug 9)
- KIDD https://www.espn.com/nba/news/2003/0711/1579469.html ; ZO https://www.espn.com/nba/news/2003/0711/1579328.html ; ZO2 https://www.espn.com/nba/news/2003/0709/1578782.html
- BRAND https://www.espn.com/nba/news/2003/0716/1581398.html ; MATCH https://www.espn.com/nba/news/2003/0718/1582499.html ; CLIP https://www.espn.com/nba/news/2003/0720/1583168.html
- ARENAS https://www.espn.com/nba/news/2003/0721/1583869.html ; WIZ https://www.espn.com/nba/news/2003/0715/1580879.html ; FRIEND https://www.espn.com/nba/columns/misc/1586294.html ; ARRULE https://hoopsrumors.com/2013/05/gilbert-arenas-provision.html
- AMILL https://www.espn.com/nba/news/2003/0716/1581622.html ; MM https://www.espn.com/nba/news/2003/0714/1580403.html ; JAZZ https://www.espn.com/nba/news/2003/0716/1581461.html ; JAZZ2 https://www.espn.com/nba/news/2003/0721/1583480.html
- HOW https://www.espn.com/nba/news/2003/0716/1581574.html ; HOW2 https://www.espn.com/nba/news/2003/0713/1580308.html ; DUNC https://www.espn.com/nba/news/2003/0716/1581549.html
- MAL https://www.espn.com/nba/news/2003/0710/1579083.html ; PAY https://www.espn.com/nba/news/2003/0708/1578233.html
- BMILL https://www.espn.com/nba/news/2003/0724/1585136.html ; PAC https://www.espn.com/nba/news/2003/0722/1584286.html ; FOUR https://www.espn.com/nba/news/2003/0723/1584797.html
- HORRY https://www.espn.com/nba/news/2003/0722/1584351.html ; DAN https://www.espn.com/nba/news/2003/0719/1582928.html
- FALIST https://www.espn.com/espn/print?id=1575042&type=story (AP free-agent list, Jun 30)
- WP = en.wikipedia.org/wiki/<Player> (named per row)
- SHAM = shamsports.com player pages (blocked; S only); SPOT = spotrac (S only); DES = deseret.com (S only)

---

## 1. Free-agent signings, offer sheets and sign-and-trades, July 16 – October 31, 2003

Signing moratorium ended July 16 (first legal signing day) (CAP, DUNC). Rows marked **MIA** involve Miami and are skipped under world-model rule 1. Terms "undisclosed" = no period figure found.

| Date | Player | From → To | Reported terms | Ev. | Source |
|---|---|---|---|---|---|
| Jul 16 | **Alonzo Mourning** MIA | Miami → New Jersey | 4 yr, $22M (Jul 11 report: $20M); MLE-sized | V | SB, ZO |
| Jul 16 | Juwan Howard | Denver → Orlando | 5 yr, "at least $28M" (range $28–38M); starts at full MLE $4.9M | V | SB, HOW, HOW2 |
| Jul 16 | Karl Malone | Utah → L.A. Lakers | 2 yr, $3M; $1.5M first year | V | SB, MAL |
| Jul 16 | Gary Payton | Milwaukee → L.A. Lakers | Full MLE ($4.917M start); 2 yr $10,325,700 w/ player option | V (MLE) / S (total) | SB, PAY, SPOT |
| Jul 16 | Rasho Nesterovic | Minnesota → San Antonio | 6 yr, $42M (Stein) / $45M (SB); Wolves had offered 7 yr $50M+ | V | ST15, SB, ST13 |
| Jul 16 | Michael Olowokandi | L.A. Clippers → Minnesota | 3 yr, $16.2M (= full MLE for 3 yrs) | V | SB, AMILL |
| Jul 16 | Tim Duncan | San Antonio (re-sign) | 7 yr, $122M; 70% paid before each season; ETO after 2007-08 | V | DUNC, SB |
| Jul 16 | Jermaine O'Neal | Indiana (re-sign) | 7 yr, $120M (SB) / $126,588,000 (S) | V/S | SB, PAC, SHAM |
| Jul 16 | Kenny Thomas (RFA) | Philadelphia (re-sign) | 7 yr, "over $40M" (SB) / $50,400,500 (S) | V/S | SB, SHAM |
| Jul 16 | **Elton Brand (RFA)** MIA | Offer sheet from Miami | 6 yr, $82.2M (Heat side reported $84.2M); Clippers matched Jul 19 | V | BRAND, MATCH, SB |
| Jul 16 | Andre Miller (RFA) | Offer sheet from Denver | 6 yr, $51.17M + $4.5M bonuses, $10M signing bonus, $14M up front; Clippers declined; signed Aug 1 | V | AMILL, MM, BBR04 |
| Jul 16 | Corey Maggette (RFA) | Offer sheet from Utah | 6 yr, $42M ($45M per AP), front-loaded; Clippers matched (date not found, within 15 days) | V | JAZZ, MATCH, SB |
| Jul 16 | Jérôme Moïso | New Orleans → Toronto | undisclosed | V | BBR04 |
| Jul 16 | Milt Palacio | Cleveland → Toronto | undisclosed | V | BBR04 |
| Jul 16 | Amal McCaskill | → Philadelphia | undisclosed | V | BBR04 |
| Jul 16 | Theron Smith (undrafted) | → Memphis | undisclosed | V | BBR04 |
| Jul 16 | Jason Kidd | New Jersey (re-sign) | agreed Jul 11: 6 yr, $99M, raised to $103.67M by the cap figure (30% max, 12.5% raises) | V | KIDD, CAP, SB |
| Jul 17 | Kevin Ollie | Seattle → Cleveland | 5 yr, $15M | V | SB, HOW |
| Jul 17 | Brian Skinner | Philadelphia → Milwaukee | 3 yr, $5M | V | SB |
| Jul 17 | Erick Strickland | Indiana → Milwaukee | 2 yr, $3.1M | V | SB |
| Jul 17 | Daniel Santiago | Lottomatica Roma → Milwaukee | undisclosed | V | SB |
| Jul 17 | Mengke Bateer | San Antonio → Toronto | undisclosed | V | BBR04 |
| Jul 19 | Antonio Daniels | Portland → Seattle | multiyear, undisclosed (S: 3 yr $7.5M) | V/S | DAN, SB |
| Jul 20 | Scottie Pippen | Portland → Chicago | 2 yr, $10M (MLE) | V | SB, WP Scottie_Pippen |
| Jul 21 | Sean Rooks | L.A. Clippers → New Orleans | 1 yr | V | SB |
| Jul 22 | Ira Newble | Atlanta → Cleveland | half of the $4.9M MLE | V | SB |
| Jul 23 | Speedy Claxton | San Antonio → Golden State | 3 yr, about $10M | V | SB, WP Speedy_Claxton |
| Jul 24 | Robert Horry | L.A. Lakers → San Antonio | 2 yr, $9.45–9.5M; Spurs team option yr 2 ($4.5M yr 1) | V | HORRY, ST28 |
| Jul 24 | Anthony Johnson | New Jersey → Indiana | 1 yr, undisclosed | V | SB, WP Anthony_Johnson_(basketball) |
| Jul 24 | **Brad Miller** (sign-and-trade) | Indiana → Sacramento | 7 yr, $68M, signed then traded (see trades) | V | BMILL |
| Jul 25 | **Mike James** MIA | Miami → Boston | undisclosed | V | BBR04 |
| Jul 26 | Elden Campbell | Seattle → Detroit | 2 yr, about $8.4M | V | SB, WP Elden_Campbell |
| Jul 26 | Eric Piatkowski | L.A. Clippers → Houston | 3 yr, $8M | V | SB |
| Jul 28 | Fred Hoiberg | Chicago → Minnesota | 1 yr | V | SB |
| Jul 28 | Mark Madsen | L.A. Lakers → Minnesota | undisclosed | V | SB |
| Jul 29 | Darrell Armstrong | Orlando → New Orleans | 2 yr, $6M | V | SB |
| Jul 29 | Horace Grant | Orlando → L.A. Lakers | undisclosed (minimum, I) | V | SB |
| Jul 29 | Marquis Daniels (undrafted) | → Dallas | 1 yr | V | BBR04, WP Marquis_Daniels |
| Jul 30 | **Anthony Carter** MIA | Miami → San Antonio | 2 yr, $1.5M | V | SB |
| Jul 31 | Devin Brown | → San Antonio | undisclosed | V | BBR04 |
| Aug 2 | **Samaki Walker** MIA | L.A. Lakers → Miami | 1 yr | V | SB, BBRMIA |
| Aug 4 | Olden Polynice | → L.A. Clippers | 1 yr | V | SB |
| Aug 5 | Richard Hamilton (RFA) | Detroit (re-sign) | 7 yr, $62M (SB) / $62,562,500 (S) | V/S | SB, SHAM |
| Aug 6 | **Udonis Haslem** (undrafted) MIA | → Miami | 2 yr minimum, partially guaranteed (S) | V/S | BBRMIA, SHAM |
| Aug 6 | Michael Ruffin | → Utah | undisclosed | V | BBR04 |
| Aug 7 | Adrian Griffin | Dallas → Houston | 2 yr, reported $1.5M | V | SB |
| Aug 8 | **John Wallace** MIA | → Miami | undisclosed | V | BBRMIA |
| Aug 8 | **Loren Woods** MIA | Minnesota → Miami | undisclosed | V | BBRMIA |
| Aug 8 | **Gilbert Arenas (RFA)** | Golden State → Washington | 6 yr, $64–65M; offer sheet signed Jul 21, Warriors could not match; BBR registers Aug 8 | V | ARENAS, FRIEND, SB, BBR04 |
| Aug 9 | James Posey (RFA) | Houston → Memphis | 4 yr, reported $23M | V | SB |
| Aug 11 | **Lamar Odom (RFA)** MIA | Offer sheet from Miami | 6 yr, "almost $67M" (SB) / $63.6M (S); Clippers declined Aug 25; signed Aug 26 | V/S | SB, ST09, BBRMIA, SHAM |
| Aug 13 | **Eddie House** MIA | Miami → L.A. Clippers | undisclosed | V | BBR04 |
| Aug 13 | Rick Brunson | Chicago → Toronto (later to Clippers Sep 30) | undisclosed | V | BBR04 |
| Aug 15 | Anthony Peeler | Milwaukee (waived Jul 7) → Sacramento | 1 yr | V | SB |
| Aug 18 | Earl Boykins | Golden State → Denver | 5 yr, $13.7M | V | SB, WP Earl_Boykins |
| Aug 19 | Jon Barry | Detroit → Denver | undisclosed | V | BBR04 |
| Aug 19 | **Dwyane Wade** MIA | rookie scale, No. 5 pick | V | BBRMIA |
| Aug 20 | Kendall Gill | Minnesota → Chicago | undisclosed | V | BBR04 |
| ~Aug 21 | Reggie Miller | Indiana (re-sign) | 3 yr, $16.5M (S); Pacers were "working to re-sign" him Jul 22 | V/S | PAC, DES |
| Aug 22 | **Travis Best** MIA | Miami → Dallas | undisclosed | V | BBR04 |
| Aug 22 | Tony Massenburg | Utah → Sacramento | undisclosed | V | BBR04 |
| Aug 25 | Chris Whitney | Orlando → Washington | undisclosed | V | BBR04 |
| Aug 27 | Calbert Cheaney | Utah → Golden State | undisclosed | V | BBR04 |
| Sep 4 | **Rafer Alston** MIA | Toronto → Miami | undisclosed (left as FA in 2004, so short deal, I) | V | BBRMIA |
| Sep 4 | Jacque Vaughn | Orlando → Atlanta | undisclosed | V | BBR04 |
| Sep 11/25 | Jason Terry (RFA) | Utah offer sheet 3 yr $22.5M; Atlanta matched Sep 25 | S | WP Jason_Terry, SHAM |
| Sep 12 | Voshon Lenard | Toronto → Denver | undisclosed | V | BBR04 |
| Sep 19 | Kenny Anderson | New Orleans → Indiana | undisclosed | V | BBR04 |
| Sep 20 | Mark Pope | New York → Denver | undisclosed | V | BBR04 |
| Sep 23 | **Bimbo Coles** MIA | Boston → Miami | undisclosed | V | BBRMIA |
| Sep 23 | Darvin Ham | Atlanta → Detroit; Donnell Harvey Denver → Orlando | undisclosed | V | BBR04 |
| Sep 26–27 | Raja Bell | Dallas → Utah; Bobby Simmons Washington → L.A. Clippers | undisclosed | V | BBR04, WP Raja_Bell |
| Sep 29 | **Sean Marks** MIA | Miami → San Antonio (waived Oct 31) | camp deal | V | BBR04 |
| Sep 29 | Tracy Murray → Portland; Shammond Williams, Alton Ford → Orlando; Dan Langhi → San Antonio | camp/undisclosed | V | BBR04 |
| Sep 30 | Jim Jackson Sacramento → Houston; Lee Nailon New York → Atlanta | undisclosed | V | BBR04 |
| Oct 1 | Bryon Russell Washington → L.A. Lakers; DerMarr Johnson Atlanta → Phoenix (waived Oct 16) | undisclosed | V | BBR04 |
| Oct 3 | Stephen Jackson | San Antonio → Atlanta | 2 yr (S: $2.1M, doubtful) | V/S | BBR04, UPI snippet |
| Oct 9 | Dikembe Mutombo | New Jersey (buyout, waived Oct 7) → New York | 2 yr | V/S | BBR04, WP Dikembe_Mutombo |
| Oct 10 | Glen Rice | Utah (after Sep 30 trade, waived) → L.A. Clippers | undisclosed | V | BBR04 |
| Oct 23 | **Vladimir Stepania** MIA | Miami → Portland | undisclosed | V | BBR04 |
| Oct 28–29 | Scott Padgett Utah → Houston; Trenton Hassell Chicago (waived Oct 23) → Minnesota; Steve Smith San Antonio → New Orleans | undisclosed | V | BBR04 |
| (re-signs, no BBR date) | P.J. Brown NOH 4 yr $34M; Derrick Coleman PHI 2 yr $10–12M; Lucious Harris NJN 2 yr $5M; Andrew DeClercq ORL 2 yr $5M; Jake Voskuhl PHX 3 yr $5M; Scott Williams PHX 1 yr $1M; Corie Blount CHI 2 yr $3.4M; Mark Blount, Walter McCarty BOS multiyear; Kevin Willis SAS; Tyronn Lue WAS → ORL 2 yr $3M; Damon Jones SAC → MIL | V | SB |

Outside the window but Miami-related: Kirk Penney signed Nov 3, waived Nov 7; Tyrone Hill signed Nov 7, waived Dec 1; Wang Zhizhi signed Dec 1 (BBRMIA). Sean Lampley waived Oct 27 (BBRMIA).

---

## 2. Cap room and status by team, July 2003

Cap $43.84M (announced Jul 15, up ~9%); MLE $4.917M; "million-dollar" exception $1.5M; tax threshold $52.9M for 2002-03 payrolls, expected ~$57M next; minimum team salary $32.88M (CAP, LAW, MAL).

| Team | Reported position | Source |
|---|---|---|
| Denver | ~$22M under, "two max slots" (Jun 30); "at least $18M" after cap set; chose to hold room rather than overpay Arenas/Olowokandi/B. Miller | LAW, AMILL, MM, ST28 |
| San Antonio | $14M (Jun 30); "$15-odd million" (Jul 12); "at least $12M" left after Duncan and Nesterovic | LAW, ST12, ST15 |
| Utah | "nearly $20M" after Malone left; "about $20M" on Jul 16; risked being $10M+ under the minimum team salary if Maggette matched (he was) | MAL, JAZZ, ST28 |
| L.A. Clippers | A max slot available but "never spend"; in the event matched Brand and Maggette (Bird rights), declined Miller and Odom | LAW, MATCH, ST28 |
| Miami | ~$7M before June 30; ~$11M (Jul 15) / "roughly $12M" (Jul 28) after Anthony Carter's $4.1M option was not exercised; Riley hinted at saving room for 2004 | SMITH, ST28, ST13, WP Anthony_Carter_(basketball) |
| Washington | ~$8M room; offered Arenas $7M+ first year | WIZ |
| Memphis | Posey 4 yr $23M (above MLE scale → implies room, I); had offered Person's expiring $7.7M in an Olowokandi S&T | SB, ST13 |
| Orlando | Over cap; used MLE on Howard; kept DeClercq's option to stay over cap and retain MLE; Hill injury exception denied | LAW, HOW |
| L.A. Lakers | ~$60M committed, $18–20M over; MLE (Payton) + $1.5M (Malone) only | LAW, MAL, ST28 |
| Dallas | MLE only (offered Mourning 4-yr MLE); shut out | ZO, ST28 |
| Minnesota | Over cap; Bird offer to Nesterovic 7 yr $50M+; MLE to Olowokandi; absorbed Sprewell via Brandon's insured contract; payroll toward $70M | ST13, ST28, FOUR |
| New York | MLE only ($4.9M to Nesterovic) | ST13 |
| Golden State | Over cap; Arenas only via Early Bird/MLE $4.9M; Claxton got MLE-scale | ARENAS, WIZ, SB |
| Indiana | ~$7M under tax line after O'Neal; let B. Miller go via S&T; Reggie Miller 3 yr | PAC, BMILL |
| Portland | Payroll >$100M, tax >$50M; lost Pippen, Daniels; waived Sabonis | CAP, BBR04 |
| Sacramento, New York, Dallas, Philadelphia | Tax payers ($15–20M, ~$25M, $15–20M, >$10M) | CAP |
| New Jersey | ~$6M tax; Kidd and Harris via Bird; Mourning via MLE (I) | CAP, SB |
| Cleveland, Chicago, Detroit, Houston, Milwaukee, Seattle, New Orleans, Phoenix, Toronto, Boston, Atlanta | MLE/minimum/Bird clubs: Ollie+Newble split MLE (I); Pippen MLE; Campbell MLE-scale; Piatkowski partial MLE; Skinner+Strickland split MLE (I); Daniels MLE-scale; Armstrong 2 yr $6M + Brown Bird; re-signs; minimums; Blount/McCarty Bird; Atlanta took Brandon's insured $11M+ contract for February cap relief and matched Terry | SB, FOUR, ST28 |

---

## 3. Key decisions that shaped the market

- **Duncan (Jul 16)**: 7 yr $122M, stays; Spurs still had $12M+ room (DUNC, ST15). V.
- **Kidd (agreed Jul 11, signed Jul 16+)**: Spurs offered the most they could ($90–92M); Kidd stayed at 6 yr $99M → $103.67M once the cap rose; Mourning's commitment to New Jersey the same day was the lever (KIDD, ZO, CAP). V.
- **Payton/Malone to the Lakers (verbal Jul 8/10, signed Jul 16)**: Payton took the MLE; Malone $1.5M; Lakers pay $6.4M for both in 2003-04; Portland had tried a sign-and-trade (McInnis/Sabonis) worth ~$10M start; Payton also resisted "substantial overtures" from Miami (PAY, MAL, ST28). V.
- **Mourning leaves Miami (Jul 9–16)**: called the Heat offer "not a significant one"; Riley: "an opportunity that is impossible for us to match"; Dallas and Denver pursued; 4 yr $20–22M with Nets (ZO2, ZO, SB). V.
- **Brand offer sheet (Jul 16) matched (Jul 19)**: Miami's 6 yr $82.2M was the maximum an outside team could offer (25% tier, 10% raises, I); structured with up to $28M lump-sum to deter Sterling; Clippers had offered $65M/5 then $78M/6 pre-cap; matched anyway (BRAND, MATCH). V.
- **Andre Miller to Denver (sheet Jul 16, declined, signed Aug 1)**: 6 yr $51.17M + bonuses, $14M up front; Utah also bid (AMILL, MM, ST28). V.
- **Maggette (Utah sheet Jul 16, matched)** 6 yr $42–45M; **Odom (Miami sheet Aug 11, declined Aug 25, signed Aug 26)**: Clippers had offered 3 yr $24M and said they would match; Odom asked ≥$60M/6; Miami first tried a sign-and-trade the Clippers refused (ST09, SB). V/S.
- **Arenas to Washington (sheet Jul 21; official Aug 8)**: 6 yr $64–65M (~$8.65M start, I). Warriors over the cap; as a 2001 second-round pick finishing a two-year deal he had only Early Bird rights, so Golden State could not exceed a $4.9M starting salary without clearing three contracts; Clippers also offered ~$60M. Led to the 2005 "Arenas provision" (ARENAS, WIZ, CLIP, ARRULE). V.
- **Jermaine O'Neal (Jul 16)** 7 yr $120–126.6M; cancelled Dallas/San Antonio visits (SB, ZO). V.
- **Brad Miller (Jul 24)**: Utah offered ~$52–55M/6, Denver $49M; Pacers could not re-sign without tax, so sign-and-trade at 7 yr $68M to Sacramento (PAC, JAZZ2, BMILL). V.
- **Juwan Howard (Jul 16)**: Detroit offered the MLE; Orlando won at MLE for 5 years (~$28–29.5M); Denver offered more money (HOW2, HOW). V.
- **Olowokandi (Jul 16)**: Memphis, Miami, Denver interested; took Minnesota's 3-yr MLE ($16.2M) after Nesterovic left (ST13, AMILL). V.
- **Rasheed Wallace**: no 2003 free-agent event; only rumored as a Portland tax dump candidate to Miami (SMITH). Not a market fact.

---

## 4. Market prices by tier (2003-04 cap arithmetic; totals from SB unless noted)

- **Maximum**: 30% tier (7+ yrs) start $13.152M → Kidd 6 yr $103.67M (12.5% raises); O'Neal/Duncan 7 yr $122–126.6M. 25% tier (0–6 yrs) start $10.96M → Brand 6 yr $82.2M from an outside club (10% raises). Only Kidd and O'Neal were expected to get "max money" (LAW) and only Brand's sheet and Duncan/O'Neal's re-signs reached it. V/I.
- **Young-starter restricted tier (offer sheets)**: $8.5–8.7M start → Odom $63.6–67M/6, Arenas $64–65M/6; $6.8–7.1M start → A. Miller $51M/6, Terry $22.5M/3, B. Miller $68M/7 (S&T, Bird raises); $5.2–6.5M start → Maggette $42M/6, Hamilton $62.5M/7, Thomas $50M/7, Nesterovic $42–45M/6, P.J. Brown $34M/4, Posey $23M/4. I (starts derived from totals).
- **Mid-level ($4.917M start)**: the price of a veteran starter from an over-cap club — Payton (2 yr $10.3M), Pippen (2 yr $10M), Olowokandi (3 yr $16.2M), Howard (5 yr $28–29.5M), Mourning (4 yr $22M); Campbell (2 yr $8.4M) and Horry (2 yr $9.5M, team option) just under; Reggie Miller 3 yr $16.5M (Bird, S). V.
- **Sixth-man/rotation tier ($2.3–3.0M start)**: Ollie 5 yr $15M (called a bar-raising deal by Orlando's GM, HOW), Claxton 3 yr $10M, Armstrong 2 yr $6M, Daniels 3 yr $7.5M (S), Newble half-MLE, Boykins 5 yr $13.7M, Piatkowski 3 yr $8M. V.
- **Backup tier ($1–1.6M)**: Skinner 3 yr $5M, Strickland 2 yr $3.1M, Lue 2 yr $3M, Corie Blount 2 yr $3.4M, Voskuhl 3 yr $5M, Griffin 2 yr $1.5M, Carter 2 yr $1.5M, S. Williams 1 yr $1M; Malone's $1.5M = the "$1 million exception" at its 2003-04 value (I, from Lawrence's "million-dollar exception" and Stein's $6.4M total). V/I.
- **Minimum / one-year**: Walker, Rooks, Hoiberg, Polynice, Peeler, A. Johnson, M. Daniels, Grant (I), and the September–October wave (Coles, Alston, Vaughn, Lenard, Pope, Harvey, Ham, Bell, Murray, Jim Jackson, Steve Smith, Kenny Anderson, Padgett, Hassell, Stepania, Russell, Rice); Haslem 2-yr minimum partially guaranteed (S). Lawrence (Jun 30) predicted exactly this: many players "waiting for calls" into September and thankful for the $1M exception. V.
- **Market tone**: TV money down, cap had fallen in 2002-03, dollar-for-dollar tax → "Never have so many lined up for so little" (LAW); rebuilding teams with room (Utah, Denver, Miami) "struggled mightily" to use it and chose to hold it for trades or 2004 (ST28). V.

---

## 5. Trades, June 23 – October 31, 2003

| Date | Deal | Mechanism / note | Source |
|---|---|---|---|
| Jun 23 | DAL Xue Yuyang → DEN for 2004 2nd | draft rights | BBR03 |
| Jun 25 | BOS Darius Songaila → SAC for 2003 2nd (Brandon Hunter) + 2005 2nd | draft rights | BBR03 |
| Jun 26 | CHI Matt Bonner → TOR for 2004 2nd; NJN sold Kyle Korver to PHI; BOS Troy Bell + Dahntay Jones → MEM for Marcus Banks + Kendrick Perkins; PHI Paccelis Morlende → SEA for Willie Green; PHX 2005 1st → SAS for Leandro Barbosa; MIL Keith Bogans → ORL for cash | draft-night | BBR03 |
| Jun 27 | MIL Sam Cassell + Ervin Johnson → MIN for Anthony Peeler + Joe Smith | salary match; Peeler waived Jul 7 | BBR03, PAY |
| Jul 23 | 4-team: ATL Glenn Robinson + 2006 2nd → PHI; MIN Terrell Brandon → ATL; MIN Marc Jackson → PHI; NYK Latrell Sprewell → MIN; PHI Randy Holcomb + cond. 2007 1st → ATL; PHI Keith Van Horn → NYK | salary matching; Brandon's insured contract (off the cap in February) was Atlanta's asset; conditional 1st became cash | FOUR, BBR04 |
| Jul 24 | 3-team: IND Brad Miller → SAC; IND Ron Mercer → SAS; SAC Scot Pollard → IND; SAC Hedo Türkoğlu → SAS; SAS Danny Ferry → IND | sign-and-trade (Miller 7 yr $68M); Spurs absorbed Türkoğlu/Mercer into room | BMILL, BBR04 |
| Jul 29 | BOS J.R. Bremer + Bruno Šundov + 2005 2nd → CLE for Jumaine Jones | Jones was a Cleveland RFA; likely sign-and-trade (unverified) | BBR04 |
| Aug 5 | SAC Keon Clark + 2004 2nd + 2007 2nd → UTA for 2004 2nd | Kings tax dump into Utah's room | BBR04, DES snippet |
| Aug 18 | DAL Eschmeyer, Avery Johnson, Popeye Jones, Rigaudeau, Nick Van Exel → GSW for Danny Fortson, Antawn Jamison, Chris Mills, Jiří Welsch | 9-player salary match | BBR04, WP Nick_Van_Exel |
| Aug 21 | DET Clifford Robinson + Pepe Sánchez → GSW for Bob Sura | salary match | BBR04 |
| Aug 28 | DET Michael Curry → TOR for Lindsey Hunter | salary match | BBR04 |
| Sep 28 | LAC 2004 2nd → SEA for Predrag Drobnjak | into Clippers' remaining room (I) | BBR04 |
| Sep 30 | HOU Glen Rice + three 2nds → UTA for John Amaechi + 2004 2nd; Houston received a trade exception | Utah absorbed Rice into room; later waived him | BBR04 |
| Sep 30 | MEM Archibald, Brevin Knight, Trybański → PHX for Bo Outlaw + Jake Tsakalidis | salary match | BBR04 |
| Oct 20 | BOS Antoine Walker + Tony Delk → DAL for Raef LaFrentz, Chris Mills, Jiří Welsch + 2004 1st | salary match / Boston tax relief | BBR04, WP Antoine_Walker |
| Oct 25 | CHI future considerations → SAS for Erick Barkley + cash; Barkley waived | roster move | BBR04 |

No real transaction in the window involved Miami other than the free-agent movements flagged above; the Eddie Jones-for-Brandon idea (SMITH) was rumor only.

---

## 6. Notes for the simulation

- Verified-vs-uncertain: every date is from BBR (V); amounts marked S came only from search snippets (shamsports/spotrac/deseret/UPI unreachable here) and should be re-checked before entering any ledger: O'Neal $126.6M, Thomas $50.4M, Hamilton $62.56M, Odom $63.6M, Payton $10.33M, Daniels $7.5M, Reggie Miller $16.5M, Terry $22.5M/Sep 11–25, Haslem terms, S. Jackson terms.
- The Jul 1 free-agent list (FALIST) matches the repository's `nba_2003_expiring_contracts.json` source; the AP version also lists Ken Johnson (Miami) and marks Malik Allen restricted — consistent with the repo file.
- Under rule 1, Miami's real departures (Mourning, Carter, Best, James, House, Marks, Stepania) and arrivals (Odom, Walker, Haslem, Wallace, Woods, Alston, Coles, Brand/Odom offer sheets) are all simulated events; the Clippers' real matching of Brand and declining of Odom are consequences of Miami's real offers and therefore also do not bind the world model.
- The repository's rights file prices Mourning's hold at $21.66M; the real market priced him at an MLE contract, and the Spurs/Nets/Mavericks bidding (ZO) is the evidence for that.
