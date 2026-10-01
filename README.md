# Basketball Player Career Simulation

Player career: **Dwyane Wade**  
Current season: **2003-04**  
Current date: **June 26, 2003**  
Draft team: **Miami Heat, No. 5 overall**

The simulation is centered on Wade as the user-controlled player. Team basketball operations are controlled by the AI/GM.

## Career

```text
career/
  Dwyane_Wade/
    Dwyane_Wade_Player_Profile.md
    2003-04/
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

The June 26 team snapshot intentionally stops at the draft. July free-agency moves, later coaching changes and later cap outcomes are not imported early.

## League source library

Raw league-wide historical datasets live outside the career state:

```text
library/
  2003/
    league/
      nba_2003_end_of_season.json
      nba_2003_draft_class.json
```

The end-of-season file is the pre-offseason league baseline. The draft-class file is the post-draft June 26 rights snapshot. Miami's live team files may derive from these sources, but the full NBA data is not duplicated inside `00_Team`.

Game execution may be performed externally, including Relay. A game becomes canonical only after its result is written into the appropriate career game record and the repository validates.
