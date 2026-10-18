# research notes

The recorded-precedent files mentioned below are preserved in the local archive described in [methods](methods.md).

## 20261014

- the 1972 forfeit even has movetext in the PGN... These files need checking before we treat them as a championship dataset
- fixed the median calculation, but a growing reference also pushes the first unfamiliar position later. Need to separate that from changes in how players prepare
- [the 2005 winners' account](https://en.chessbase.com/post/pal-c-report-from-the-dark-horse-s-mouth/9) describes choices between engine suggestions. Need to see when the humans changed the direction of analysis. Started a Stockfish pilot, though sending positions alone loses repetition history

## 20261015

- the knockout files mix classical games, tiebreaks, and alternative scores. Need to keep those apart before comparing tournaments
- the title-only reference calls 2.Bf4 new... Added [Lumbra](https://lumbrasgigabase.com/en/) for earlier play outside the championships, but found championship copies under wrong players and dates. A larger database needs checking too; try another source before trusting the historical curve
- most of the long-run rise disappears when the reference size is fixed. How much of the plot is just the history of what was collected? The decline since 2000 persists across the reference checks, including when the 2024 match is left out. Earlier departures could still be prepared lines that have never been played
- the [Go paper](https://doi.org/10.1073/pnas.2214840120) counts earlier departures as more novelty. We are asking how long players follow recorded precedent; calling the result 'novelty' makes the direction confusing
- [FIDE's 7.Re1](https://www.fide.com/world-championship-game-7-ding-liren-escapes-by-the-skin-of-his-teeth/) reaches an already recorded position through a different move order. Is a new move or a new position a better proxy for where preparation ends? [Chassy and Gobet](https://doi.org/10.1371/journal.pone.0026692) include analysed moves too, which our game records miss
- in the winners' annotated games, the humans were revising preparation, choosing plans, and judging opponents. The Rentner account disagrees with the game score, though, so we need to check their explanations against the moves
- found a separate [archive with move times](https://en.chessbase.com/post/dark-horse-zacks-wins-freestyle-che-tournament). Their preparation was saving time for later decisions, though the override of h3 still looks unconvincing in modern paired searches. Wrote up the [three annotated games](pal-css-2005.md)
- Lichess confirms the Re1 transposition; [TWIC](https://theweekinchess.com/chessnews/events/51st-groningen-chess-festival-2013) adds the next position in a lower-rated game. Masters also contains [ICCF games](https://lichess.org/mb7iq8TJ/black). Whose body of knowledge should our 'novelty' measure approximate?
- [Krakowski, Luger, and Raisch (2023)](https://doi.org/10.1002/smj.3387) found that earlier assisted-play results predicted later wins when conventional ratings did not. Their 'human–machine capability' measure comes from past results, though, so the paper leaves the decisions behind those results unexplained
- [Vaccaro et al. (2024)](https://www.nature.com/articles/s41562-024-02024-1) found that assisted humans improved on humans alone, but fell below the better partner alone on average. Becca's question would require comparison with the engine alone, using the same preparation and computing resources
- found clocks for the qualifier and main event too. The opening in the final was unusually quick; their other games involved much earlier thinking
- Nielsen spent seventeen minutes checking a prepared move in 2007... A first long think is not necessarily the end of preparation. [Later cases](preparation-and-clocks.md)
- two moves that Nielsen said engines struggled with are now Stockfish's first choices. Need to describe human advantages against the particular engines of the time
- the opening-position check gives no consistent narrowing across years. Later plies barely distinguish tournaments because nearly every game reaches a different position

## 20261016

- the 2005 Hydra scores reproduce 7.5/16, but the two accounts had different modes. Zor_champ was unassisted; Ares01 had human intervention. Opponent modes are incomplete, so this total is against the field
- recovered Nickel's original 2014 report in an [archived copy](https://gwern.net/doc/www/www.infinitychess.com/2e38d048d76721a8837bf0bd309978835692c242.html). Its comparison is interim and colour-imbalanced
- [ICCF's 2024 commissioner report](https://webfiles.iccf.com/congress/2024/reports/ICCF%20-%20Title%20Tournament%20Commissioner%20-%20Report%20-%20Congress%20-%202024.pdf) attributes the ten decisive scores in final 33 to Dronov's death. A raw decisive-game curve would mix chess results with administrative awards
- [Chassy and Gobet's paper](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0026692) is accessible; its theoretical-opening definition includes analysed moves. The recorded-game measure remains a different object
- Fruit accepts a node-limit command without enforcing it. Added a stop guard and retained actual searched nodes; nominal 2005 search speeds still lack a hardware calibration
- the sixteen decisions were chosen from the winners' explanations. Screening both players in the three annotated scores addresses unequal attention within those games; it leaves the selection of games unchanged
- [Shoresh and Loewenstein](https://arxiv.org/abs/2412.18593) use Maia as a human behavioural clone with Leela, then test how well experts recognise relative advantages. The preprint is from 2024; the proceedings paper is from 2025

### learning and the next corpus

- the [source review](learning-evidence.md) identifies direct historical chess studies of engine-benchmarked human play. The proposed learning analysis can extend their populations and budget checks; it is not filling an empty literature
- recorded [hypotheses](hypotheses.md) for quality, differences between populations, pattern adoption, revised engine advice and opening use, and human participation. Historical timing alone does not identify engine exposure, explanation access, or job effects
- restored 59 title PGNs after checking the archive and source-manifest hashes. There are 2,973 source records, including excluded records, with 2,258 previously accepted classical games. The proposed pilot lacks the comparison population; raw Lumbra batches were not preserved, only metadata and position indexes
- Fruit 2.1 also ignores `searchmoves`: the parser calls it a dummy. Keep its candidate gaps unavailable until root restriction is implemented and validated; a UCI command being accepted does not establish that it is enforced

### release checks, participation, and the learning pilot

- read Bilalić et al. and Anicker in full, and Strittmatter et al. in full text with published page references. Added the dated literature amendment without changing the original hypotheses.
- Stockfish 13–16 match their official bench signatures. The two Nielsen moves first match all three tested budgets in SF15 and SF4 respectively; later preference reversals prevent a 'years ahead' claim. Local SF4/8/12 benches also match; 67 unpatched Fruit source files match Debian's original after newline normalisation
- all 17 decisive ICCF final-32 scores now have reported-circumstance labels. Formal termination codes and independent review of the contested resignation remain unavailable. The Williams/Ibermax and Intagrand labels have contemporary sources; the 435 TWIC 2014 headers do not identify every account's live assistance mode
- downloaded 53 January rating snapshots. Listed 2250+ entries grew from 9733 in 1997 to 13344 in 2026, while active entries fell from 9305 in 2007 to 5830 in 2026. That weakens an unqualified claim that all participation kept growing. Separate title-award and living-title gaps remain visible; January 2002 total coverage is unresolved
- the final 2005 Qualification Commission minutes resolve the 1400 floor as January 2006. Added the temporary November 2020–December 2022 activity window and January 2023 reversal; the earlier look-back history and exact 1600-floor date remain incomplete
- six Lumbra downloads match their archived hashes, but the OTB batches contain blitz, correspondence, and computer records. Independent event archives also expose wrong-player copies. The old indexer exclusions and sampling priorities are not reused for learning
- the verified-event pilot supplies 252/750 player-games, with 234 identity matches and 219 usable birth years. At 25k nodes, 44/229 presampled recommendations change at 100k, and 33 losses change by more than 0.02. Sparse early strata, rating conflicts, and one unverified high-variance 1995 score prevent a defensible main sample-size choice; no historical quality result is reported
- the frozen h/a-pawn detector passed ten checks and has counts for the restricted pool. Those counts cannot identify historical pattern adoption or quality improvement. Search-speed scenarios are labelled uncalibrated and excluded from the essay and default run
- removed figure subtitles and explanatory text blocks. Data labels and legends remain; methods, coverage, and source caveats are in notes and panel JSON
- the 500-position H-D comparison gives 52.4% SF4/SF17.1 first-choice agreement (95% game-bootstrap interval 47.8–56.6%). SF4 suggestions exceed 0.02 judged loss in 87/500 positions, while 37 shared-root scores reverse the modern screening ranking. The 400k subset remains sensitive; [the result](revised-advice.md) separates preference, quality estimate, and budget uncertainty

### matched budgets and rating thresholds: 16 October 2026

The matched fifty-position advice check gives within-release agreement of 70%, 70%, 76%, and 84% for SF4/8/12/17.1 across 100k/400k nodes. SF4/SF17.1 disagreement exceeds the mean endpoint budget-disagreement baseline by 25 percentage points (95% paired bootstrap interval 11–39); at 400k the excess is 23 points (10–36). SF4/SF8's interval includes zero. The baseline is descriptive, without an identified measurement-error correction.

Active 2000/2250/2400 counts change by +6.8%, −30.3%, and −7.2% from 2000 to 2026; all three decline from 2010, by 12.1%, 21.2%, and 20.4%. In the 2008–09 bridge, 1,790 formerly active 2250+ identities become inactive, 583 remain active below 2250, and 52 disappear. The January drop precedes the documented July rule changes; its exact implementation remains unresolved. Nine duplicated 2008 IDs are excluded from both sides of the bridge, including one whose 2009 entry reaches 2250; annual counts continue to count entries. Lichess's official monthly index supplies a separate online-game series, without identifying unique people or rapid-specific growth.

Rxb5 already scores near-equal in SF8/SF12 at four million nodes despite being unselected: this prevents calling every early release a rejection. The two ICCF board-result labels also cannot prove an unconditional upper bound while the contested resignation is unresolved. Budzyń's before/after exposure comparison coincides with a screening suspension; Choi's v2 has inconsistent stated regression counts.

The thirteen reading copies include separate versions of Agarwal's July 2023 original and August 2026 revision; Choi's v2 is dated January 2025. The pilot cannot support historical learning estimates, and corpus expansion stopped without another event pass; OSF calibration waits for maintenance to end.

The 2250–2399 band falls from 6,519 active entries in January 2000 to 4,123 in January 2026: its decline of 2,396 accounts for 94.7% of the 2,529-entry decline at 2250+. No explanation has been found; the corresponding share from 2007 is 82.8%, so 'nearly all' is explicitly tied to the 2000 baseline. The participation figure names all three active thresholds and moves its threshold legend below the data; the revised PNG and both accompanying renders were inspected.

## 20261018

- restored the README's original essay questions and analysis sections; the retired recorded-precedent plot now links to the archive description instead of a deleted figure
