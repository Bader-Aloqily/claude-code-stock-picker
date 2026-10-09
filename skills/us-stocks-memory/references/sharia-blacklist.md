# US Sharia Business-Activity Blacklist (Single-Layer)

> Best-effort business-activity screen for the `/us-picks` system. This is **NOT** a certified Sharia advisory service. It blocks tickers whose core business clearly conflicts with the screened categories below.
>
> **Categories blocked (6):**
> 1. Defense / weapons
> 2. Casinos / gambling / sports betting
> 3. Alcohol
> 4. Tobacco / recreational cannabis
> 5. Adult entertainment
> 6. Pork-heavy food processors
>
> **⚠️ 2026-07-08 (user-directed) — the Al Rajhi financial-ratio screen was REMOVED; this file is once again the WHOLE `/us-picks` Sharia screen (single-layer).** From 2026-06-18 to 2026-07-08, `/us-picks` also applied Al Rajhi criteria #2–#3 (debt/market-cap < 30% + interest-income/revenue < 5%, computed in code by the now-removed `uspicks_data.alrajhi_screen`); that financial-ratio screen was removed 2026-07-08 per user direction, so `/us-picks` Sharia = this business-activity blacklist ONLY. Conventional financials (banks/insurers/lenders) and cash-rich names are **eligible again** (consistent with the 2026-06-05 change below). _(Reversal: re-add the ratio screen via a structured amendment; the removed screen code is recoverable from git history.)_
>
> **⚠️ INTEREST-BASED CATEGORIES NOT SCREENED (since 2026-06-05).** The seven interest-based categories that this file used to carry were **removed**: conventional banks, conventional insurers, mortgage REITs (mREITs), Business Development Companies (BDCs), consumer/payday/subprime/specialty lenders, fintech lenders, and crypto exchanges/brokerages with material interest revenue (~210 tickers). As a result, **this screen no longer excludes interest-based businesses** — conventional banks, insurers, and lenders are now *eligible* picks. **NOTE:** this **departs from mainstream Islamic equity screens** (AAOIFI / DJIM / S&P Sharia / MSCI Islamic), all of which exclude conventional banks/insurers/lenders as core-riba businesses. The screen now covers only the six non-financial product/vice categories above. The removed tickers remain recoverable from git history if the user reverts this decision.
>
> **Financial-ratio screens — history (none active now).** The AAOIFI Standard #21 screen (debt<33% / cash+IBS<33% / interest<5%) was wired 2026-05-13 and retired 2026-05-25 (v4.8). The Al Rajhi screen (debt<30% + interest<5%) was wired 2026-06-18 (v5.1) and **removed 2026-07-08** (per the note above). Between those windows, and again since 2026-07-08, `/us-picks` Sharia compliance is single-layer — this business-activity blacklist only. (Historical note: the riba *business-activity* categories survived the v4.8 retirement and were removed 2026-06-05.)
>
> **How it's used:** Phase 3.5 of `/us-picks` removes any ticker in this file before ranking. Applies to final picks AND runners-up. Since the 2026-06-05 change — and with the Al Rajhi ratio screen removed 2026-07-08 — interest-based businesses (conventional banks / insurers / lenders) are **not screened**; only the six vice categories below are.
>
> **How to edit:** Add/remove tickers freely. One ticker per line in each category. Comments after `#` are ignored by the matcher (matching is case-insensitive, ticker-exact).
>
> **Contested categories:** If unsure, include it — the cost of a false positive is losing one candidate. The cost of a false negative is holding a stock the user considers non-compliant.

---

## Category 1: Defense / Weapons

```
LMT     # Lockheed Martin
RTX     # RTX Corp (Raytheon)
NOC     # Northrop Grumman
GD      # General Dynamics
LHX     # L3Harris Technologies
HII     # Huntington Ingalls (naval warships)
BWXT    # BWX Technologies (naval nuclear propulsion)
TXT     # Textron (Bell helicopters, defense)
LDOS    # Leidos (defense IT)
KBR     # KBR Inc (defense services)
HEI     # HEICO (defense aerospace parts)
HEI-A   # HEICO Class A (same defense-aerospace business as HEI; separate ticker) — added 2026-05-31
TDG     # TransDigm (defense aerospace)
CW      # Curtiss-Wright (defense)
MRCY    # Mercury Systems (defense electronics)
AXON    # Axon Enterprise (tasers, police tech)
KTOS    # Kratos Defense
BA      # Boeing (large defense segment — contested but typically excluded)
CACI    # CACI International (defense IT)
SAIC    # Science Applications International
BAH     # Booz Allen Hamilton (defense consulting)
V2X     # V2X Inc (defense services)
VSE     # VSE Corp (defense logistics)
OSK     # Oshkosh (military vehicles)
AVAV    # AeroVironment (military drones)
ESLT    # Elbit Systems (ADR, defense electronics)
BAESY   # BAE Systems (ADR)
RHM     # Rheinmetall (ADR, defense)
TGI     # Triumph Group (defense aerospace)
DRS     # Leonardo DRS (defense electronics)
ATRO    # Astronics
ONDS    # Ondas Holdings (defense-ISR drones / ground robotics; defense-ministry customer; border-security & demining contracts) — added 2026-05-17
VOYG    # Voyager Technologies (Defense & National Security segment per public 10-K — DoD missile-defense / hypersonic-propulsion contracts) — added 2026-05-25
RCAT    # Red Cat Holdings (military/tactical drone manufacturer — US Army SRR program, Teal Drones defense subsidiary) — added 2026-05-31
RGR     # Sturm, Ruger & Co (firearms) — added 2026-07-08
SWBI    # Smith & Wesson Brands (firearms) — added 2026-07-08
POWW    # Outdoor Holding Co (fka AMMO Inc — ammunition + GunBroker) — added 2026-07-08
AMTM    # Amentum Holdings (defense/intel govt services) — added 2026-07-08
KRMN    # Karman Holdings (missile-defense / hypersonic / space-defense) — added 2026-07-08
CVU     # CPI Aerostructures (military aircraft structures) — added 2026-07-08
OLN     # Olin Corp (Winchester ammunition — contested: ~25% ammo) — added 2026-07-08
MOG-A   # Moog Inc Cl A (defense/space + military aircraft — contested: segment) — added 2026-07-08
PSN     # Parsons Corp (defense/intel/cyber federal — contested: segment) — added 2026-07-08
RKLB    # Rocket Lab (space launch; national-security book — contested) — added 2026-07-08
SPCX    # Space Exploration Technologies / SpaceX (Starshield military satellites + DoD launch — contested: segment; NDX member) — added 2026-07-23 (v5.5 universe widening, consistency with RKLB/PLTR)
FLY     # Firefly Aerospace (space/defense launch — contested) — added 2026-07-08
RDW     # Redwire (space infrastructure/defense — contested) — added 2026-07-08
PLTR    # Palantir Technologies (defense/intel software — contested: segment) — added 2026-07-08
LASR    # nLIGHT (lasers — majority-defense directed-energy business; caught 2026-07-13 scoring #9 on a military laser-weapon [JLWS] award; the file's "if unsure, include it" rule) — added 2026-07-13
```

## Category 2: Casinos / Gambling

```
WYNN    # Wynn Resorts
MGM     # MGM Resorts
LVS     # Las Vegas Sands
CZR     # Caesars Entertainment
PENN    # Penn Entertainment
BYD     # Boyd Gaming
RRR     # Red Rock Resorts
MCRI    # Monarch Casino
GDEN    # Golden Entertainment
CHDN    # Churchill Downs (horse racing / gambling)
DKNG    # DraftKings
FLUT    # Flutter Entertainment
IGT     # International Game Technology
LNW     # Light & Wonder (was SGMS — Nasdaq ticker changed SGMS->LNW in 2022)
ACEL    # Accel Entertainment
MLCO    # Melco Resorts
BALY    # Bally's
RSI     # Rush Street Interactive (online casino/sports betting)
GENI    # Genius Sports (sports betting data/B2B)
SRAD    # Sportradar (sports betting data)
EVRI    # Everi Holdings (casino tech)
INSE    # Inspired Entertainment (gaming tech)
FLL     # Full House Resorts
PLTM    # Playtika (social casino)
PLTK    # Playtika alternate
LOTO    # Lottery.com
GAMB    # Gambling.com
SGHC    # Super Group (Betway operator) — online gambling — added 2026-05-25
CNTY    # Century Casinos (casino operator) — added 2026-07-08
BRAG    # Bragg Gaming (B2B iGaming) — added 2026-07-08
GMGI    # Golden Matrix Group (iGaming platform) — added 2026-07-08
CDRO    # Codere Online (online casino / sports betting) — added 2026-07-08
VICI    # VICI Properties (casino REIT — landlord; contested: REIT) — added 2026-07-08
GLPI    # Gaming and Leisure Properties (casino REIT — landlord; contested: REIT) — added 2026-07-08
```

## Category 3: Alcohol

```
STZ     # Constellation Brands
BUD     # Anheuser-Busch InBev
DEO     # Diageo
TAP     # Molson Coors
SAM     # Boston Beer
BF-A    # Brown-Forman A
BF-B    # Brown-Forman B
ABEV    # Ambev SA (LatAm brewer, ADR) — added 2026-07-08
MGPI    # MGP Ingredients (distilled spirits ~77% of sales) — added 2026-07-08
WVVI    # Willamette Valley Vineyards (winery) — added 2026-07-08
CCU     # Compania Cervecerias Unidas (Chile beer/wine/spirits — contested) — added 2026-07-08
```

## Category 4: Tobacco / Recreational Cannabis

```
MO      # Altria
PM      # Philip Morris International
BTI     # British American Tobacco
IMBBY   # Imperial Brands
VGR     # Vector Group
TPB     # Turning Point Brands
TLRY    # Tilray
CGC     # Canopy Growth
ACB     # Aurora Cannabis
CRON    # Cronos Group
SNDL    # SNDL Inc (formerly Sundial)
GRWG    # GrowGeneration
MSOS    # AdvisorShares MSO ETF
XXII    # 22nd Century Group (reduced-nicotine tobacco) — added 2026-07-08
UVV     # Universal Corp (leaf tobacco) — added 2026-07-08
RLX     # RLX Technology (e-cigarette/vapor, China ADR) — added 2026-07-08
IIPR    # Innovative Industrial Properties (cannabis REIT — landlord; contested: REIT) — added 2026-07-08
VFF     # Village Farms International (cannabis) — added 2026-07-08
```

## Category 5: Adult Entertainment

```
RICK    # RCI Hospitality (gentlemen's clubs)
PLBY    # PLBY Group (Playboy)
```

## Category 6: Pork-Heavy Food Processors

```
HRL     # Hormel Foods (Spam, pork-major)
TSN     # Tyson Foods (large pork segment)
SFD     # Smithfield Foods (largest US pork processor; relisted 2025) — added 2026-07-08
JBS     # JBS N.V. (global animal protein incl. pork — contested: segment) — added 2026-07-08
SEB     # Seaboard Corp (pork among 6 segments — contested: segment) — added 2026-07-08
BRFS    # BRF SA (poultry+pork, Brazil ADR — contested: segment) — added 2026-07-08
```

---

## Notes on Contested Categories (NOT hard-blocked by default)

- **Interest-based businesses (banks, insurers, mREITs, BDCs, lenders, crypto exchanges):** As of 2026-06-05 these are **NOT blocked** (not part of this business-activity list — see header). This screen no longer evaluates interest/riba or financial structure at all. To re-block them, restore the categories from git history.
- **REITs:** Not excluded by this screen.
- **Bitcoin miners (MARA, RIOT, HUT, etc.):** Crypto's status is contested among scholars; this list does not block it.
- **Conventional payment networks (V, MA):** Not blocked. Kept in.
- **Hotels without casinos (MAR, HLT, H):** Pass the business screen even though many serve alcohol. Contested; kept in.
- **Entertainment (DIS, NFLX, WBD):** Pass the business screen. Content concerns are personal, not systematic. Kept in.
- **Large conglomerates (GE, HON, MMM):** May have small defense segments. The primary business (aerospace + healthcare + industrial / automation + diversified industrial) keeps them in the pickable universe — defense is a segment, not the core business activity. If you assess any of them as having a too-material defense segment, add to Category 1 manually.

If you want any of these contested categories hard-blocked, add the tickers to the relevant section above.
