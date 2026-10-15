# research notes

## 20261014

- the 1972 forfeit even has movetext in the PGN... These files need checking before we treat them as a championship dataset
- fixed the median calculation, but a growing reference also pushes the first unfamiliar position later. Need to separate that from changes in how players prepare
- [the 2005 winners' account](https://en.chessbase.com/post/pal-c-report-from-the-dark-horse-s-mouth/9) describes choices between engine suggestions. Need to see when the humans changed the direction of analysis. Started a Stockfish pilot, though sending positions alone loses repetition history

## 20261015

- the knockout files mix classical games, tiebreaks, and alternative scores. Need to keep those apart before comparing tournaments
- the title-only reference calls 2.Bf4 new... Added [Lumbra](https://lumbrasgigabase.com/en/) for earlier play outside the championships, but found championship copies under wrong players and dates. A larger database needs checking too; try another source before trusting the historical curve
- most of the long-run rise disappears when the reference size is fixed. How much of the plot is just the history of what was collected? The recent decline also needs explaining
- the [Go paper](https://doi.org/10.1073/pnas.2214840120) counts earlier departures as more novelty. We are asking how long players follow recorded precedent; calling the result 'novelty' makes the direction confusing
- [FIDE's 7.Re1](https://www.fide.com/world-championship-game-7-ding-liren-escapes-by-the-skin-of-his-teeth/) reaches an already recorded position through a different move order. Is a new move or a new position a better proxy for where preparation ends? [Chassy and Gobet](https://doi.org/10.1371/journal.pone.0026692) include analysed moves too, which our game records miss
- in the winners' annotated games, the humans were revising preparation, choosing plans, and judging opponents. The Rentner account disagrees with the game score, though, so we need to check their explanations against the moves
- full histories are now restored in the pilot, but Stockfish still switches between Qe3 and h3 as we add search. How stable does that comparison need to be before calling the human choice an improvement?
