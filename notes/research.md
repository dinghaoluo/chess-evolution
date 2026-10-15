# research notes

## 20261014

- went through the championship files and checked which games belong in the analyses. The event choices are in [events.csv](../data/events.csv), and the decisions for each game are in [game_classifications.csv](../data/game_classifications.csv)
- the 1972 forfeit even has a move in the PGN... Excluded that record and the 2006 forfeit; 1975 stays as an event without games, and the 1909 Lasker-Janowski match stays outside the title series
- the 2002 FIDE file mixes in 26 games from the [women's championship](https://www.olimpbase.org/~B-FISH/ind-wwcc/wwc2001-wch.html), and the remaining open games are 16 short of [FIDE's match results](https://www.fide.com/images/stories/fide_history/2001_Moscow.htm). The missing counts are in [fide_2002_matches.csv](../data/fide_2002_matches.csv). Still need to sort out the classical and tiebreak games in the 1998, 2000, 2002, and 2004 files
- saved hashes of the current local files in [source_manifest.csv](../data/source_manifest.csv), including the earlier 2018 and 2023 repairs. Tried downloading again but got HTTP 465
- reran novelty on 1,042 played classical games from the main title line. Some dates are incomplete, so the comparison now uses earlier events only
- the plot was also taking the upper middle value for even-sized samples, so corrected that to the arithmetic median. A growing archive gives each game more earlier positions to match against; sampled 100 earlier games at a time to check this. The slope falls from 4.86 to 1.80 plies per century on the same years.
- started with seven positions from [Stephen and Cramton's account](https://en.chessbase.com/post/pal-c-report-from-the-dark-horse-s-mouth/9) of the 2005 PAL/CSS tournament. At 18.Qf4 they revised their preparation; at 23.Qe3 they chose a move over the engines' reported preference for h3.
- ran Stockfish 17.1 on the first and last classical games of the 1984, 2000, 2008, and 2023 matches. [stockfish_config.json](../data/stockfish_config.json) records the engine settings. More search changed the first choice in 9 of 69 sampled championship positions, and at 23.Qe3 it changed from h3 to Qe3. The current input loses repetition history because it uses FENs
