# historical reference

The index checks championship positions and incoming moves against Lumbra batches. [Sources, hashes, and licences](../../data/master_database_sources.csv) are recorded per batch. Online and correspondence records are excluded where identified; strengths and time controls remain mixed.

Games with title labels and championship players, identical scores, and close variants are [held out](../../data/master_reference_exclusions.csv), then audited championship games enter after their round. Identical scores need matching players below 40 plies. For targets of at least 40 plies, close variants need the same players and endpoint, at least 70% of the target's positions, and a length difference within four plies or 10%.

Position identity includes side to move, castling, and legal en passant rights. Games without a departure remain censored; medians and quartiles require agreeing bounds.

From the repository root, with the Python requirements installed, Rust 1.90, and `bsdtar` available:

```sh
CARGO_TARGET_DIR=.venv/master-index-build cargo build --release --manifest-path scripts/master_index/Cargo.toml
.venv/bin/python scripts/build_master_reference.py
.venv/bin/python scripts/resolve_game_dates.py
.venv/bin/python scripts/master_novelty.py
.venv/bin/python scripts/sample_master_reference.py
.venv/bin/python scripts/novelty_trend_tests.py
.venv/bin/python scripts/plot_novelty.py
.venv/bin/python scripts/check_reference.py
```

The lowest 10,000 random priorities per year retain the lowest 10,000 of any earlier-year union. Ten disjoint samples of 1,000 records measure archive-sampling variation; they are not independent histories.

Yearly medians are regressed on calendar year, with a two-sided zero-slope test. [Calendar HAC](https://www.federalreserve.gov/pubs/ifdp/2012/1060/ifdp1060.htm) uses a ten-year window, checked at five and twenty years. The full-minus-fixed comparison is paired; results since 1972 are exploratory.

Compressed batches are deleted after indexing. `.venv/master-reference` keeps the index and sampled records; hashes tie them to the source archives, targets, and native binary.
