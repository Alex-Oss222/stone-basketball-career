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
    Dwyane Wade: Player Profile.md
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

Game execution may be performed externally, including Relay. A game becomes canonical only after its result is written into the appropriate career game record and the repository validates.
