# learning variance pilot

The pilot scored 252 player-games from 229 games, leaving 251 primary-window observations; shortages against the frozen target of 750 prevent a historical learning comparison.

Stockfish 17.1 screened 8,538 decisions at 25,000 nodes. The 2024 strata each contain fifty player-games; their variation gives a methods result conditional on the Olympiad sample:

| mover PGN Elo | SD of mean expected-score loss | 95% game-bootstrap interval |
|---|---:|---:|
| 2200–2399 | 0.0210 | 0.0159–0.0267 |
| 2400–2599 | 0.0153 | 0.0122–0.0181 |
| 2600+ | 0.0158 | 0.0116–0.0191 |

At one presampled position per game, recommendations agree across 25k/100k budgets in 185/229 cases (80.8%); absolute loss changes exceed 0.02 in 33 and 0.05 in seventeen. The 95th-percentile change is 0.0833; measured worker time was 465 seconds across three workers.

The birth-year join matched 234/252 identities and supplied 219 usable birth years; four of fifteen strata cannot estimate variance. Twenty-five PGN ratings conflict with event records, and the 1995 intermediate-band variance depends on the independently unverified Waitzkin–Xie Jun score. Main sizes and budgets remain unfrozen: the pilot cannot support a band-gap curve or age effect, and corpus expansion stopped here.

[Variance table](../data/derived/learning_pilot_variance.csv); [coverage](../data/derived/learning_pilot_coverage.csv); [search hashes](../data/derived/learning_pilot_scoring_config.json). Windows and metric definitions are in [methods](methods.md#capped-learning-pilot).

Amended 16 October 2026: newly read literature; pilot retained as a methods note.
