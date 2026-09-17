# Player universe — IPL 2026 season (current as of Sep 2026)

`seed_players_universe.json` is the canonical player pool for the app: 129 real
players across all 10 franchises, reflecting post-Dec-2025-mini-auction squads
for the IPL 2026 season (retentions, trades, auction buys, releases;
cross-checked vs iplt20.com, ESPNcricinfo, Cricbuzz, and Sportradar IPL 2026
match rosters). Supersedes the stale `seed_players_64.json` /
`seed_players_extra.json` one-off demo seeds (which contained retired players
and outdated team assignments).

## `pred` methodology

`pred` is a projected fantasy-points-per-season figure under the app's standard
T20 scoring: carried over from the previous pool where the player matched by
name; new players assigned tier-based estimates (elite 85–96, strong starters
70–85, regulars 60–70, reserves 50–60) from 2025–26 IPL performance and role.

## Name format

Repo `X Surname` convention (single first initial; `MS Dhoni` / `B S Sudharsan`
keep their familiar double initials). Three collisions disambiguated by giving
the less-capped player his full first name: `Ashutosh Sharma` (DC, vs Abhishek
`A Sharma` SRH), `Suyash Sharma` (RCB, vs Sandeep `S Sharma` RR),
`Sarfaraz Khan` (CSK, vs Shahrukh `S Khan` GT).

## Retired / excluded

Excluded from the pool: D Karthik (ret. Jun 2024), S Dhawan (Aug 2024),
W Saha (Feb 2025), P Chawla (Jun 2025), R Ashwin IPL (Aug 2025),
A Russell IPL (Nov 2025), F du Plessis IPL opt-out (Nov 2025).
Not retired — kept: MS Dhoni (CSK, active), G Maxwell (ODI-only retirement),
N Pooran & H Klaasen (international-only retirements), D Warner / T Boult /
T Southee (international-only; Boult plays IPL for MI).

## Notable team moves captured

S Samson RR→CSK; R Jadeja + S Curran CSK→RR; Q de Kock KKR→MI;
M Pathirana CSK→KKR; L Livingstone RCB→SRH; S Thakur LSG→MI (trade);
M Shami SRH→LSG (trade); A Tendulkar MI→LSG (trade); N Rana RR→DC (trade);
S Iyer KKR→PBKS (2025); R Pant DC→LSG (2025); J Buttler RR→GT (2025);
J Inglis PBKS→LSG; V Iyer KKR→RCB; M Markande KKR→MI (trade);
W Hasaranga RR→LSG; L Ngidi RCB→DC; A Nortje KKR→LSG; R Bishnoi →RR.
D Miller verified at DC (not LSG) via IPL 2026 match rosters.
