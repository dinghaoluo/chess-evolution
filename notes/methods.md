# methods and reproduction

## inputs and versions

`data/curated/` holds reviewed inputs, and readers write tables to `data/derived/`; analysis configurations record input and output SHA-256 fingerprints. Panel JSON files retain interpretation limits, with coverage and methods in the corresponding notes.

Downloaded papers, games, and builds remain under the ignored `cache` link to `~/Library/Caches/chess-evolution`, outside iCloud. The [literature catalogue](../data/curated/literature_catalogue.json) records versions and hashes: Agarwal's July 2023 original and August 2026 revision are separate copies; Choi's v2 is dated January 2025. Local availability does not establish redistribution rights.

The 2005 ChessBase CBV requires cbvault 0.1.4 at `cache/cbvault/bin/cbvault`: its old 149-byte directory entries are expanded to the converter's 173-byte form, preserving compressed members. Both archive and resulting PGN have curated hashes; other readers use zipped PGNs directly. No redistribution licence was identified for the ChessBase archives. Michael Jansen's Lumbra database is CC BY-NC 4.0; its separately licensed Lichess collection is a different input.

## games and clocks

PAL/CSS cumulative elapsed time sums available `%emt` values; after missing time it is a lower bound, making reconstructed remaining time an upper bound. Remaining time equals starting time plus earned increments minus elapsed time; Dobrov's missing value occurs at 15...Kh8. Tiebreak clocks and the fourth edition's unresolved increment remain blank.

A substantial PAL/CSS pause uses 5% of starting time, with 2.5% and 10% sensitivity checks; classical cases use five minutes. Games ending before a qualifying pause are censored, and earlier missing times are flagged; Nielsen's account demonstrates why the pause cannot establish where preparation ended.

The Lichess broadcast reader requires classical time controls and a unique round within each match: eleven rounds in 2021, fourteen in 2023 and 2024. Broadcast main lines and results lack an independent score join; these cases compare recorded time with preparation accounts, without the retired four-mistake engine check.

## engine comparisons

Fruit 2.1 and Stockfish 4/8/12/13/14/15/16 are built from frozen sources; the existing official SF17.1 binary supplies the modern reference. Build records include compiler commands, source and binary hashes, options, patches, and networks. These are macOS arm64 builds with `clang++`, without cross-platform equivalence; SF1.0 repeatedly crashed on selected positions and remains excluded.

Official bench signatures match for SF4/8/12/13/14/15/16. Fruit's 67 unpatched mirror source files match Debian's original DFSG source after newline normalisation; signature authentication was not completed. Fruit ignores its parsed node limit, so a patch stops at the existing search-check cadence and records overshoot; it also ignores root restrictions: nonselection is observed, but the candidate gap remains unknown. Fruit's June 2005 release postdates the main event, whose winners principally used Shredder 8 and Fritz 8.

Each comparison starts a fresh process with the game's move history, one thread where supported, books disabled, and zero contempt where available, with SF12 analysis contempt disabled. The eighteen selected positions use 250,000, one million, and four million requested nodes; the Nielsen extension adds SF13–16 under the same rules. Equal nodes do not mean equal time or playing strength. The first tested release to select a move does not date when that move first became discoverable.

An unrestricted single-PV search supplies each release's preferred move; fresh restricted searches score an unselected played move and the recommendation separately. The signed gap is recommendation minus played score from the mover's perspective: absolute finite gaps within twenty centipawns are near-equal, larger positive gaps are rejections, and larger negative gaps are search reversals. Ten- and thirty-centipawn summaries are retained. Mate scores keep their own ordering and are not converted to centipawns.

Modern shared-root searches retain the last complete exact MultiPV cycle, with distinct moves at equal depth and variation count capped by legal roots; a search without a complete cycle fails. The turning-point screen selects three apparent deteriorations per side in each annotated game; comparisons at larger budgets remain finite estimates, with histories, scores, WDL, nodes, depth, and PV saved for replay.

Reuse options check input, output, binary, and option fingerprints before accepting saved unrestricted selections; candidate searches run afresh unless summary-only mode is selected. Repeatability checks compare two fresh runs of one saved position per build at 250,000 nodes: they distinguish identical searches from identical move/score results, establishing repetition for those searches only.

The retained time scenarios multiply move times by 10,000 or 100,000 nominal nodes per second; two missing move times stay missing. These files are labelled uncalibrated and excluded from the essay: no measured 2005 speed accounts for preparation, pondering, or multiple PCs.

## participation and outcomes

The rating analysis selects one January list per year, using OlimpBase through 2001 and FIDE afterwards; 2250 is the conservative common floor for listed-entry comparisons. January 1971 is unofficial and excluded, 1972–74 are gaps, and 2002 total-membership coverage is unresolved. The 1975 text has 1,534 entries against its summary's 1,543; 2011's stale `Nov10` header is retained, with three leading ratings checked against FIDE's January announcement.

Active counts use absence of the inactive flag from 2000 onwards, with thresholds 2000/2250/2400 counted separately; these are entries at nominal ratings, without a constant-skill interpretation. The 2008–09 identity bridge excludes every duplicated ID from both editions, preventing arbitrary choice between conflicting rows. Nine IDs are duplicated in 2008; none reaches 2250 in 2008; each bridge partitions the original eligible identities into retained, newly inactive, missing, or still-active-below-threshold groups; gains reconcile the following total.

The activity-rule ledger leaves the pre-July-2009 window unverified: January 2009's drop precedes the July changes documented in the November 2008 minutes. COVID extends inactivity from twelve to twenty-four months for November 2020–December 2022; January 2023 returns to twelve. Floor-source conflicts and March 2024 remain annotated; the one-off March formula directly changes only ratings below 2000.

Title awards for 2005–10 are transcribed from FIDE's 2011 statistics, pp. 1–3, and include CM/WCM; one person can receive multiple awards. Living titled players cannot be identified from these lists. Lichess's separate series sums twelve monthly standard-rated export counts per complete year: 'standard' identifies the variant, including fast time controls. No game archive is downloaded for that count, and no rapid-specific growth series is verified.

ICCF outcome labels combine official scores with Edwards's reported circumstances, preserving thirteen batch resignations and the contested resignation separately; formal termination codes and independent resolution of the contested game remain unavailable; the two grids each contain 136 squares, with two board-result labels that do not establish an unconditional upper bound on wins through play. TWIC's 2014 headers establish results and account names, without complete live-assistance classifications.

## capped learning pilot

Six Lumbra batches were re-downloaded against archived hashes; old ordinal exclusions are not reused. The old non-OTB filter did not establish classical play, and its championship-copy exclusions served a different population; new eligibility checks require legal completed main lines, standard starts, compatible event dates, and duplicate/conflict review; independent score and participant matches govern the verified-event pool. Pan-Pacific classical status uses Schiller's contemporary reports, but its player ratings and scores lack the independent reconciliation required for revised advice.

The pilot samples mover PGN Elo at game time in bands 2200–2399, 2400–2599, and 2600+, capped at fifty player-games per year/band and one per player-year; hash ordering with seed 20261016 fixes selection; IDs or full normalised names govern the cap, with remaining spelling ambiguity recorded. Sampled players alone join to the nearest January list: 234/252 match identities and 219/252 provide birth years, with boundary ages and list distance recorded for sensitivity analysis; no full top-hundred join is attempted.

SF17.1 screens and pairs moves at 25,000 nodes, retaining a presampled 100,000-node stability position per game; primary moves 9–40 and secondary moves 11–60 are inclusive full-move numbers for the mover; WDL expectation is `(wins + draws / 2) / 1000`: signed loss is recommendation minus played expectation, reported loss its nonnegative part, and blunders exceed 0.10; reversals remain recorded. Variance intervals resample player-games and games separately, using 2,000 draws, without estimating a historical improvement effect.

Secondary move accuracy uses `W = 100 / (1 + exp(-0.00368208 * cp))`, then `A = clip(103.1668 * exp(-0.04354 * max(0, W_best - W_played)) - 3.1669, 0, 100)`. Mate proxies are ±100,000 for this formula only; centipawn error denominators exclude mate comparisons; cumulative thresholds are ≥50/100/200 cp, with disjoint bins [50,100), [100,200), and ≥200. Mean move accuracy is an arithmetic mean, distinct from Lichess's full game-score aggregation; fixed nodes, aggregation, and sampling differ from Bilalić's pipeline. OSF calibration waits for maintenance to end.

Corpus expansion stopped with the pilot; its variance alone cannot determine a main learning run. The h/a-pawn detector follows the frozen hypothesis rules, including opportunity denominators and the matched a-pawn control; its restricted-pool counts establish no historical style trend.

## revised advice and noise

The reduced H-D protocol fixes 500 independently selected positions, one per independently verified game, before searches: mover Elo ≥2200, moves 9–40, cycling year, band, move half, and material strata until filled. SF4/8/12/17.1 run at 100,000 nodes; SF17.1 judges distinct recommendations together at the last complete common depth; fifty presampled positions repeat at 400,000 nodes. Agreement intervals resample games, omitting selection and judge uncertainty.

The noise check uses exactly those fifty positions for every comparison: each release's 100k/400k disagreement is computed, then the two endpoint rates are averaged. Between-release disagreement is measured at each common budget; excess disagreement subtracts that mean baseline, with two thousand paired game bootstrap draws, seed 20261016, resampling all terms together. This is a descriptive comparison with budget sensitivity, without an identified correction for measurement error. SF4/SF8's excess interval includes zero.

The original advice protocol's mistaken reason for omitting Fruit was corrected after searching, without changing parameters; the original is retained in `advice_protocol_before_search.json`. Fruit's unrestricted recommendation could be judged by a modern engine, but it was not run in this sample. The 2024-heavy pool supports a finite release comparison, without historical human-learning estimates or an opening-turnover result.

## reproduction and archives

```sh
.venv/bin/python scripts/rating_participation.py
.venv/bin/python scripts/join_pilot_birth_years.py
.venv/bin/python scripts/online_participation.py
.venv/bin/python scripts/run_analysis.py panels check
```

A fresh checkout requires the pinned Python dependencies, cbvault 0.1.4, then `run_analysis.py sources build-engines tables searches` before those commands; the full search stage can take much longer than panel regeneration. The check stage validates histories, clocks, fingerprints, and edge cases; every new render is inspected separately.

Ten panel JSON files feed the two plotting scripts; PNG/SVG hashes are in `research_figures_config.json`. Retired recorded-precedent work is preserved in the hashed `20261016-before-refinement.tar.gz`, with `cache/retired` linked to the separate local archive directory; archive recovery validates original members without renewing their old eligibility classifications; it is excluded from the default runner.

Amended 16 October 2026: newly read literature; methods consolidated from result notes, matched-budget comparisons added, and remaining source ambiguities retained.
