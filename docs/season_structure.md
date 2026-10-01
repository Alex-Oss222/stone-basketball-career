# Season structure

The active hierarchy is:

```text
career/Dwyane_Wade/2003-04/
  00_Team/
    Organization/
    Team/
      Roster/
      Depth_Chart/
      Player_Cards/
    Finances/
  01_Free_Agency/
  02_Summer_League/
  03_Offseason/
  04_Training_Camp/
  05_Preseason/
  06_Regular_Season/
  07_Play_In_Tournament/
  08_Playoffs/
  09_Draft/
```

`00_Team` is AI/GM-owned and sits outside the player's phase choices. Organization records only basketball-relevant decision makers. Team owns roster, depth chart and player cards. Finances owns cap and contract-control state.

Actual dates control chronology, so the June 26 draft can close before June 30 free agency even though Draft is folder 09.

Regular-season month weeks remain:
- Week 1: days 1 to 7
- Week 2: days 8 to 14
- Week 3: days 15 to 21
- Week 4: day 22 through month end

Conditional postseason game files are created only when scheduled or explicitly marked not played.
