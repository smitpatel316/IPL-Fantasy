# P4-D4 — Full three-way role/team drift audit (report only, NO writes)

**Date:** 2026-10-12 · **Author:** data-coord-p4b · **Status:** for Atlas's decision
**Sources (all read-only):**
- **A — canonical universe:** `data/seed_players_universe.json` on master (129 players)
- **B — Pi demo DB:** `~/ipl-fantasy/data/ipl_fantasy.db` on budupi, read via
  `mode=ro` URI over SSH (122 players, season-2027 `player_roles`)
- **C — sandbox seed:** `api/sandbox.py` `MOCK_SQUADS` on master (48 players)
- **Adjudication aid:** phase-1 role registry (`phase1/player_roles.csv`, season
  2026 rows, Wikipedia personnel-change lists) — used only to say which side of
  a disagreement matches the 2026 squad record, never as a fourth source.

**Reproduce:** `data/audit_drift_p4d4.py --db-json <dump>` (dump = the same
read-only SSH query) or `--db <sqlite path with WAL alongside>`. Raw machine
output regenerates every table below.

## ⚠ Hazard found first: the demo DB lives in its WAL

The Pi DB's main file alone contains **112 players and no `status` column**;
the live view (main + `ipl_fantasy.db-wal`, 4.1 MB, uncheckpointed) has **122
players with `status`**. `ipl_fantasy.db.bak-p4d1d2` (taken 2026-10-12 11:58,
presumably as the pre-migration backup) has the same defect — opened alone it
shows 112/no-status. **Any `cp`-style backup or file copy of this DB silently
captures a stale universe.** Backups/migrations must use `sqlite3 .backup` or
checkpoint (`PRAGMA wal_checkpoint(TRUNCATE)`) first. All numbers below are
from the live (WAL-inclusive) view.

## Headline numbers

| | A universe | B demo DB | C sandbox |
|---|---|---|---|
| players | 129 | 122 (114 active + 8 retired-flagged) | 48 |
| franchises covered | 10 | 10 (skewed: KKR 18, MI 18, RCB 16 … DC 8, LSG 7) | 4 (MI/CSK/RCB/KKR × 12) |
| roles WK/BAT/AR/BOWL | 18/30/35/46 | 19/32/31/40 | 7/12/15/14 |

Exact-name overlaps: A∩B = 77 · A∩C = 48 · B∩C = 36 · A∩B∩C = 36.
DB provenance: ids 1–48 `source=sandbox` (an **old** sandbox seed), ids 49–122
`source=preseason-csv`. The DB was never re-synced to the canonical universe.

## 1. Exact-name field mismatches (the hard errors)

**B vs A: only 4** (role/team/overseas; overseas had **zero** mismatches in
every pairwise comparison):

| player | DB | universe | registry 2026 | verdict |
|---|---|---|---|---|
| S Iyer | AR/PBKS | BAT/PBKS | BAT/PBKS | **DB wrong** → BAT |
| S Dube | BAT/CSK | AR/CSK | AR/CSK | **DB wrong** → AR (sandbox also AR) |
| P Cummins | AR/SRH | BOWL/SRH | AR/SRH | **genuine conflict**: DB+registry AR vs universe BOWL — Atlas/Smit call (frontline bowler who bats; either is defensible, sources must pick one) |
| R Singh | BAT/**RCB**, retired | BAT/KKR | — | **false match — name collision, not drift** (see §2) |

**C vs A: 0 mismatches.** Sandbox is a clean subset of the universe.
**B vs C: 2** — the R Singh collision and S Dube (both above).

## 2. Name-variant / collision pairs (same person, different string — or worse)

| DB row | universe row | evidence | verdict |
|---|---|---|---|
| `R Rinku` id42, BAT/KKR, active, drafted | `R Singh` BAT/KKR | Rinku Singh, KKR BAT in registry 2023–2026; data/README disambiguation convention | Same person under an inverted name form. Rename DB id42 → `R Singh`. |
| `R Singh` id35, BAT/RCB, **retired** | (same string as above) | P4-D2: no R Singh batsman in any RCB squad 2023–2026; unidentified, kept retired | **Collision hazard:** the DB's `R Singh` is NOT Rinku. Any name-keyed sync to the universe would silently merge/conflate these two rows. Resolve together with the id42 rename (keep id35 retired under a distinct label or id-keyed only). |
| `BKG Mendis` id97, **BAT/GT** | `K Mendis` **AR/SRH** | Registry: Kamindu Mendis AR/SRH 2025+2026 | Same person; DB has wrong name form, role AND team → rename + AR + SRH. (Drafted in demo — migrate by id, cf. P4-D1/D2 pattern.) |
| `CV Varun` id103, BOWL/KKR | `V Chakravarthy` BOWL/KKR (= DB id43) | — | Duplicate person inside the DB — **this is P4-D5**, not fixed here. |
| `Suyash Sharma` id34 | `Suyash Sharma` | P4-D2 rename already applied on Pi (DB, universe, sandbox all agree) | ✅ resolved, listed to close the loop |

## 3. Sandbox (C): clean vs universe, stale inside the DB

- C ⊂ A exactly: all 48 sandbox players exist in the universe with identical
  role/team/overseas. **No sandbox.py action needed.**
- But the DB's embedded sandbox seed (ids 1–48) predates the 2026-09-16
  sandbox refresh: only 36 of the current 48 sandbox players are in the DB.
  **12 current-sandbox players missing from DB:** D Brevis, J Bethell,
  J Sharma, K Ahmed, M Henry, M Short, R Chahar, R Powell, R Ravindra,
  R Shepherd, S Thakur, V Iyer (all also in §4).
- DB old-sandbox rows no longer in sandbox.py: D Conway, M Ali, N Dhir,
  A Madhwal, M Bhandage, M Pandey, V Arora, R Rinku (variant, §2) + the
  retired-flagged K Pollard, R Ashwin, A Russell, Mandeep Singh.

## 4. In the universe but missing from the demo DB: 52

Every one is a registry-verified 2026 squad player on the same team in the
universe — the demo pool simply never received them (built from old sandbox +
preseason-csv). Full list (by team): **CSK** D Brevis, K Ahmed, M Henry,
M Short, R Chahar, Sarfaraz Khan · **RCB** J Bethell, J Sharma, R Shepherd,
V Iyer · **KKR** R Powell, R Ravindra · **DC** Ashutosh Sharma, D Miller,
K Jamieson, K Yadav, N Rana, T Natarajan, T Stubbs · **SRH** A Sharma,
A Verma, B Carse, H Patel, J Unadkat, K Mendis (present as variant, §2) ·
**RR** L Pretorius, N Burger, R Bishnoi, S Hetmyer, S Sharma (Sandeep — absent
from DB in any form) · **PBKS** A Singh, L Ferguson, M Jansen, M Owen,
N Wadhera, P Singh, S Singh, X Bartlett, Y Chahal · **GT** G Phillips,
I Sharma, R Tewatia, W Sundar · **LSG** A Khan, A Nortje, D Rathi, M Khan,
M Shami, M Yadav, W Hasaranga.

Registry-vs-universe role notes inside this list (universe may itself want a
look): T Stubbs registry BAT vs universe WK; R Powell registry BAT vs
universe AR; H Patel registry AR vs universe BOWL; Ashutosh Sharma registry
BAT vs universe AR. All four are judgment-call classifications like Cummins.

**Decision for Atlas:** sync the demo pool to the canonical 129 (add the 52,
preserving drafted ids), or formally freeze the demo league's pool as-is.
If syncing, do it id-keyed — the §2 collision makes name-keyed sync unsafe.

## 5. In the demo DB but absent from the universe: 45

### 5a. Retired-flagged (7 of the 45) — by-design keeps, no action
K Pollard, R Ashwin, A Russell, S Dhawan, PP Chawla, KD Karthik,
Mandeep Singh (P4-D2). (The DB's 8th retired row, R Singh id35, is an
exact-name collision — §2 — not a DB-only name.)
All carry `status=retired`, consistent with the IL/eligibility status logic.
(The universe excludes these people entirely; the DB keeps them flagged —
that asymmetry is the demo league's design, already ratified by P4-D2.)

### 5b. Active, real 2026 squad members the universe trimmed (18) — demo depth
Registry 2026 confirms each on the DB's team; role agrees except as noted:
A Kamboj (CSK), A Mhatre (CSK), AM Ghazanfar (MI), B Muzarabani (KKR),
C Bosch (MI), H Brar (PBKS), H Dubey (SRH), JA Duffy (RCB), KR Sen (RR),
N Thushara (RCB), PP Hinge (SRH), RS Ghosh (CSK), S Hussain (SRH),
SR Dubey (KKR — Saurabh Dubey, registry BOWL/KKR exact), V Vinod (PBKS),
Y Thakur (PBKS), plus old-sandbox M Pandey (KKR) and V Arora (KKR).
Verdict: plausible demo-league depth by design — the universe is a trimmed
"fantasy-relevant core" (data/README), the demo pool is deeper. Atlas
decides whether depth stays.

### 5c. Active DB-only with a registry disagreement (3)
- `A Rawat` id118 BAT/GT — registry: Anuj Rawat **WK**/GT → DB role wrong.
- `N Dhir` id11 BAT/MI — registry: Naman Dhir **AR**/MI → DB role wrong.
- `A Madhwal` id12 BOWL/MI — registry 2026: Akash Madhwal BOWL/**CSK** →
  DB team stale.
### 5d. Active DB-only with NO 2026 squad presence (14) — legacy residue
No registry-2026 row and no universe row; all are `status=active` in the DB
and most are drafted in the demo league, so they occupy real demo rosters:
D Conway (WK/CSK — also role: registry last had him BAT, 2025), M Ali
(AR/CSK — his last squad was KKR 2025, so team is stale too), JM Bairstow
(WK/MI — 2025 temporary replacement only), RR Rossouw (BAT/PBKS),
R Gurbaz (WK/KKR), J Little (BOWL/GT), W O'Rourke (BOWL/LSG),
Naveen-ul-Haq (BOWL/LSG), DJ Mitchell (AR/CSK — last squad 2024),
S Atal (BAT/DC), V Kaverappa (BOWL/PBKS), R Salam (BOWL/RCB),
T Kotian (AR/RR), M Bhandage (AR/RCB).
Verdict: candidates to flag `retired`/inactive in the DB (the P4-D2 pattern —
flag, never delete, because draft/roster rows reference them), or keep as
avowed demo-only players. Atlas decides.

### 5e. Covered elsewhere (2)
`CV Varun` id103 → P4-D5 duplicate-person dedup. `BKG Mendis` id97 → §2
variant fix. (`R Rinku` id42, the 38th active DB-only row, is §2 as well:
7 retired + 18 depth + 3 registry-disagreement + 14 legacy + 2 here +
R Rinku = 45.)

## Decision list for Atlas (no writes made by this audit)
1. Fix DB roles: S Iyer AR→BAT, S Dube BAT→AR (§1, clear).
2. Rule on P Cummins: universe BOWL vs DB+registry AR — pick one everywhere.
3. Fix BKG Mendis → K Mendis, BAT/GT → AR/SRH (§2, by-id migration).
4. Rename R Rinku → R Singh and disambiguate retired R Singh id35 (§2)
   BEFORE any name-keyed universe sync.
5. Sync-or-freeze the demo pool vs the missing 52 (§4).
6. Keep-or-trim the §5b depth (18) and §5c fixes (3).
7. Flag-or-keep the §5d legacy actives (14).
8. Adopt WAL-safe backup discipline (header hazard) for all future DB work.
