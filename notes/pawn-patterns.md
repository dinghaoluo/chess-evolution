# h-pawn counts in the verified event pool

The frozen detector found 170 h-pawn events and 191 a-pawn events among 3,445 strict opportunities in the 2024 Olympiad; the counts describe style within this event.

| mover PGN Elo | strict opportunities | h-pawn events | a-pawn events |
|---|---:|---:|---:|
| 2200–2399 | 1648 | 65 | 88 |
| 2400–2599 | 1311 | 78 | 75 |
| 2600+ | 486 | 27 | 28 |

Events require the original h-pawn's first arrival on h5/h6 for White or h4/h3 for Black by move 24, after the opponent has castled kingside; the strict denominator has additional conditions: the king remains on the g- or h-file, both queens remain, and at least four rooks or minor pieces remain. The a-pawn comparison uses the corresponding squares; ten detector checks cover pawn identity and the frozen boundaries; both opportunity denominators remain in the [counts](../data/derived/pawn_pattern_counts.csv).

Historical coverage is too unequal to estimate adoption over time, and the detector supplies no measure of decision quality. Bilalić et al.'s absence of a detectable top-level neural-engine quality gain (p. 604) is compatible with style change, but that comparison has no temporal test here.

[Configuration and hashes](../data/derived/pawn_pattern_config.json); [methods](methods.md#capped-learning-pilot).

Amended 16 October 2026: newly read literature; restricted-pool result retained without a historical curve.
