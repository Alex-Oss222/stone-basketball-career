<!--
AUTHORING RULES
- Keep the section order. Regular-season statistics, playoff statistics, and awards form the final block. Awards is always the last section; add any other historical records before it.
- Use only evidence available on the assessment date for the opening report. Keep recorded statistics, statistical estimates and staff judgments distinct. Card grades do not directly drive the engine; dated generated rates do.
- Preserve the opening report and grades. Append dated changes with evidence; show old and new grades when relevant. Write the final season assessment separately and retain previous annual profiles.
- Update statistics after each completed game. The statistics date can be later than the opening assessment date. Retain every prior season.
- Write specific basketball actions and limitations. Cite the observation or statistic behind a claim. Do not invent film, practice reports, quotes, sources, or improvement.
- Keep the scouting report under 100 words. Give each grade its statistical evidence or one short staff explanation. Omit unsupported strengths/weaknesses, unused placeholders and empty detail tables.
- Keep additional statistics when available; omit empty detail tables. Use N/A for unavailable data, not zero. For no appearances, record G = 0 and N/A for averages. For zero shot attempts, use N/A for that percentage.
-->

# {{PLAYER_NAME}} | {{SEASON}} Player Profile

<!-- photo: omit if unavailable -->
<img src="{{PHOTO_URL}}" alt="{{PLAYER_NAME}}" width="160">

*Photo: {{PHOTO_CREDIT}}.*
<!-- /photo -->

**Team:** {{TEAM}} · **League:** {{LEAGUE}} · **Position:** {{POSITION}}  
**Age at assessment:** {{AGE}} · **Height:** {{HEIGHT}} · **Weight:** {{WEIGHT}}  
**Opening assessment:** {{ASSESSMENT_DATE}} · **Statistics through:** {{STATS_DATE}}  
**Previous profile:** [{{PRIOR_SEASON}}]({{PREVIOUS_PROFILE_LINK}})

## Scouting report

**Role:** {{ACTUAL_ROLE_AND_RESPONSIBILITIES}}

**Offense:** {{HOW_THE_PLAYER_SCORES_CREATES_OR_SUPPORTS_POSSESSIONS}}

**Defense:** {{ASSIGNMENTS_COVERAGES_AND_MATCHUP_LIMITS}}

**Best traits:** {{TWO_SPECIFIC_STRENGTHS}}

**Main weaknesses:** {{TWO_SPECIFIC_LIMITATIONS_AND_THEIR_EFFECT}}

## Player grades

<!-- For eligible NBA veterans, copy the generated grades by verified bbr_id. Do not rank by hand. Omit this table if no eligible statistical record exists. Keep any staff assessment in a separate, dated paragraph or table. -->

**Statistical estimates, 20–80.** 50 is the median of players with at least 500 minutes; higher is better for the named statistic. These are estimates from prior production, not staff scouting grades.

**Sample:** {{GAMES}} games, {{MINUTES}} minutes in {{SOURCE_SEASON}}. Small samples are pulled toward the league baseline; label fewer than 100 minutes “Very small sample.”

| Statistic | Grade | Recorded evidence |
| --- | ---: | --- |
| Two-point scoring | {{GRADE}} | {{TWO_PCT_AND_MAKES_ATTEMPTS}} |
| Three-point shooting | {{GRADE}} | {{THREE_PCT_AND_MAKES_ATTEMPTS}} |
| Free throws | {{GRADE}} | {{FT_PCT_AND_MAKES_ATTEMPTS}} |
| Scoring efficiency | {{GRADE}} | {{TS_PCT}} |
| Assist production | {{GRADE}} | {{AST_PCT}} |
| Turnover control | {{GRADE}} | {{TOV_PCT}}; lower is better |
| Offensive rebounding | {{GRADE}} | {{ORB_PCT}} |
| Defensive rebounding | {{GRADE}} | {{DRB_PCT}} |
| Steal production | {{GRADE}} | {{STL_PCT}} |
| Block production | {{GRADE}} | {{BLK_PCT}} |

**Tendencies:** usage {{USG_PCT}}; threes {{THREE_PAR}} of field-goal attempts; {{FTR}} free-throw attempts per field-goal attempt.

**Not assessed:** {{UNSUPPORTED_TRAITS_OR_MISSING_STATISTICAL_RECORD}}. Do not infer overall ability, rim/midrange splits, decision quality or matchup defense from these grades. A missing value or zero attempts receives “Not assessed,” not a zero grade.

**Source and method:** {{STATS_SOURCE_AND_MODEL_VERSION}} · [Statistical rating method](../../../../../../docs/statistical_ratings.md) · BRef ID: `{{BBR_ID}}`.

## Changes and coaching notes

<!-- First entry: a supported change since the prior profile, or “No material change established.” Later entries: dated findings, with source references. Record small samples as observations, not established development. -->

| Date | Finding and effect on role or grade | Evidence |
| --- | --- | --- |
| {{DATE}} | {{CHANGE_OR_NO_MATERIAL_CHANGE}} | {{SOURCE_OR_GAME_REFERENCE}} |

## Sources and uncertainty

- **Assessment evidence:** {{SOURCE_LINKS_OR_DATED_FILM_AND_COACHING_REFERENCES}}
- **Not yet established:** {{SPECIFIC_QUESTION_OR_MISSING_EVIDENCE}}

<!-- yearly-statistics:start -->

## Regular-season statistics by year

G and GS are counts. MIN and all other counting statistics are per game. Percentages use total makes divided by total attempts. Use the same basis in the detail table.

**Coverage:** {{COMPLETED_SEASONS_AND_CURRENT_SEASON_THROUGH_DATE_OR_ANY_PARTIAL_DATA}}

| Season | Team(s) | G | GS | MIN | PTS | REB | AST | STL | BLK | TOV | FG% | 3P% | FT% |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| {{SEASON}} | {{TEAM}} | {{G}} | {{GS}} | {{MIN}} | {{PTS}} | {{REB}} | {{AST}} | {{STL}} | {{BLK}} | {{TOV}} | {{FG_PCT}} | {{THREE_PCT}} | {{FT_PCT}} |

### Additional statistics

<!-- Optional: retain when populated. One row per season, matching the main table. +/- is average point differential while the player is on court per game. -->

| Season | FGM | FGA | 3PM | 3PA | FTM | FTA | ORB | DRB | PF | +/- |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| {{SEASON}} | {{FGM}} | {{FGA}} | {{THREE_PM}} | {{THREE_PA}} | {{FTM}} | {{FTA}} | {{ORB}} | {{DRB}} | {{PF}} | {{PLUS_MINUS}} |

Source: {{REGULAR_SEASON_STATS_SOURCE}}.

<!-- List seasons oldest to newest. Combine traded-team stints into one full-season row and list all teams. Do not count combined rows and team splits twice. Identify partial or unavailable seasons in Coverage. -->

## Playoff statistics by year

Use the same units as the regular-season tables. Keep playoff results separate.

**Coverage:** {{COMPLETED_PLAYOFFS_AND_CURRENT_PLAYOFFS_THROUGH_DATE_OR_NO_APPEARANCES}}

| Season | Team(s) | G | GS | MIN | PTS | REB | AST | STL | BLK | TOV | FG% | 3P% | FT% |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| {{SEASON}} | {{TEAM}} | {{G}} | {{GS}} | {{MIN}} | {{PTS}} | {{REB}} | {{AST}} | {{STL}} | {{BLK}} | {{TOV}} | {{FG_PCT}} | {{THREE_PCT}} | {{FT_PCT}} |

### Additional statistics

<!-- Optional: retain when populated. If the player has no playoff appearances, keep this section heading, state “No playoff appearances,” and omit its tables. -->

| Season | FGM | FGA | 3PM | 3PA | FTM | FTA | ORB | DRB | PF | +/- |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| {{SEASON}} | {{FGM}} | {{FGA}} | {{THREE_PM}} | {{THREE_PA}} | {{FTM}} | {{FTA}} | {{ORB}} | {{DRB}} | {{PF}} | {{PLUS_MINUS}} |

Source: {{PLAYOFF_STATS_SOURCE}}.

<!-- yearly-statistics:end -->

## Awards and honors

<!-- Always last. List confirmed honors through the record update date, oldest to newest. Include award wins, All-League/All-NBA, All-Defense, All-Rookie and All-Star selections, championships, and statistical titles when applicable. Name the league or competition. Label voting finishes as voting finishes, not wins. If none are verified, state “No verified awards or honors.” Do not add empty categories or projected awards. -->

| Season / year | Award or honor | Source |
| --- | --- | --- |
| {{SEASON_OR_YEAR}} | {{LEAGUE_AWARD_AND_TEAM_OR_VOTING_DETAIL}} | {{AWARD_SOURCE}} |
