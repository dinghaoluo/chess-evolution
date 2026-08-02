# 'What are we playing for, now?'

This is a working research archive for an essay on my personal website, on what machine-chess means to human players. This analysis plans to draw data from the open World Chess Championship, from Steinitz-Zukertort in 1886 to Gukesh-Ding in 2024, plus the parallel FIDE title from 1993 to 2005.

## essay

In July 2023, Magnus Carlsen declined to defend his classical world title. He had held it for a decade and had been the highest-rated player alive for most of that time; his stated reason was that the classical match format no longer motivated him, and that he did not intend to sit through another one. Ding Liren beat Ian Nepomniachtchi in the 2023 match without him; Ding then lost the title to Gukesh Dommaraju in 2024. As can be seen in the recent matches, engine-assisted preparations have dominated.

The strongest chess engines had been unreachable by any human player since roughly the mid-2000s, and by the late 2010s the gap had became absurd, a state that had not stopped anyone playing or watching. The obvious question, then, is 'What are we still playing for, if engines are unreachable?'

## analyses

Note: none of the analyses are built yet. This shows simply a rough plan for what analyses I would like to do.

### the historical map

I will build a single table that contains every played classical championship game from 1886 through 2024, plus the rapid tiebreaks where a title was actually decided (Carlsen-Karjakin 2016, Carlsen-Caruana 2018, Ding-Nepomniachtchi 2023, and the relevant FIDE knockouts). Per game, enough detail (position sequence, plies, opening tag, format class) to derive later the two quantities I keep coming back to: the ply at which a game first arrives at a position that no earlier championship game had reached (a *novelty*), and the ply at which a player first plays a move a modern engine would not (a suboptimal move).

### where the 'human' game starts

I will probably plot those two ply-quantities against year across the century. My rough guess is that both have migrated deeper into the game over time, and that the second migration has accelerated since the mid-2000s, once serious preparation went engine-assisted. This is a high-confidence projection and if this analysis turns out wrong, then serious structural changes to the essay will entail.

### opening names against reached positions

Check whether the variety of named openings and the variety of positions actually reached at fixed plies have moved together across the archive, or diverged. My guess is that the vocabulary has expanded whilst the sentences have shortened; but the divergence would need to survive rarefaction and plausible ply choices before I trust it.

### convergence on Stockfish

I plan to run one frozen Stockfish configuration over the archive and record how far each player's moves sit from what the engine would have chosen. This analysis will first be anchored to a handful of matches that I know well (Karpov-Kasparov 1984-85, Kramnik-Kasparov 2000, Kramnik-Anand 2008, Ding-Nepomniachtchi 2023).

### style spread across champions (optional)

I will think about how to go about doing this later. 

## scope

Classical and rapid tiebreak games only. FIDE knockouts from 1998 through 2005 stay in, tagged as their own format. The 1972 forfeit and the 1975 non-event stay in the register; the 1909 Lasker-Janowski match does not.